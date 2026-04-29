from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Generator, Tuple

import requests


class DevSecOpsCLI:
    def __init__(self) -> None:
        self.base_url = os.getenv("BACKEND_URL", "http://127.0.0.1:5000").rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    # ------------------------------------------------------------------
    # Generic helpers
    # ------------------------------------------------------------------

    def run(self) -> None:
        while True:
            self._print_header()
            print("1) Health checks")
            print("2) Evaluate file (standard)")
            print("3) Evaluate file (live stream)")
            print("4) Evaluate raw text")
            print("5) List reports")
            print("6) Inspect report by ID")
            print("7) Delete report")
            print("8) Analytics")
            print("9) Change backend URL")
            print("10) Model switch instructions")
            print("0) Exit")

            choice = self._ask("Choose an option", default="1")
            print()

            try:
                if choice == "1":
                    self.health_checks()
                elif choice == "2":
                    self.evaluate_file(stream=False)
                elif choice == "3":
                    self.evaluate_file(stream=True)
                elif choice == "4":
                    self.evaluate_text()
                elif choice == "5":
                    self.list_reports()
                elif choice == "6":
                    self.inspect_report()
                elif choice == "7":
                    self.delete_report()
                elif choice == "8":
                    self.analytics_menu()
                elif choice == "9":
                    self.change_backend_url()
                elif choice == "10":
                    self.print_model_switch_help()
                elif choice == "0":
                    print("Goodbye.")
                    return
                else:
                    print("Invalid choice.")
            except KeyboardInterrupt:
                print("\nOperation cancelled.")
            except Exception as exc:
                print(f"Error: {exc}")

            input("\nPress Enter to continue...")

    def _print_header(self) -> None:
        print("\n" + "=" * 72)
        print("DevSecOps Report Evaluator CLI")
        print(f"Backend: {self.base_url}")
        print("=" * 72)

    @staticmethod
    def _ask(prompt: str, default: str | None = None) -> str:
        suffix = f" [{default}]" if default is not None else ""
        value = input(f"{prompt}{suffix}: ").strip()
        return value if value else (default or "")

    @staticmethod
    def _ask_bool(prompt: str, default: bool = True) -> bool:
        token = "Y/n" if default else "y/N"
        value = input(f"{prompt} ({token}): ").strip().lower()
        if not value:
            return default
        return value in {"y", "yes", "1", "true", "t"}

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        timeout: int = 60,
        **kwargs: Any,
    ) -> Tuple[int, Any]:
        url = f"{self.base_url}{path}"
        response = self.session.request(method, url, timeout=timeout, **kwargs)
        content_type = response.headers.get("Content-Type", "")

        if "application/json" in content_type:
            payload = response.json()
        else:
            payload = response.text

        return response.status_code, payload

    @staticmethod
    def _pretty(data: Any) -> None:
        print(json.dumps(data, indent=2, ensure_ascii=True))

    # ------------------------------------------------------------------
    # Health and config
    # ------------------------------------------------------------------

    def health_checks(self) -> None:
        endpoints = [
            ("Overall", "/api/health"),
            ("Model", "/api/health/model"),
            ("Ollama", "/api/health/ollama"),
            ("Database", "/api/health/db"),
        ]

        for label, path in endpoints:
            print(f"\n[{label}] {path}")
            status, payload = self._request_json("GET", path)
            print(f"HTTP {status}")
            self._pretty(payload)

    def change_backend_url(self) -> None:
        new_url = self._ask("Enter backend URL", default=self.base_url).rstrip("/")
        self.base_url = new_url
        print(f"Backend URL updated to: {self.base_url}")

    # ------------------------------------------------------------------
    # Evaluate endpoints
    # ------------------------------------------------------------------

    def evaluate_file(self, stream: bool = False) -> None:
        file_path = Path(self._ask("Path to report file"))
        if not file_path.exists() or not file_path.is_file():
            print("File not found.")
            return

        flags = self._collect_pipeline_flags()

        if stream:
            self._evaluate_file_stream(file_path, flags)
            return

        with file_path.open("rb") as f:
            files = {"file": (file_path.name, f)}
            status, payload = self._request_json(
                "POST",
                "/api/evaluate/upload",
                files=files,
                data=flags,
                timeout=900,
            )

        print(f"HTTP {status}")
        if isinstance(payload, dict):
            self._print_result_summary(payload)
            self._maybe_save_json(payload)
        else:
            print(payload)

    def evaluate_text(self) -> None:
        print("Enter/Paste report text. End with an empty line:")
        lines = []
        while True:
            line = input()
            if line == "":
                break
            lines.append(line)

        text = "\n".join(lines).strip()
        if not text:
            print("No text provided.")
            return

        filename = self._ask("Virtual filename", default="inline_report.txt")
        flags = self._collect_pipeline_flags()

        body = {
            "text": text,
            "filename": filename,
            **{k: (v == "true") for k, v in flags.items()},
        }

        status, payload = self._request_json(
            "POST",
            "/api/evaluate/text",
            json=body,
            timeout=900,
        )

        print(f"HTTP {status}")
        if isinstance(payload, dict):
            self._print_result_summary(payload)
            self._maybe_save_json(payload)
        else:
            print(payload)

    def _evaluate_file_stream(self, file_path: Path, flags: Dict[str, str]) -> None:
        url = f"{self.base_url}/api/evaluate/stream"
        print("\nStreaming pipeline events...\n")

        with file_path.open("rb") as f:
            files = {"file": (file_path.name, f)}
            with self.session.post(url, files=files, data=flags, stream=True, timeout=None) as response:
                if response.status_code != 200:
                    print(f"HTTP {response.status_code}")
                    print(response.text)
                    return

                final_result: Dict[str, Any] | None = None
                report_id: str | None = None

                for event, data in self._iter_sse_events(response):
                    if event == "connected":
                        msg = data.get("message", "Connected") if isinstance(data, dict) else str(data)
                        print(f"[connected] {msg}")
                    elif event == "report_id":
                        if isinstance(data, dict):
                            report_id = data.get("report_id")
                        print(f"[report_id] {report_id}")
                    elif event == "progress":
                        if isinstance(data, dict):
                            pct = data.get("percent", "?")
                            step = data.get("step", "unknown")
                            msg = data.get("message", "")
                            elapsed_ms = data.get("elapsed_ms")
                            elapsed = f"{elapsed_ms / 1000:.1f}s" if isinstance(elapsed_ms, (int, float)) else "--"
                            print(f"[{pct:>3}%] {step:<34} {msg} (elapsed: {elapsed})")
                        else:
                            print(f"[progress] {data}")
                    elif event == "error":
                        print("[error]")
                        self._pretty(data)
                        return
                    elif event == "result":
                        if isinstance(data, dict):
                            final_result = data
                            break
                        print("[result] Received non-JSON result payload")
                        return

        if final_result is None:
            print("Stream ended without a final result.")
            return

        print("\nPipeline complete.")
        self._print_result_summary(final_result)
        self._maybe_save_json(final_result)

    @staticmethod
    def _iter_sse_events(response: requests.Response) -> Generator[Tuple[str, Any], None, None]:
        event = "message"
        data_lines: list[str] = []

        for raw_line in response.iter_lines(decode_unicode=True):
            if raw_line is None:
                continue

            line = raw_line.rstrip("\r")

            if line == "":
                if data_lines:
                    payload_str = "\n".join(data_lines).strip()
                    try:
                        payload: Any = json.loads(payload_str) if payload_str else {}
                    except json.JSONDecodeError:
                        payload = {"message": payload_str}
                    yield event, payload
                event = "message"
                data_lines = []
                continue

            if line.startswith(":"):
                continue

            if line.startswith("event:"):
                event = line[len("event:") :].strip()
            elif line.startswith("data:"):
                data_lines.append(line[len("data:") :].strip())

    def _collect_pipeline_flags(self) -> Dict[str, str]:
        run_srlm = self._ask_bool("Run SRLM multi-agent evaluation", default=True)
        run_highlights = self._ask_bool("Run attention highlights", default=True)
        run_fol = self._ask_bool("Run FOL verification", default=True)
        run_xai = self._ask_bool("Run XAI explanations", default=True)

        return {
            "run_srlm": "true" if run_srlm else "false",
            "run_highlights": "true" if run_highlights else "false",
            "run_fol": "true" if run_fol else "false",
            "run_xai": "true" if run_xai else "false",
        }

    @staticmethod
    def _print_result_summary(payload: Dict[str, Any]) -> None:
        if "error" in payload:
            print("API error:")
            DevSecOpsCLI._pretty(payload)
            return

        print("Result summary:")
        print(f"- report_id: {payload.get('report_id')}")
        print(f"- filename: {payload.get('filename')}")
        print(f"- status: {payload.get('status')}")
        print(f"- elapsed_ms: {payload.get('elapsed_ms')}")

        verdict = payload.get("unified_verdict")
        if isinstance(verdict, dict):
            print(f"- final_verdict: {verdict.get('final_verdict')}")
            print(f"- confidence: {verdict.get('confidence')}")

    def _maybe_save_json(self, payload: Dict[str, Any]) -> None:
        if not self._ask_bool("Save full JSON result to file", default=False):
            return

        default_name = f"cli_result_{payload.get('report_id', 'unknown')}.json"
        out_path = Path(self._ask("Output file", default=default_name))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
        print(f"Saved: {out_path.resolve()}")

    # ------------------------------------------------------------------
    # Reports endpoints
    # ------------------------------------------------------------------

    def list_reports(self) -> None:
        domain = self._ask("Domain filter (optional)", default="")
        label = self._ask("Label filter (optional)", default="")
        limit = self._ask("Limit", default="20")
        offset = self._ask("Offset", default="0")

        params = {
            "limit": limit,
            "offset": offset,
        }
        if domain:
            params["domain"] = domain
        if label:
            params["label"] = label

        status, payload = self._request_json("GET", "/api/reports", params=params)
        print(f"HTTP {status}")
        self._pretty(payload)

    def inspect_report(self) -> None:
        report_id = self._ask("Report ID")
        if not report_id:
            print("Report ID is required.")
            return

        include_text = self._ask_bool("Include full report text", default=False)
        status, payload = self._request_json(
            "GET",
            f"/api/reports/{report_id}",
            params={"include_text": "true" if include_text else "false"},
        )

        print(f"\n[GET /api/reports/{report_id}] HTTP {status}")
        self._pretty(payload)

        if not self._ask_bool("Fetch all sub-resources (highlights/thought/fol/agents/xai/full-text)", default=True):
            return

        for suffix in ["highlights", "thought-process", "fol", "agents", "xai", "full-text"]:
            path = f"/api/reports/{report_id}/{suffix}"
            status, payload = self._request_json("GET", path)
            print(f"\n[GET {path}] HTTP {status}")
            self._pretty(payload)

    def delete_report(self) -> None:
        report_id = self._ask("Report ID to delete")
        if not report_id:
            print("Report ID is required.")
            return

        if not self._ask_bool(f"Delete report '{report_id}'", default=False):
            print("Cancelled.")
            return

        status, payload = self._request_json("DELETE", f"/api/reports/{report_id}")
        print(f"HTTP {status}")
        self._pretty(payload)

    # ------------------------------------------------------------------
    # Analytics endpoints
    # ------------------------------------------------------------------

    def analytics_menu(self) -> None:
        while True:
            print("\nAnalytics")
            print("1) Overview")
            print("2) Score distribution")
            print("3) Confidence trends")
            print("4) Label distribution")
            print("5) Domain breakdown")
            print("6) Model performance")
            print("7) Agent scores")
            print("0) Back")

            choice = self._ask("Choose analytics option", default="1")
            if choice == "0":
                return

            if choice == "1":
                self._print_analytics("/api/analytics/overview")
            elif choice == "2":
                bins = self._ask("Number of bins", default="10")
                self._print_analytics("/api/analytics/score-distribution", params={"bins": bins})
            elif choice == "3":
                self._print_analytics("/api/analytics/confidence-trends")
            elif choice == "4":
                self._print_analytics("/api/analytics/label-distribution")
            elif choice == "5":
                self._print_analytics("/api/analytics/domain-breakdown")
            elif choice == "6":
                self._print_analytics("/api/analytics/model-performance")
            elif choice == "7":
                self._print_analytics("/api/analytics/agent-scores")
            else:
                print("Invalid choice.")

    def _print_analytics(self, path: str, params: Dict[str, str] | None = None) -> None:
        status, payload = self._request_json("GET", path, params=params or {})
        print(f"HTTP {status}")
        self._pretty(payload)

    # ------------------------------------------------------------------
    # Model guidance
    # ------------------------------------------------------------------

    def print_model_switch_help(self) -> None:
        print("Current backend model info:")
        status, payload = self._request_json("GET", "/api/health/ollama")
        print(f"HTTP {status}")
        self._pretty(payload)

        print("\nTemporary model switch (current PowerShell session):")
        print("  $env:OLLAMA_MODEL='llama3:latest'")
        print("  c:/Users/kamal/Desktop/RIT/devsecops/.venv/Scripts/python.exe run.py")

        print("\nSwitch back to GPT-OSS 20B:")
        print("  $env:OLLAMA_MODEL='gpt-oss:20b'")
        print("  c:/Users/kamal/Desktop/RIT/devsecops/.venv/Scripts/python.exe run.py")

        print("\nPersistent (future sessions):")
        print("  setx OLLAMA_MODEL llama3:latest")
        print("  # reopen terminal, restart backend")


def main() -> int:
    cli = DevSecOpsCLI()
    cli.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

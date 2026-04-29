from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import torch
from transformers import AutoConfig, AutoModelForSequenceClassification, AutoTokenizer

from checkpoint_utils import resolve_best_checkpoint

TEXT_EXTENSIONS = {".txt", ".md", ".log"}
OPTIONAL_EXTENSIONS = {".pdf", ".docx"}


@dataclass
class Prediction:
    report_path: Path
    predicted_label_id: int
    predicted_label_raw: str
    predicted_label_display: str
    confidence: float
    probabilities_by_id: Dict[str, float]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate one or more student report files using a local checkpoint-* model."
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path("."),
        help="Workspace path that contains checkpoint-* folders (default: current folder).",
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=None,
        help="Specific checkpoint path. If omitted, best checkpoint is auto-selected.",
    )
    parser.add_argument(
        "--tokenizer",
        type=str,
        default=None,
        help=(
            "Tokenizer source path or model id. If omitted, tries checkpoint, then config _name_or_path, then roberta-base."
        ),
    )
    parser.add_argument(
        "--local-files-only",
        action="store_true",
        help="Force tokenizer loading from local files only (no internet fallback).",
    )
    parser.add_argument(
        "--report-file",
        type=Path,
        default=None,
        help="Single report file to evaluate.",
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=None,
        help="Directory containing report files to evaluate.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively scan --reports-dir for supported files.",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=512,
        help="Tokenized max sequence length (default: 512).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=8,
        help="Batch size for inference (default: 8).",
    )
    parser.add_argument(
        "--label-map",
        type=Path,
        default=None,
        help=(
            "Optional JSON mapping for label display names, e.g. {\"0\": \"Needs Improvement\", \"1\": \"Good\", \"2\": \"Excellent\"}."
        ),
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("predictions.json"),
        help="Output JSON file path (default: predictions.json).",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("predictions.csv"),
        help="Output CSV file path (default: predictions.csv).",
    )
    parser.add_argument(
        "--cpu",
        action="store_true",
        help="Force CPU inference even if CUDA is available.",
    )

    args = parser.parse_args()

    if not args.report_file and not args.reports_dir:
        parser.error("Provide either --report-file or --reports-dir.")
    if args.report_file and args.reports_dir:
        parser.error("Use only one of --report-file or --reports-dir.")
    if args.max_length < 8:
        parser.error("--max-length must be >= 8")
    if args.batch_size < 1:
        parser.error("--batch-size must be >= 1")

    return args


def load_label_map(label_map_path: Path | None) -> Dict[str, str]:
    if label_map_path is None:
        return {}

    with label_map_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("--label-map must be a JSON object.")

    return {str(k): str(v) for k, v in data.items()}


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def read_report_text(path: Path) -> str:
    suffix = path.suffix.lower()

    if suffix in TEXT_EXTENSIONS:
        return path.read_text(encoding="utf-8", errors="replace")

    if suffix == ".pdf":
        try:
            import pypdf
        except ImportError as exc:
            raise RuntimeError(
                "PDF support requires pypdf. Install with: pip install pypdf"
            ) from exc

        reader = pypdf.PdfReader(str(path))
        return "\n".join((page.extract_text() or "") for page in reader.pages)

    if suffix == ".docx":
        try:
            from docx import Document
        except ImportError as exc:
            raise RuntimeError(
                "DOCX support requires python-docx. Install with: pip install python-docx"
            ) from exc

        document = Document(str(path))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)

    raise ValueError(f"Unsupported file extension for {path.name}: {path.suffix}")


def gather_report_files(report_file: Path | None, reports_dir: Path | None, recursive: bool) -> List[Path]:
    if report_file:
        if not report_file.exists():
            raise FileNotFoundError(f"Report file not found: {report_file}")
        return [report_file]

    assert reports_dir is not None
    if not reports_dir.exists() or not reports_dir.is_dir():
        raise FileNotFoundError(f"Reports directory not found: {reports_dir}")

    allowed = TEXT_EXTENSIONS | OPTIONAL_EXTENSIONS
    pattern = "**/*" if recursive else "*"

    files = [
        p
        for p in sorted(reports_dir.glob(pattern))
        if p.is_file() and p.suffix.lower() in allowed
    ]

    return files


def pick_device(force_cpu: bool) -> torch.device:
    if not force_cpu and torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def load_tokenizer(checkpoint_dir: Path, config: AutoConfig, preferred: str | None, local_only: bool):
    sources: List[str] = []

    if preferred:
        sources.append(preferred)

    sources.append(str(checkpoint_dir))

    base_name = getattr(config, "_name_or_path", None)
    if isinstance(base_name, str) and base_name:
        sources.append(base_name)

    if "roberta-base" not in sources:
        sources.append("roberta-base")

    errors: List[str] = []
    for source in sources:
        try:
            tokenizer = AutoTokenizer.from_pretrained(
                source,
                use_fast=True,
                local_files_only=local_only,
            )
            return tokenizer, source
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{source}: {exc}")

    joined_errors = "\n".join(errors)
    raise RuntimeError(
        "Failed to load tokenizer from all candidate sources. "
        "Pass --tokenizer explicitly or remove --local-files-only if internet is available.\n"
        f"Details:\n{joined_errors}"
    )


def display_label(label_id: int, raw_label: str, label_map: Dict[str, str]) -> str:
    if str(label_id) in label_map:
        return label_map[str(label_id)]
    if raw_label in label_map:
        return label_map[raw_label]
    return raw_label


def chunked(items: Sequence[Path], size: int) -> Iterable[Sequence[Path]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


@torch.inference_mode()
def run_inference(
    report_files: Sequence[Path],
    model,
    tokenizer,
    id2label: Dict[int, str],
    label_map: Dict[str, str],
    device: torch.device,
    max_length: int,
    batch_size: int,
) -> List[Prediction]:
    predictions: List[Prediction] = []

    for batch_files in chunked(report_files, batch_size):
        raw_texts = [normalize_whitespace(read_report_text(path)) for path in batch_files]

        encoded = tokenizer(
            raw_texts,
            truncation=True,
            max_length=max_length,
            padding=True,
            return_tensors="pt",
        )
        encoded = {k: v.to(device) for k, v in encoded.items()}

        logits = model(**encoded).logits
        probs = torch.softmax(logits, dim=-1).detach().cpu()

        for i, path in enumerate(batch_files):
            row_probs = probs[i]
            pred_id = int(torch.argmax(row_probs).item())
            raw = id2label.get(pred_id, f"LABEL_{pred_id}")
            shown = display_label(pred_id, raw, label_map)

            probabilities_by_id = {
                str(idx): float(prob) for idx, prob in enumerate(row_probs.tolist())
            }

            predictions.append(
                Prediction(
                    report_path=path,
                    predicted_label_id=pred_id,
                    predicted_label_raw=raw,
                    predicted_label_display=shown,
                    confidence=float(row_probs[pred_id].item()),
                    probabilities_by_id=probabilities_by_id,
                )
            )

    return predictions


def write_json_output(predictions: Sequence[Prediction], output_path: Path) -> None:
    payload = [
        {
            "report_path": str(p.report_path),
            "predicted_label_id": p.predicted_label_id,
            "predicted_label_raw": p.predicted_label_raw,
            "predicted_label": p.predicted_label_display,
            "confidence": p.confidence,
            "probabilities_by_id": p.probabilities_by_id,
        }
        for p in predictions
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def write_csv_output(predictions: Sequence[Prediction], output_path: Path, num_labels: int) -> None:
    header = [
        "report_path",
        "predicted_label_id",
        "predicted_label_raw",
        "predicted_label",
        "confidence",
    ] + [f"prob_label_{i}" for i in range(num_labels)]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()

        for p in predictions:
            row = {
                "report_path": str(p.report_path),
                "predicted_label_id": p.predicted_label_id,
                "predicted_label_raw": p.predicted_label_raw,
                "predicted_label": p.predicted_label_display,
                "confidence": p.confidence,
            }
            for i in range(num_labels):
                row[f"prob_label_{i}"] = p.probabilities_by_id.get(str(i), 0.0)

            writer.writerow(row)


def main() -> int:
    args = parse_args()

    workspace = args.workspace.resolve()
    checkpoint_dir = args.checkpoint.resolve() if args.checkpoint else resolve_best_checkpoint(workspace)
    report_files = gather_report_files(args.report_file, args.reports_dir, args.recursive)

    if not report_files:
        print("No supported report files found.", file=sys.stderr)
        return 2

    label_map = load_label_map(args.label_map)
    device = pick_device(force_cpu=args.cpu)

    config = AutoConfig.from_pretrained(str(checkpoint_dir), local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        str(checkpoint_dir),
        local_files_only=True,
    )
    tokenizer, tokenizer_source = load_tokenizer(
        checkpoint_dir=checkpoint_dir,
        config=config,
        preferred=args.tokenizer,
        local_only=args.local_files_only,
    )

    model.to(device)
    model.eval()

    id2label = {int(k): str(v) for k, v in dict(config.id2label).items()}
    num_labels = int(config.num_labels)

    predictions = run_inference(
        report_files=report_files,
        model=model,
        tokenizer=tokenizer,
        id2label=id2label,
        label_map=label_map,
        device=device,
        max_length=args.max_length,
        batch_size=args.batch_size,
    )

    write_json_output(predictions, args.output_json)
    write_csv_output(predictions, args.output_csv, num_labels=num_labels)

    print(f"Checkpoint: {checkpoint_dir}")
    print(f"Tokenizer source: {tokenizer_source}")
    print(f"Device: {device}")
    print(f"Reports processed: {len(predictions)}")

    for p in predictions:
        print(
            f"- {p.report_path.name}: {p.predicted_label_display} "
            f"(id={p.predicted_label_id}, confidence={p.confidence:.4f})"
        )

    print(f"Saved JSON: {args.output_json.resolve()}")
    print(f"Saved CSV: {args.output_csv.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

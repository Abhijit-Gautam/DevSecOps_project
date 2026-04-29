"""
Server-Sent Events (SSE) streaming route for real-time pipeline progress.

POST /api/evaluate/stream        — evaluate with live progress stream
GET  /api/evaluate/stream/<id>   — re-stream a completed report's pipeline log

The client receives a stream of SSE events:
  event: progress
  data: {"step": "roberta_inference", "message": "...", "elapsed_ms": 450, ...}

  event: result
  data: { full evaluation result JSON }

  event: error
  data: {"message": "..."}

Frontend usage (JavaScript):
  const es = new EventSource('/api/evaluate/stream-result?id=abc123');
  es.addEventListener('progress', e => updateUI(JSON.parse(e.data)));
  es.addEventListener('result',   e => showResult(JSON.parse(e.data)));
  es.addEventListener('error',    e => showError(JSON.parse(e.data)));

Or with fetch (POST):
  const res = await fetch('/api/evaluate/stream', { method: 'POST', body: formData });
  const reader = res.body.getReader();
  // read chunks and parse SSE lines
"""
from __future__ import annotations

import json
import logging
import os
import queue
import threading
import time
import uuid
from pathlib import Path
from typing import Generator

from flask import Blueprint, Response, current_app, request, stream_with_context

from ..utils.text_processor import normalize_text, read_bytes_text
from ..utils.report_parser import parse_report, parsed_report_to_dict
from ..utils.diagram_extractor import extract_diagram_images

logger = logging.getLogger(__name__)
stream_bp = Blueprint("stream", __name__)

ALLOWED_EXTENSIONS = {".txt", ".md", ".log", ".pdf", ".docx"}

# ── Human-readable step messages ─────────────────────────────────────────────

STEP_MESSAGES = {
    "start":                   ("Initialising pipeline", "⚙️"),
    "roberta_inference":        ("RoBERTa classification complete", "🤖"),
    "attention_highlights":    ("Attention rollout — text highlights extracted", "🔦"),
    "agent_r1_AbstractAgent":  ("AbstractAgent evaluated abstract quality", "📝"),
    "agent_r1_MethodologyAgent": ("MethodologyAgent evaluated research design", "🔬"),
    "agent_r1_ResultsAgent":   ("ResultsAgent evaluated results & analysis", "📊"),
    "agent_r1_CitationAgent":  ("CitationAgent evaluated citations & literature", "📚"),
    "agent_r1_DocumentStructureAgent": ("DocumentStructureAgent evaluated formatting", "📄"),
    "agent_r1_ContentDepthAgent": ("ContentDepthAgent evaluated academic rigour", "🎓"),
    "agent_r1_DiagramAgent": ("DiagramAgent evaluated report visuals", "🖼️"),
    "agent_r1_FormatterAgent": ("FormatterAgent evaluated layout consistency", "📐"),
    "self_reward_AbstractAgent": ("AbstractAgent self-assessed its reasoning quality", "⭐"),
    "self_reward_MethodologyAgent": ("MethodologyAgent self-assessed its reasoning quality", "⭐"),
    "self_reward_ResultsAgent": ("ResultsAgent self-assessed its reasoning quality", "⭐"),
    "self_reward_CitationAgent": ("CitationAgent self-assessed its reasoning quality", "⭐"),
    "self_reward_DocumentStructureAgent": ("DocumentStructureAgent self-assessed quality", "⭐"),
    "self_reward_ContentDepthAgent": ("ContentDepthAgent self-assessed quality", "⭐"),
    "self_reward_DiagramAgent": ("DiagramAgent self-assessed quality", "⭐"),
    "self_reward_FormatterAgent": ("FormatterAgent self-assessed quality", "⭐"),
    "cross_review_AbstractAgent": ("AbstractAgent reviewed peer evaluation", "🔄"),
    "cross_review_MethodologyAgent": ("MethodologyAgent reviewed peer evaluation", "🔄"),
    "cross_review_ResultsAgent": ("ResultsAgent reviewed peer evaluation", "🔄"),
    "cross_review_CitationAgent": ("CitationAgent reviewed peer evaluation", "🔄"),
    "cross_review_DocumentStructureAgent": ("DocumentStructureAgent reviewed peer", "🔄"),
    "cross_review_ContentDepthAgent": ("ContentDepthAgent reviewed peer evaluation", "🔄"),
    "cross_review_DiagramAgent": ("DiagramAgent reviewed peer evaluation", "🔄"),
    "cross_review_FormatterAgent": ("FormatterAgent reviewed peer evaluation", "🔄"),
    "master_arbiter":          ("Master Arbiter synthesised all agent verdicts", "⚖️"),
    "fol_verification":        ("FOL axiom verification complete", "🔏"),
    "xai_explanation":         ("XAI explanations generated", "💡"),
    "complete":                ("Pipeline complete — full results ready", "✅"),
}

STEP_ORDER = [
    "start", "roberta_inference", "attention_highlights",
    "agent_r1_AbstractAgent", "agent_r1_MethodologyAgent",
    "agent_r1_ResultsAgent", "agent_r1_CitationAgent",
    "agent_r1_DocumentStructureAgent", "agent_r1_ContentDepthAgent",
    "agent_r1_DiagramAgent", "agent_r1_FormatterAgent",
    "self_reward_AbstractAgent", "self_reward_MethodologyAgent",
    "self_reward_ResultsAgent", "self_reward_CitationAgent",
    "self_reward_DocumentStructureAgent", "self_reward_ContentDepthAgent",
    "self_reward_DiagramAgent", "self_reward_FormatterAgent",
    "cross_review_AbstractAgent", "cross_review_MethodologyAgent",
    "cross_review_ResultsAgent", "cross_review_CitationAgent",
    "cross_review_DocumentStructureAgent", "cross_review_ContentDepthAgent",
    "cross_review_DiagramAgent", "cross_review_FormatterAgent",
    "master_arbiter", "fol_verification", "xai_explanation", "complete",
]
TOTAL_STEPS = len(STEP_ORDER)


def _step_index(step_name: str) -> int:
    try:
        return STEP_ORDER.index(step_name)
    except ValueError:
        return 0


def _sse(event: str, data: dict) -> str:
    """Format a single SSE message."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _sse_progress(step: str, extra: dict | None = None) -> str:
    msg, icon = STEP_MESSAGES.get(step, (step.replace("_", " ").title(), "⏳"))
    idx = _step_index(step)
    pct = round(((idx + 1) / TOTAL_STEPS) * 100) if TOTAL_STEPS else 0
    payload = {
        "step": step,
        "message": msg,
        "icon": icon,
        "step_index": idx,
        "total_steps": TOTAL_STEPS,
        "percent": min(100, max(0, pct)),
        **(extra or {}),
    }
    return _sse("progress", payload)


# ── Main streaming route ──────────────────────────────────────────────────────

@stream_bp.route("/stream", methods=["POST"])
def evaluate_stream():
    """
    Evaluate a report with real-time SSE progress stream.

    Request: multipart/form-data (same as /api/evaluate/upload)
      - file  OR  text (JSON body with {"text": "..."})
      - run_srlm, run_highlights, run_fol, run_xai (optional booleans)

    Response: text/event-stream
      Multiple SSE events: progress*, result | error
    """
    orchestrator = current_app.config.get("_orchestrator")
    db = current_app.config.get("_db")
    if not orchestrator or not db:
        def _not_ready():
            yield _sse("error", {"message": "Backend still loading. Retry in a few seconds."})
        return Response(stream_with_context(_not_ready()), mimetype="text/event-stream")

    # ── Parse request ────────────────────────────────────────────────────
    report_text = ""
    filename = "stream_input.txt"
    diagram_images: list[str] = []

    if request.content_type and "multipart" in request.content_type:
        file = request.files.get("file")
        if not file or not file.filename:
            def _no_file():
                yield _sse("error", {"message": "No file provided."})
            return Response(stream_with_context(_no_file()), mimetype="text/event-stream")
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            def _bad_ext():
                yield _sse("error", {"message": f"Unsupported file type '{ext}'."})
            return Response(stream_with_context(_bad_ext()), mimetype="text/event-stream")
        filename = file.filename
        file_bytes = file.read()
        report_text = read_bytes_text(file_bytes, filename)
        diagram_images = extract_diagram_images(file_bytes, filename)
        run_srlm = request.form.get("run_srlm", "true").lower() != "false"
        run_highlights = request.form.get("run_highlights", "true").lower() != "false"
        run_fol = request.form.get("run_fol", "true").lower() != "false"
        run_xai = request.form.get("run_xai", "true").lower() != "false"
    else:
        body = request.get_json(force=True, silent=True) or {}
        report_text = body.get("text", "").strip()
        filename = body.get("filename", "inline.txt")
        run_srlm = bool(body.get("run_srlm", True))
        run_highlights = bool(body.get("run_highlights", True))
        run_fol = bool(body.get("run_fol", True))
        run_xai = bool(body.get("run_xai", True))

    if not report_text.strip():
        def _empty():
            yield _sse("error", {"message": "Empty or unreadable report."})
        return Response(stream_with_context(_empty()), mimetype="text/event-stream")

    report_text = normalize_text(report_text)

    # ── Run pipeline in thread, stream events via queue ──────────────────
    q: queue.Queue = queue.Queue()
    SENTINEL = object()

    def _callback(step: str, data: dict):
        q.put(("progress", step, data))

    def _pipeline_thread():
        try:
            parsed = parse_report(report_text)
            parsed_dict = parsed_report_to_dict(parsed)
            q.put(("progress", "start", {"message": "Report parsed", "domain": parsed_dict.get("domain")}))

            report_id = db.create_report(filename=filename, report_text=report_text)
            q.put(("report_id", report_id, {}))

            result = orchestrator.run(
                report_text=report_text,
                parsed_data=parsed_dict,
                run_srlm=run_srlm,
                run_highlights=run_highlights,
                run_fol=run_fol,
                run_xai=run_xai,
                diagram_images=diagram_images,
                step_callback=_callback,
            )

            # Persist
            roberta_result = result.get("roberta_result", {})
            unified_verdict = result.get("unified_verdict", {})
            db.update_report(report_id, {
                "parsed_data": parsed_dict,
                "predicted_label_id": roberta_result.get("predicted_label_id"),
                "predicted_label": roberta_result.get("predicted_label"),
                "confidence": roberta_result.get("confidence"),
                "probabilities": roberta_result.get("probabilities", {}),
                "srlm_results": {
                    "agent_evaluations": result.get("agent_evaluations", []),
                    "self_reward_scores": result.get("self_reward_scores", {}),
                    "cross_reviews": result.get("cross_reviews", []),
                },
                "unified_verdict": unified_verdict,
                "thought_process": result.get("thought_process", []),
                "highlights": result.get("highlight_data", {}),
                "explanations": result.get("xai_result", {}),
                "fol_statements": result.get("fol_result", {}).get("fol_statements", []),
                "fol_verification": result.get("fol_result", {}),
                "domain": parsed_dict.get("domain"),
                "total_score": parsed_dict.get("total_score"),
                "max_score": parsed_dict.get("max_score"),
                "status": "complete",
            })
            for ev in result.get("agent_evaluations", []):
                agent_name = ev.get("agent", "Unknown")
                db.save_agent_evaluation(
                    report_id=report_id, agent_name=agent_name,
                    round_num=ev.get("round", 1), evaluation=ev,
                    self_reward_score=result.get("self_reward_scores", {}).get(agent_name, 5.0),
                )

            full_result = {
                "report_id": report_id, "filename": filename,
                "status": "complete",
                "elapsed_ms": result.get("total_elapsed_ms"),
                "parsed_data": parsed_dict,
                "roberta_result": roberta_result,
                "unified_verdict": unified_verdict,
                "agent_evaluations": result.get("agent_evaluations", []),
                "self_reward_scores": result.get("self_reward_scores", {}),
                "cross_reviews": result.get("cross_reviews", []),
                "highlight_data": result.get("highlight_data", {}),
                "xai_result": result.get("xai_result", {}),
                "fol_result": result.get("fol_result", {}),
                "thought_process": result.get("thought_process", []),
                "pipeline_timeline": result.get("pipeline_timeline", []),
            }
            q.put(("result", full_result, {}))
        except Exception as exc:
            logger.exception("Streaming pipeline failed")
            q.put(("error", str(exc), {}))
        finally:
            q.put((SENTINEL, None, None))

    threading.Thread(target=_pipeline_thread, daemon=True).start()

    @stream_with_context
    def _generate() -> Generator[str, None, None]:
        # Keep-alive ping every 15s while waiting
        last_ping = time.time()
        report_id_sent = False

        yield _sse("connected", {
            "message": "Pipeline started. Streaming progress...",
            "total_steps": TOTAL_STEPS,
        })

        while True:
            try:
                item = q.get(timeout=1.0)
            except queue.Empty:
                # Send keep-alive comment to prevent connection timeout
                if time.time() - last_ping > 15:
                    yield ": keep-alive\n\n"
                    last_ping = time.time()
                continue

            kind, payload, extra = item

            if kind is SENTINEL:
                break
            elif kind == "report_id":
                if not report_id_sent:
                    yield _sse("report_id", {"report_id": payload})
                    report_id_sent = True
            elif kind == "progress":
                yield _sse_progress(payload, extra)
            elif kind == "result":
                yield _sse("result", payload)
                break
            elif kind == "error":
                yield _sse("error", {"message": payload})
                break

    return Response(
        _generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering if behind proxy
        },
    )

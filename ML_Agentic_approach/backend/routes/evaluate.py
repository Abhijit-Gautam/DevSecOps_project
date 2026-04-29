"""
Evaluation routes — the core of the backend.

POST /api/evaluate/text    — evaluate from JSON body
POST /api/evaluate/upload  — evaluate from uploaded file
"""
from __future__ import annotations

import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict

from flask import Blueprint, current_app, jsonify, request

from ..utils.text_processor import normalize_text, read_bytes_text
from ..utils.report_parser import parse_report, parsed_report_to_dict
from ..utils.diagram_extractor import extract_diagram_images
from ..utils.pdf_highlights import extract_pdf_page_texts

logger = logging.getLogger(__name__)
evaluate_bp = Blueprint("evaluate", __name__)

ALLOWED_EXTENSIONS = {".txt", ".md", ".log", ".pdf", ".docx"}


def _get_services():
    """Retrieve lazily-initialised services from app context."""
    orchestrator = current_app.config.get("_orchestrator")
    db = current_app.config.get("_db")
    if orchestrator is None or db is None:
        from flask import abort
        abort(503, "Services not yet initialised. Retry in a few seconds.")
    return orchestrator, db


def _run_pipeline(
    report_text: str,
    filename: str,
    run_srlm: bool,
    run_highlights: bool,
    run_fol: bool,
    run_xai: bool,
    diagram_images: list[str] | None = None,
    pdf_pages: list[str] | None = None,
    original_file_bytes: bytes | None = None,
    original_filename: str | None = None,
) -> Dict[str, Any]:
    """Execute the full analysis pipeline and persist to DB."""
    orchestrator, db = _get_services()

    # ── Persist initial record ────────────────────────────────────────────
    report_id = db.create_report(filename=filename, report_text=report_text)
    pdf_url = _save_original_pdf(report_id, original_file_bytes, original_filename)

    try:
        # ── Parse structure ───────────────────────────────────────────────
        parsed = parse_report(report_text)
        parsed_dict = parsed_report_to_dict(parsed)

        # ── Run orchestrator pipeline ─────────────────────────────────────
        t0 = time.time()
        result = orchestrator.run(
            report_text=report_text,
            parsed_data=parsed_dict,
            run_srlm=run_srlm,
            run_highlights=run_highlights,
            run_fol=run_fol,
            run_xai=run_xai,
            diagram_images=diagram_images,
            pdf_pages=pdf_pages,
        )
        elapsed = round((time.time() - t0) * 1000)

        # ── Unpack results ────────────────────────────────────────────────
        roberta_result = result.get("roberta_result", {})
        unified_verdict = result.get("unified_verdict", {})

        # ── Persist full results ──────────────────────────────────────────
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

        # ── Save per-agent evaluations ────────────────────────────────────
        for ev in result.get("agent_evaluations", []):
            agent_name = ev.get("agent", "Unknown")
            sr_score = result.get("self_reward_scores", {}).get(agent_name, 5.0)
            db.save_agent_evaluation(
                report_id=report_id,
                agent_name=agent_name,
                round_num=ev.get("round", 1),
                evaluation=ev,
                self_reward_score=sr_score,
            )

        return {
            "report_id": report_id,
            "filename": filename,
            "elapsed_ms": elapsed,
            "status": "complete",
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
            "pdf_url": pdf_url,
        }

    except Exception as exc:
        logger.exception(f"Pipeline failed for report {report_id}: {exc}")
        db.update_report(report_id, {"status": "error"})
        raise


def _save_original_pdf(report_id: str, data: bytes | None, filename: str | None) -> str | None:
    if not data or not filename or Path(filename).suffix.lower() != ".pdf":
        return None
    upload_dir = current_app.config.get("UPLOAD_DIR", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    save_path = os.path.join(upload_dir, f"{report_id}.pdf")
    try:
        with open(save_path, "wb") as f:
            f.write(data)
        return f"/api/reports/{report_id}/pdf"
    except Exception:
        logger.exception("Failed to save original PDF for highlighting")
        return None


# ── Routes ────────────────────────────────────────────────────────────────────

@evaluate_bp.route("/text", methods=["POST"])
def evaluate_text():
    """
    Evaluate a report submitted as JSON text.

    Request JSON:
      {
        "text": "...",          # required
        "filename": "optional",
        "run_srlm": true,       # optional, default true
        "run_highlights": true, # optional, default true
        "run_fol": true,        # optional, default true
        "run_xai": true         # optional, default true
      }

    Response 200:
      Full evaluation result (see _run_pipeline return value)
    """
    body = request.get_json(force=True, silent=True) or {}
    text = body.get("text", "").strip()

    if not text:
        return jsonify({"error": "Field 'text' is required and must not be empty."}), 400
    if len(text) > 200_000:
        return jsonify({"error": "Report text exceeds 200,000 character limit."}), 413

    filename = body.get("filename") or "inline_text.txt"
    run_srlm = bool(body.get("run_srlm", True))
    run_highlights = bool(body.get("run_highlights", True))
    run_fol = bool(body.get("run_fol", True))
    run_xai = bool(body.get("run_xai", True))

    normalized = normalize_text(text)

    try:
        result = _run_pipeline(normalized, filename, run_srlm, run_highlights, run_fol, run_xai)
        return jsonify(result), 200
    except Exception as e:
        logger.exception("evaluate_text failed")
        return jsonify({"error": str(e)}), 500


@evaluate_bp.route("/upload", methods=["POST"])
def evaluate_upload():
    """
    Evaluate a report uploaded as a file.

    Request: multipart/form-data
      - file: the report file (.txt, .md, .log, .pdf, .docx)
      - run_srlm: "true"|"false" (optional)
      - run_highlights: "true"|"false" (optional)
      - run_fol: "true"|"false" (optional)
      - run_xai: "true"|"false" (optional)

    Response 200:
      Full evaluation result
    """
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded. Use field name 'file'."}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No filename provided."}), 400

    filename = file.filename
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({
            "error": f"Unsupported file type '{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}"
        }), 415

    file_bytes = file.read()
    if len(file_bytes) > current_app.config.get("MAX_CONTENT_LENGTH", 16 * 1024 * 1024):
        return jsonify({"error": "File too large (max 16 MB)."}), 413

    try:
        text = read_bytes_text(file_bytes, filename)
    except Exception as e:
        return jsonify({"error": f"Failed to read file: {e}"}), 422

    if not text.strip():
        return jsonify({"error": "File appears to be empty or unreadable."}), 422

    # Save to uploads directory
    upload_dir = current_app.config.get("UPLOAD_DIR", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    save_path = os.path.join(upload_dir, f"{uuid.uuid4().hex[:8]}_{filename}")
    try:
        with open(save_path, "wb") as f:
            f.write(file_bytes)
    except Exception:
        pass  # Non-fatal, file saving is optional

    run_srlm = request.form.get("run_srlm", "true").lower() != "false"
    run_highlights = request.form.get("run_highlights", "true").lower() != "false"
    run_fol = request.form.get("run_fol", "true").lower() != "false"
    run_xai = request.form.get("run_xai", "true").lower() != "false"

    normalized = normalize_text(text)
    diagram_images = extract_diagram_images(file_bytes, filename)
    pdf_pages = extract_pdf_page_texts(file_bytes, filename)

    try:
        result = _run_pipeline(
            normalized, filename, run_srlm, run_highlights, run_fol, run_xai,
            diagram_images, pdf_pages, file_bytes, filename
        )
        return jsonify(result), 200
    except Exception as e:
        logger.exception("evaluate_upload failed")
        return jsonify({"error": str(e)}), 500

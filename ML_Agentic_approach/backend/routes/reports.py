"""
Reports CRUD routes.

GET    /api/reports              — list reports (paginated, filterable)
GET    /api/reports/<id>         — get full report
DELETE /api/reports/<id>         — delete report

GET    /api/reports/<id>/highlights      — attention-based text highlights
GET    /api/reports/<id>/thought-process — step-by-step reasoning chain
GET    /api/reports/<id>/fol             — FOL verification details
GET    /api/reports/<id>/agents          — per-agent SRLM evaluations
GET    /api/reports/<id>/xai             — XAI explanation details
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request, send_file

logger = logging.getLogger(__name__)
reports_bp = Blueprint("reports", __name__)


def _db():
    db = current_app.config.get("_db")
    if db is None:
        from flask import abort
        abort(503, "Database not yet initialised.")
    return db


# ── List / CRUD ───────────────────────────────────────────────────────────────

@reports_bp.route("", methods=["GET"])
def list_reports():
    """
    List reports with optional filters.

    Query params:
      domain  — filter by domain (e.g. "Cybersecurity")
      label   — filter by predicted_label
      limit   — page size (default 50, max 200)
      offset  — pagination offset (default 0)

    Response 200:
      {
        "reports": [...],
        "total": int,
        "limit": int,
        "offset": int
      }
    """
    domain = request.args.get("domain")
    label = request.args.get("label")
    limit = min(int(request.args.get("limit", 50)), 200)
    offset = int(request.args.get("offset", 0))

    db = _db()
    reports = db.list_reports(domain=domain, label=label, limit=limit, offset=offset)
    total = db.count_reports()

    return jsonify({
        "reports": reports,
        "total": total,
        "limit": limit,
        "offset": offset,
    })


@reports_bp.route("/<report_id>", methods=["GET"])
def get_report(report_id: str):
    """
    Get a full report by ID (includes all analysis fields).

    Response 200: Full report dict
    Response 404: Not found
    """
    db = _db()
    report = db.get_report(report_id)
    if not report:
        return jsonify({"error": f"Report '{report_id}' not found."}), 404

    if _pdf_exists(report_id):
        report["pdf_url"] = f"/api/reports/{report_id}/pdf"

    # Strip raw report text from summary view unless explicitly requested
    include_text = request.args.get("include_text", "false").lower() == "true"
    if not include_text and "report_text" in report:
        report["report_text_length"] = len(report["report_text"])
        report["report_text_preview"] = report["report_text"][:500] + "..."
        del report["report_text"]

    return jsonify(report)


@reports_bp.route("/<report_id>", methods=["DELETE"])
def delete_report(report_id: str):
    """
    Delete a report and all associated agent evaluations.

    Response 200: {"message": "deleted"}
    Response 404: Not found
    """
    db = _db()
    deleted = db.delete_report(report_id)
    if not deleted:
        return jsonify({"error": f"Report '{report_id}' not found."}), 404
    return jsonify({"message": f"Report '{report_id}' deleted.", "report_id": report_id})


# ── Sub-resource routes ───────────────────────────────────────────────────────

@reports_bp.route("/<report_id>/highlights", methods=["GET"])
def get_highlights(report_id: str):
    """
    Get attention-based text highlighting data.

    Response 200:
      {
        "report_id": str,
        "highlighted_spans": [{"token", "start", "end", "score"}],
        "threshold": float,
        "total_tokens": int,
        "mapped_evidence": [...] (highlight spans mapped to report sections)
      }
    """
    db = _db()
    report = db.get_report(report_id)
    if not report:
        return jsonify({"error": f"Report '{report_id}' not found."}), 404

    highlights = report.get("highlights") or {}
    xai = report.get("explanations") or {}

    return jsonify({
        "report_id": report_id,
        "predicted_label": report.get("predicted_label"),
        "highlighted_spans": highlights.get("highlighted_spans", []),
        "pdf_annotations": highlights.get("pdf_annotations", []),
        "threshold": highlights.get("threshold"),
        "total_tokens": len(highlights.get("tokens", [])),
        "mapped_evidence": xai.get("highlighted_evidence", []),
    })


@reports_bp.route("/<report_id>/thought-process", methods=["GET"])
def get_thought_process(report_id: str):
    """
    Get the step-by-step reasoning chain (thought process log).

    Response 200:
      {
        "report_id": str,
        "steps": [...],
        "total_steps": int,
        "pipeline_timeline": [...]
      }
    """
    db = _db()
    report = db.get_report(report_id)
    if not report:
        return jsonify({"error": f"Report '{report_id}' not found."}), 404

    return jsonify({
        "report_id": report_id,
        "steps": report.get("thought_process") or [],
        "total_steps": len(report.get("thought_process") or []),
    })


@reports_bp.route("/<report_id>/fol", methods=["GET"])
def get_fol(report_id: str):
    """
    Get First-Order Logic verification details.

    Response 200:
      {
        "report_id": str,
        "verdict": str,
        "consistent": bool,
        "consistency_score": float,
        "fol_statements": [...],
        "verification_details": [...],
        "satisfied_rules": [...],
        "violated_rules": [...]
      }
    """
    db = _db()
    report = db.get_report(report_id)
    if not report:
        return jsonify({"error": f"Report '{report_id}' not found."}), 404

    fol = report.get("fol_verification") or {}
    return jsonify({
        "report_id": report_id,
        "verdict": report.get("unified_verdict", {}).get("final_verdict") if isinstance(report.get("unified_verdict"), dict) else report.get("predicted_label"),
        **fol,
    })


@reports_bp.route("/<report_id>/agents", methods=["GET"])
def get_agent_evaluations(report_id: str):
    """
    Get per-agent SRLM evaluations for a report.

    Response 200:
      {
        "report_id": str,
        "agents": [...],
        "self_reward_scores": {...},
        "cross_reviews": [...]
      }
    """
    db = _db()
    report = db.get_report(report_id)
    if not report:
        return jsonify({"error": f"Report '{report_id}' not found."}), 404

    agent_rows = db.get_agent_evaluations(report_id)
    srlm = report.get("srlm_results") or {}

    return jsonify({
        "report_id": report_id,
        "agent_evaluations_db": agent_rows,
        "agent_evaluations": srlm.get("agent_evaluations", []),
        "self_reward_scores": srlm.get("self_reward_scores", {}),
        "cross_reviews": srlm.get("cross_reviews", []),
        "unified_verdict": report.get("unified_verdict"),
    })


@reports_bp.route("/<report_id>/xai", methods=["GET"])
def get_xai(report_id: str):
    """
    Get full XAI (Explainable AI) explanation details.

    Response 200:
      {
        "report_id": str,
        "model_explanation": {...},
        "section_explanations": {...},
        "decision_factors": [...],
        "counterfactuals": [...],
        "improvement_roadmap": [...]
      }
    """
    db = _db()
    report = db.get_report(report_id)
    if not report:
        return jsonify({"error": f"Report '{report_id}' not found."}), 404

    xai = report.get("explanations") or {}
    return jsonify({
        "report_id": report_id,
        "predicted_label": report.get("predicted_label"),
        "confidence": report.get("confidence"),
        **xai,
    })


@reports_bp.route("/<report_id>/full-text", methods=["GET"])
def get_report_text(report_id: str):
    """
    Get the raw report text (not returned by default in get_report).

    Response 200:
      {"report_id": str, "text": str, "word_count": int}
    """
    db = _db()
    report = db.get_report(report_id)
    if not report:
        return jsonify({"error": f"Report '{report_id}' not found."}), 404

    text = report.get("report_text", "")
    return jsonify({
        "report_id": report_id,
        "text": text,
        "word_count": len(text.split()),
        "char_count": len(text),
    })


@reports_bp.route("/<report_id>/pdf", methods=["GET"])
def get_report_pdf(report_id: str):
    """Serve the original uploaded PDF for overlay highlighting."""
    db = _db()
    report = db.get_report(report_id)
    if not report:
        return jsonify({"error": f"Report '{report_id}' not found."}), 404

    pdf_path = _pdf_path(report_id)
    if not pdf_path:
        return jsonify({"error": "Original PDF not available for this report."}), 404

    return send_file(
        os.fspath(pdf_path),
        mimetype="application/pdf",
        as_attachment=False,
        download_name=f"{report_id}.pdf",
    )


def _pdf_path(report_id: str) -> Path | None:
    upload_dir = Path(current_app.config.get("UPLOAD_DIR", "uploads")).resolve()
    pdf_path = (upload_dir / f"{report_id}.pdf").resolve()
    if upload_dir not in pdf_path.parents or not pdf_path.exists():
        return None
    return pdf_path


def _pdf_exists(report_id: str) -> bool:
    return _pdf_path(report_id) is not None

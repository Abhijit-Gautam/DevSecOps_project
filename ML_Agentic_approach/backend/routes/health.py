"""
Health check routes.

GET /api/health          — overall system health
GET /api/health/model    — RoBERTa model status
GET /api/health/ollama   — Ollama LLM server status
GET /api/health/db       — Database status
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

from flask import Blueprint, current_app, jsonify

logger = logging.getLogger(__name__)
health_bp = Blueprint("health", __name__)


@health_bp.route("", methods=["GET"])
def health():
    """
    Overall system health check.

    Response 200:
      {
        "status": "healthy|degraded|unhealthy",
        "components": {"model", "ollama", "db"},
        "uptime_s": float
      }
    """
    checks = {
        "model": _check_model(),
        "ollama": _check_ollama(),
        "db": _check_db(),
    }

    statuses = [c["status"] for c in checks.values()]
    if all(s == "ok" for s in statuses):
        overall = "healthy"
        http_code = 200
    elif any(s == "ok" for s in statuses):
        overall = "degraded"
        http_code = 200
    else:
        overall = "unhealthy"
        http_code = 503

    return jsonify({
        "status": overall,
        "components": checks,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }), http_code


@health_bp.route("/model", methods=["GET"])
def health_model():
    """
    RoBERTa model health check.

    Response:
      {"status": "ok|error", "checkpoint": str, "device": str, "num_labels": int}
    """
    return jsonify(_check_model())


@health_bp.route("/ollama", methods=["GET"])
def health_ollama():
    """
    Ollama LLM server health check.

    Response:
      {"status": "ok|error", "model": str, "available_models": [str], "base_url": str}
    """
    return jsonify(_check_ollama())


@health_bp.route("/db", methods=["GET"])
def health_db():
    """
    Database health check.

    Response:
      {"status": "ok|error", "total_reports": int, "db_path": str}
    """
    return jsonify(_check_db())


# ── Internal check functions ──────────────────────────────────────────────────

def _check_model() -> dict:
    """Check if the RoBERTa model is loaded."""
    orchestrator = current_app.config.get("_orchestrator")
    if orchestrator is None:
        return {
            "status": "loading",
            "message": "Model not yet initialised — startup in progress.",
        }
    try:
        roberta = orchestrator.roberta
        checkpoint = str(roberta.checkpoint_path)
        device = str(roberta.device)
        num_labels = len(roberta.id2label)
        return {
            "status": "ok",
            "checkpoint": checkpoint,
            "device": device,
            "num_labels": num_labels,
            "labels": roberta.id2label,
            "max_length": roberta.max_length,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _check_ollama() -> dict:
    """Check if Ollama is reachable."""
    orchestrator = current_app.config.get("_orchestrator")
    if orchestrator is None:
        return {"status": "loading", "message": "Not yet initialised."}
    try:
        client = orchestrator.ollama
        available = client.is_available()
        models = client.list_models() if available else []
        return {
            "status": "ok" if available else "error",
            "model": client.model,
            "base_url": client.base_url,
            "available_models": models,
            "reachable": available,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _check_db() -> dict:
    """Check database connectivity."""
    db = current_app.config.get("_db")
    if db is None:
        return {"status": "loading", "message": "DB not yet initialised."}
    try:
        total = db.count_reports()
        return {
            "status": "ok",
            "total_reports": total,
            "db_path": db.db_path,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

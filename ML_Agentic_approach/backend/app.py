"""
Flask application factory.

Usage:
    python app.py                  # dev server
    flask --app backend.app run    # via flask CLI

All heavy model loading happens in a background thread so the
server is immediately responsive with 503 until ready.
"""
from __future__ import annotations

import logging
import os
import sys
import threading
from pathlib import Path

from flask import Flask, jsonify
from flask_cors import CORS

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Allow importing from project root (checkpoint_utils, etc.) ───────────────
_BACKEND_DIR = Path(__file__).parent
_ROOT_DIR = _BACKEND_DIR.parent
sys.path.insert(0, str(_ROOT_DIR))


def create_app(config_overrides: dict | None = None) -> Flask:
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # ── Load config ───────────────────────────────────────────────────────
    from .config import Config
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)

    app.config["_orchestrator"] = None
    app.config["_db"] = None

    # ── Register blueprints ───────────────────────────────────────────────
    from .routes.evaluate import evaluate_bp
    from .routes.reports import reports_bp
    from .routes.analytics import analytics_bp
    from .routes.health import health_bp
    from .routes.stream import stream_bp

    app.register_blueprint(evaluate_bp, url_prefix="/api/evaluate")
    app.register_blueprint(stream_bp, url_prefix="/api/evaluate")  # /api/evaluate/stream
    app.register_blueprint(reports_bp, url_prefix="/api/reports")
    app.register_blueprint(analytics_bp, url_prefix="/api/analytics")
    app.register_blueprint(health_bp, url_prefix="/api/health")

    # ── Root / info ───────────────────────────────────────────────────────
    @app.route("/")
    def index():
        return jsonify({
            "name": "DevSecOps Report Evaluator API",
            "version": "1.0.0",
            "status": "running",
            "docs": "See BACKEND.md for full API reference",
            "endpoints": {
                "evaluate_text":      "POST /api/evaluate/text",
                "evaluate_upload":    "POST /api/evaluate/upload",
                "evaluate_stream":    "POST /api/evaluate/stream  ← SSE real-time",
                "list_reports":       "GET  /api/reports",
                "get_report":         "GET  /api/reports/<id>",
                "highlights":         "GET  /api/reports/<id>/highlights",
                "thought_process":    "GET  /api/reports/<id>/thought-process",
                "fol_verification":   "GET  /api/reports/<id>/fol",
                "agent_evaluations":  "GET  /api/reports/<id>/agents",
                "xai_explanation":    "GET  /api/reports/<id>/xai",
                "analytics_overview": "GET  /api/analytics/overview",
                "score_distribution": "GET  /api/analytics/score-distribution",
                "label_distribution": "GET  /api/analytics/label-distribution",
                "confidence_trends":  "GET  /api/analytics/confidence-trends",
                "domain_breakdown":   "GET  /api/analytics/domain-breakdown",
                "model_performance":  "GET  /api/analytics/model-performance",
                "agent_scores":       "GET  /api/analytics/agent-scores",
                "health":             "GET  /api/health",
                "health_model":       "GET  /api/health/model",
                "health_ollama":      "GET  /api/health/ollama",
                "health_db":          "GET  /api/health/db",
            },
        })

    @app.route("/api")
    def api_root():
        return index()

    # ── Error handlers ────────────────────────────────────────────────────
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": "Bad request", "detail": str(e)}), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found", "detail": str(e)}), 404

    @app.errorhandler(413)
    def too_large(e):
        return jsonify({"error": "Payload too large (max 16 MB)"}), 413

    @app.errorhandler(415)
    def unsupported_media(e):
        return jsonify({"error": "Unsupported media type", "detail": str(e)}), 415

    @app.errorhandler(500)
    def server_error(e):
        logger.exception("Unhandled 500")
        return jsonify({"error": "Internal server error", "detail": str(e)}), 500

    @app.errorhandler(503)
    def service_unavailable(e):
        return jsonify({"error": "Service temporarily unavailable. Model loading in progress.", "detail": str(e)}), 503

    # ── Background model initialisation ──────────────────────────────────
    _init_services_async(app)

    return app


# ── Service initialisation ────────────────────────────────────────────────────

def _init_services_async(app: Flask):
    """Start background thread to load model and wire up services."""
    def _loader():
        with app.app_context():
            try:
                _init_services(app)
            except Exception:
                logger.exception("Service initialisation failed")

    t = threading.Thread(target=_loader, name="model-loader", daemon=True)
    t.start()


def _init_services(app: Flask):
    """Load all heavy services: DB, RoBERTa model, Ollama client, Orchestrator."""
    cfg = app.config

    # ── 1. Database ───────────────────────────────────────────────────────
    logger.info("Initialising database...")
    from .storage.db import Database
    db = Database(db_path=cfg["DB_PATH"])
    cfg["_db"] = db
    logger.info(f"Database ready at {cfg['DB_PATH']}")

    # ── 2. RoBERTa model ──────────────────────────────────────────────────
    logger.info("Loading RoBERTa model (may take 30-60s on first load)...")
    from .models.roberta_model import RoBERTaEvaluator
    roberta = RoBERTaEvaluator(
        workspace=cfg["WORKSPACE_PATH"],
        checkpoint_path=cfg.get("CHECKPOINT_PATH"),
        tokenizer_name=cfg["TOKENIZER_NAME"],
        max_length=cfg["MAX_LENGTH"],
        local_files_only=cfg["LOCAL_FILES_ONLY"],
    )
    logger.info(f"RoBERTa loaded from {roberta.checkpoint_path} on {roberta.device}")

    # ── 3. Ollama client ──────────────────────────────────────────────────
    logger.info(f"Connecting to Ollama at {cfg['OLLAMA_BASE_URL']} (model: {cfg['OLLAMA_MODEL']})...")
    from .models.ollama_client import OllamaClient
    ollama = OllamaClient(
        base_url=cfg["OLLAMA_BASE_URL"],
        model=cfg["OLLAMA_MODEL"],
        timeout=cfg["OLLAMA_TIMEOUT"],
    )
    if ollama.is_available():
        models = ollama.list_models()
        logger.info(f"Ollama available. Models: {models}")
    else:
        logger.warning("Ollama not reachable — LLM features will be degraded.")

    # ── 4. Groq VLM client ────────────────────────────────────────────────
    from .utils.groq_vlm_client import GroqVLMClient
    groq_vlm = GroqVLMClient(
        api_key=cfg.get("GROQ_API_KEY"),
        model=cfg["GROQ_VLM_MODEL"],
        timeout=cfg["GROQ_TIMEOUT"],
    )
    if not groq_vlm.is_available():
        logger.warning("GROQ_API_KEY not configured — DiagramAgent will report unavailable when images are present.")

    # ── 5. Orchestrator ───────────────────────────────────────────────────
    logger.info("Wiring up orchestrator...")
    from .agents.orchestrator import AgentOrchestrator
    orchestrator = AgentOrchestrator(
        roberta_model=roberta,
        ollama_client=ollama,
        groq_vlm_client=groq_vlm,
        srlm_rounds=cfg["SRLM_ROUNDS"],
    )
    cfg["_orchestrator"] = orchestrator
    logger.info("All services ready. Backend fully operational.")


# ── Dev server entry point ────────────────────────────────────────────────────

def main():
    """Entry point called by run.py or python -m backend.app."""
    app = create_app()
    port = int(os.getenv("PORT", 5000))
    logger.info(f"Starting server on http://0.0.0.0:{port}")
    try:
        from waitress import serve
        serve(app, host="0.0.0.0", port=port, threads=4)
    except ImportError:
        logger.warning("waitress not installed — falling back to Werkzeug dev server")
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    if __package__ is None or __package__ == "":
        # Invoked as `python backend/app.py` — re-run properly as a module
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, "-m", "backend.app"],
            cwd=str(_ROOT_DIR),
        )
        sys.exit(result.returncode)
    else:
        # Invoked as `python -m backend.app` — relative imports work fine
        main()

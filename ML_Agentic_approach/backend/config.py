"""
Backend configuration - all tuneable knobs in one place.
Override via environment variables in production.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent  # devsecops root


class Config:
    # ── Flask ────────────────────────────────────────────────────────────────
    DEBUG = os.getenv("DEBUG", "true").lower() == "true"
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-CHANGE-IN-PROD")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB upload limit

    # ── RoBERTa Model ────────────────────────────────────────────────────────
    WORKSPACE_PATH = os.getenv("WORKSPACE_PATH", str(BASE_DIR))
    CHECKPOINT_PATH = os.getenv("CHECKPOINT_PATH", None)  # None = auto-discover
    TOKENIZER_NAME = os.getenv("TOKENIZER_NAME", "roberta-base")
    MAX_LENGTH = int(os.getenv("MAX_LENGTH", "512"))
    BATCH_SIZE = int(os.getenv("BATCH_SIZE", "8"))
    LOCAL_FILES_ONLY = os.getenv("LOCAL_FILES_ONLY", "false").lower() == "true"

    # ── Ollama ───────────────────────────────────────────────────────────────
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:latest")
    OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "180"))  # seconds

    # ── Groq VLM (DiagramAgent) ──────────────────────────────────────────────
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_VLM_MODEL = os.getenv("GROQ_VLM_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
    GROQ_TIMEOUT = int(os.getenv("GROQ_TIMEOUT", "60"))

    # ── Storage ──────────────────────────────────────────────────────────────
    DB_PATH = os.getenv(
        "DB_PATH", str(BASE_DIR / "backend" / "storage" / "reports.db")
    )
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", str(BASE_DIR / "backend" / "uploads"))

    # ── SRLM (Self-Rewarding Language Models) ────────────────────────────────
    SRLM_ROUNDS = int(os.getenv("SRLM_ROUNDS", "2"))
    SRLM_SELF_REWARD_THRESHOLD = float(os.getenv("SRLM_SELF_REWARD_THRESHOLD", "7.0"))

    # ── Label mapping ────────────────────────────────────────────────────────
    LABELS = {0: "Needs Improvement", 1: "Good", 2: "Excellent"}

    # ── Allowed upload extensions ─────────────────────────────────────────────
    ALLOWED_EXTENSIONS = {".txt", ".md", ".log", ".pdf", ".docx"}

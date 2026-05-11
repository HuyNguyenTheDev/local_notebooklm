"""
backend/config.py — Cấu hình trung tâm, load .env một lần duy nhất.

Tất cả services import config từ đây, KHÔNG gọi load_dotenv() riêng lẻ.
Thứ tự tìm .env: backend/.env → root/.env → biến môi trường hệ thống.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# ── Tìm và load .env ──────────────────────────────────────────────────────
_backend_dir = Path(__file__).resolve().parent
_root_dir = _backend_dir.parent

_loaded = False
for _env_path in [_backend_dir / ".env", _root_dir / ".env"]:
    if _env_path.exists():
        load_dotenv(_env_path, override=True)
        print(f"[CONFIG] Loaded .env from: {_env_path}")
        _loaded = True
        break

if not _loaded:
    print("[CONFIG] No .env file found, using system environment variables")

# ── Supabase ──────────────────────────────────────────────────────────────
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

# Tự động fix scheme postgresql+asyncpg:// → postgresql://
_raw_db_url: str = os.getenv("DATABASE_URL", "")
DATABASE_URL: str = (
    _raw_db_url
    .replace("postgresql+asyncpg://", "postgresql://")
    .replace("postgres+asyncpg://", "postgresql://")
)

# ── External APIs ─────────────────────────────────────────────────────────
LLM_API_URL: str = os.getenv("LLM_API_URL", "http://127.0.0.1:8001")
LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
EMBEDDING_API_URL: str = os.getenv("EMBEDDING_API_URL", "")   # Optional khi chưa setup
PDF_PARSE_API_URL: str = os.getenv("PDF_PARSE_API_URL", "")   # Optional

# ── OpenRouter Embeddings (optional) ─────────────────────────────────────
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_SITE_URL: str = os.getenv("OPENROUTER_SITE_URL", "")
OPENROUTER_SITE_NAME: str = os.getenv("OPENROUTER_SITE_NAME", "")

# ── Chunking ──────────────────────────────────────────────────────────────
CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1024"))
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "128"))

# ── Vector / Embedding ────────────────────────────────────────────────────
EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "1024"))
EMBED_MODEL: str = os.getenv("EMBED_MODEL", "BAAI/bge-m3")

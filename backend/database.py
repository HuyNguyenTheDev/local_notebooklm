"""
database.py — Supabase clients (sync + async) + asyncpg pool cho pgvector queries.

Dung:
  from backend.database import get_supabase_client (sync), get_supabase (async), get_db_pool

Supabase sync client  -> CRUD operations (synchronous)
Supabase async client -> CRUD operations (asynchronous)
asyncpg pool          -> pgvector similarity search (raw SQL)
"""

import ssl
from typing import Optional

import asyncpg
from supabase import AsyncClient, acreate_client, create_client

from backend.config import DATABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL

# ---------------------------------------------------------------------------
# Supabase sync client (singleton)
# ---------------------------------------------------------------------------
_supabase_sync_client: Optional[object] = None


def get_supabase_client():
    """Tra ve Supabase sync client (khoi tao lan dau goi)."""
    global _supabase_sync_client
    if _supabase_sync_client is None:
        if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
            raise RuntimeError(
                "SUPABASE_URL hoac SUPABASE_SERVICE_ROLE_KEY chua duoc set trong .env"
            )
        _supabase_sync_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        print("[OK] Supabase sync client initialized")
    return _supabase_sync_client


# ---------------------------------------------------------------------------
# Supabase async client (singleton)
# ---------------------------------------------------------------------------
_supabase_async_client: Optional[AsyncClient] = None


async def get_supabase() -> AsyncClient:
    """Tra ve Supabase AsyncClient (khoi tao lan dau goi)."""
    global _supabase_async_client
    if _supabase_async_client is None:
        if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
            raise RuntimeError(
                "SUPABASE_URL hoac SUPABASE_SERVICE_ROLE_KEY chua duoc set trong .env"
            )
        _supabase_async_client = await acreate_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    return _supabase_async_client


# ---------------------------------------------------------------------------
# asyncpg connection pool (cho pgvector raw SQL)
# ---------------------------------------------------------------------------
_pool: Optional[asyncpg.Pool] = None


async def get_db_pool() -> asyncpg.Pool:
    """Tra ve asyncpg Pool (khoi tao lan dau goi)."""
    global _pool
    if _pool is None:
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL chua duoc set trong .env")

        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        _pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=1,
            max_size=10,
            ssl=ssl_ctx,
            init=_register_vector_codec,
            command_timeout=30,
        )
    return _pool


async def _register_vector_codec(conn: asyncpg.Connection) -> None:
    """
    Dang ky kieu 'vector' cho asyncpg duoi dang text codec.
    KHONG chay CREATE EXTENSION — extension da duoc tao qua migration SQL.
    """
    try:
        await conn.set_type_codec(
            "vector",
            encoder=_encode_vector,
            decoder=_decode_vector,
            schema="public",
            format="text",
        )
    except Exception:
        # Neu kieu vector chua ton tai (chua chay migration), bo qua
        pass


def _encode_vector(value) -> str:
    if isinstance(value, str):
        return value
    return "[" + ",".join(str(v) for v in value) + "]"


def _decode_vector(value: str) -> list:
    return [float(v) for v in value.strip("[]").split(",")]


async def close_db_pool() -> None:
    """Dong pool khi shutdown."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None

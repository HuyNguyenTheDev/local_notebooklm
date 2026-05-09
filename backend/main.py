"""
main.py -- FastAPI application entry point.

Lifecycle:
  startup  -> warm up DB pool (asyncpg) + Supabase client
  shutdown -> close pool

Routers:
  /upload    -> upload file + trigger ingest
  /documents -> workspace & file CRUD
  /chat      -> RAG chat
"""

# Fix Windows terminal encoding
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import close_db_pool, get_db_pool
from backend.routers.chat import router as chat_router
from backend.routers.embeddings import router as embeddings_router
from backend.routers.knowledge import router as knowledge_router
from backend.routers.upload import router as upload_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: warm up DB pool
    try:
        await get_db_pool()
        print("[OK] Database pool initialized")
    except Exception as e:
        print(f"[WARN] Database connection failed: {e}")
        print("[INFO] Server se chay ma khong co DB. Cac endpoint can DB se bao loi khi goi.")

    yield

    # Shutdown: close pool
    await close_db_pool()
    print("[INFO] Server shutdown complete")


app = FastAPI(
    title="Local NotebookLM Backend",
    version="2.0.0",
    description="RAG-powered document Q&A with Supabase pgvector",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router)
app.include_router(knowledge_router)
app.include_router(chat_router)
app.include_router(embeddings_router)


@app.get("/")
async def healthcheck() -> dict:
    return {"status": "ok", "version": "2.0.0"}

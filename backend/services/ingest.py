"""
services/ingest.py — Orchestrator: parse → chunk → embed → store.

Được gọi dưới dạng FastAPI BackgroundTask sau khi upload file.
Pipeline:
  1. Đọc file bytes từ disk (file đã được lưu tạm)
  2. Parse text (pypdf hoặc API)
  3. Update DB: raw_text, status='processing'
  4. Chunk text
  5. Embed chunks (batch)
  6. Store chunks vào pgvector
  7. Update DB: status='done'
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from backend.services.chunker import estimate_token_count, split_text
from backend.services.embedding import EMBED_MODEL, embed_texts
from backend.services.file_parser import parse_file_async
from backend.services.vector_store import (
    delete_chunks_by_file,
    insert_chunks,
    update_file_status,
    update_file_text,
)

UPLOADS_DIR = Path(__file__).resolve().parents[1] / "data" / "uploads"


async def ingest_file(file_id: UUID, workspace_id: UUID, stored_path: Path) -> None:
    """
    Hàm chính của ingest pipeline.
    Chạy trong background — không raise exception ra ngoài request.
    """
    try:
        await _run_ingest(file_id, workspace_id, stored_path)
    except Exception as exc:
        print(f"[ERROR] ingest_file {file_id}: {exc}")
    finally:
        if stored_path.exists():
            stored_path.unlink(missing_ok=True)


async def _run_ingest(file_id: UUID, workspace_id: UUID, stored_path: Path) -> None:
    parse_done = False
    try:
        # --- Bước 1: Parse ---
        await update_file_status(file_id, "processing")
        raw_text = await parse_file_async(stored_path)

        suffix = stored_path.suffix.lower()
        is_pdf = suffix == ".pdf"

        if is_pdf and not raw_text.strip():
            await update_file_status(file_id, "failed")
            return

        # --- Bước 2: Lưu raw_text vào DB ---
        if is_pdf:
            # PDF: lưu raw_text nhưng chưa mark done (chǝ chunk+embed xong mới done)
            await update_file_text(file_id, raw_text, parse_status="processing")
        else:
            # txt/md: không cần chunk/embed, mark done luôn
            await update_file_text(file_id, raw_text, parse_status="done")
            await update_file_status(file_id, "done")
            return

        parse_done = True

        # --- Bước 3: Chunk ---
        chunks = split_text(raw_text)
        if not chunks:
            print(f"[WARN] ingest_file {file_id}: no chunks generated")
            await update_file_status(file_id, "done")
            return

        # --- Bước 4: Embed (batch) ---
        embeddings = await embed_texts(chunks)

        # --- Bước 5: Token counts ---
        token_counts = [estimate_token_count(c) for c in chunks]

        # --- Bước 6: Xóa chunks cũ (re-ingest support) + Insert mới ---
        await delete_chunks_by_file(file_id)
        await insert_chunks(
            file_id=file_id,
            workspace_id=workspace_id,
            chunks=chunks,
            embeddings=embeddings,
            token_counts=token_counts,
            embed_model=EMBED_MODEL,
        )

        # Mark done chỉ sau khi toàn bộ pipeline thành công
        await update_file_text(file_id, raw_text, parse_status="done")
        await update_file_status(file_id, "done")
        print(f"[INFO] ingest_file {file_id}: {len(chunks)} chunks embedded & stored.")
    except Exception as exc:
        print(f"[ERROR] ingest_file {file_id} (post-parse): {exc}")
        await update_file_status(file_id, "failed")

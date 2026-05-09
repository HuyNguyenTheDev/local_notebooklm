"""
services/vector_store.py — CRUD operations cho Supabase (workspaces, files, chunks).

Dùng Supabase sync client để tối giản complexity.
"""

from __future__ import annotations

import uuid
from typing import Optional
from uuid import UUID

from backend.database import get_db_pool, get_supabase_client
from backend.models.chunk import ChunkSearchResult

# ---------------------------------------------------------------------------
# Workspaces
# ---------------------------------------------------------------------------


async def create_workspace(name: str) -> dict:
    """
    Tạo workspace mới. Trả về dict row từ Supabase.
    Nếu đã tồn tại (name unique), trả về workspace đó.
    """
    sb = get_supabase_client()

    # Kiểm tra đã tồn tại chưa
    existing = sb.table("workspaces").select("*").eq("name", name).execute()
    if existing.data:
        return existing.data[0]

    result = sb.table("workspaces").insert({"name": name}).execute()
    return result.data[0]


async def list_workspaces() -> list[dict]:
    """Lấy tất cả workspaces, sort by created_at DESC."""
    sb = get_supabase_client()
    result = sb.table("workspaces").select("*").order("created_at", desc=True).execute()
    return result.data


async def get_workspace_by_name(name: str) -> Optional[dict]:
    """Lấy workspace theo tên (name unique)."""
    sb = get_supabase_client()
    result = sb.table("workspaces").select("*").eq("name", name).execute()
    return result.data[0] if result.data else None


async def resolve_workspace_id(workspace_key: str, create_if_missing: bool = False) -> Optional[UUID]:
    """Nhận UUID hoặc name, trả về UUID nếu tìm thấy."""
    try:
        return UUID(workspace_key)
    except (ValueError, TypeError):
        pass

    row = await get_workspace_by_name(workspace_key)
    if row is None and create_if_missing:
        row = await create_workspace(workspace_key)

    return UUID(row["id"]) if row else None


async def search_workspaces(query: str) -> list[dict]:
    """Tìm workspace theo tên (ilike)."""
    sb = get_supabase_client()
    result = (
        sb.table("workspaces")
        .select("*")
        .ilike("name", f"%{query}%")
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


async def delete_workspace(workspace_id: UUID) -> int:
    """
    Xóa workspace. Nhờ ON DELETE CASCADE, files và chunks liên quan bị xóa theo.
    Trả về số file đã bị xóa.
    """
    sb = get_supabase_client()

    # Đếm file trước khi xóa
    files_res = (
        sb.table("files")
        .select("id", count="exact")
        .eq("workspace_id", str(workspace_id))
        .execute()
    )
    file_count = files_res.count or 0

    sb.table("workspaces").delete().eq("id", str(workspace_id)).execute()
    return file_count


# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------


async def create_file_record(
    workspace_id: UUID,
    filename: str,
    file_type: str,
    raw_text: Optional[str] = None,
    parse_status: str = "pending",
) -> dict:
    """Insert bản ghi file mới vào bảng `files`."""
    sb = get_supabase_client()
    payload = {
        "workspace_id": str(workspace_id),
        "filename": filename,
        "file_type": file_type,
        "raw_text": raw_text,
        "parse_status": parse_status,
    }
    result = sb.table("files").insert(payload).execute()
    return result.data[0]


async def update_file_text(file_id: UUID, raw_text: str, parse_status: str = "done") -> None:
    """Cập nhật raw_text và parse_status sau khi parse xong."""
    sb = get_supabase_client()
    sb.table("files").update(
        {"raw_text": raw_text, "parse_status": parse_status}
    ).eq("id", str(file_id)).execute()


async def update_file_status(file_id: UUID, status: str) -> None:
    """Cập nhật chỉ parse_status."""
    sb = get_supabase_client()
    sb.table("files").update({"parse_status": status}).eq("id", str(file_id)).execute()


async def list_files(workspace_id: UUID) -> list[dict]:
    """Lấy tất cả files của workspace."""
    sb = get_supabase_client()
    result = (
        sb.table("files")
        .select("id, workspace_id, filename, file_type, parse_status, created_at")
        .eq("workspace_id", str(workspace_id))
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


async def get_file(file_id: UUID) -> Optional[dict]:
    """Lấy 1 file theo ID."""
    sb = get_supabase_client()
    result = sb.table("files").select("*").eq("id", str(file_id)).execute()
    return result.data[0] if result.data else None


async def delete_file(file_id: UUID, workspace_id: UUID) -> bool:
    """
    Xóa file (chunks tự xóa theo CASCADE).
    Trả về True nếu xóa thành công.
    """
    sb = get_supabase_client()
    result = (
        sb.table("files")
        .delete()
        .eq("id", str(file_id))
        .eq("workspace_id", str(workspace_id))
        .execute()
    )
    return bool(result.data)


async def rename_file(file_id: UUID, workspace_id: UUID, new_filename: str) -> bool:
    """Đổi tên file."""
    sb = get_supabase_client()
    result = (
        sb.table("files")
        .update({"filename": new_filename})
        .eq("id", str(file_id))
        .eq("workspace_id", str(workspace_id))
        .execute()
    )
    return bool(result.data)


# ---------------------------------------------------------------------------
# Chunks
# ---------------------------------------------------------------------------


async def insert_chunks(
    file_id: UUID,
    workspace_id: UUID,
    chunks: list[str],
    embeddings: list[list[float]],
    token_counts: list[int],
    embed_model: str,
) -> None:
    """
    Bulk insert chunks với embedding vào bảng `chunks`.
    Dùng Supabase REST API (HTTPS) thay vì asyncpg để tránh lỗi port bị chặn.
    """
    sb = get_supabase_client()
    records = [
        {
            "id": str(uuid.uuid4()),
            "file_id": str(file_id),
            "workspace_id": str(workspace_id),
            "chunk_index": idx,
            "content": content,
            "token_count": token_count,
            "embedding": f"[{','.join(str(v) for v in embedding)}]",
            "embed_model": embed_model,
        }
        for idx, (content, embedding, token_count) in enumerate(
            zip(chunks, embeddings, token_counts)
        )
    ]

    # Supabase REST upsert theo batch 100 để tránh request quá lớn
    batch_size = 100
    for i in range(0, len(records), batch_size):
        sb.table("chunks").upsert(
            records[i : i + batch_size],
            on_conflict="file_id,chunk_index",
        ).execute()


async def delete_chunks_by_file(file_id: UUID) -> None:
    """Xóa tất cả chunks của một file."""
    sb = get_supabase_client()
    sb.table("chunks").delete().eq("file_id", str(file_id)).execute()


async def list_chunks_by_file(file_id: UUID) -> list[dict]:
    """Lay tat ca chunks cua mot file theo thu tu chunk_index."""
    sb = get_supabase_client()
    result = (
        sb.table("chunks")
        .select("id, file_id, workspace_id, chunk_index, content, token_count, embed_model")
        .eq("file_id", str(file_id))
        .order("chunk_index")
        .execute()
    )
    return result.data


async def similarity_search(
    workspace_id: UUID,
    query_embedding: list[float],
    top_k: int = 5,
    similarity_threshold: float = 0.3,
) -> list[ChunkSearchResult]:
    """
    Tìm top-K chunks gần nhất với query_embedding trong workspace.

    Dùng SQL function `search_chunks` đã tạo sẵn trên Supabase,
    fallback sang raw SQL nếu function chưa tồn tại.
    """
    pool = await get_db_pool()
    embedding_str = f"[{','.join(str(v) for v in query_embedding)}]"

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                id        AS chunk_id,
                file_id,
                content,
                1 - (embedding <=> $1::vector) AS similarity
            FROM chunks
            WHERE workspace_id = $2
              AND 1 - (embedding <=> $1::vector) > $3
            ORDER BY embedding <=> $1::vector
            LIMIT $4
            """,
            embedding_str,
            str(workspace_id),
            similarity_threshold,
            top_k,
        )

    return [
        ChunkSearchResult(
            chunk_id=row["chunk_id"],
            file_id=row["file_id"],
            content=row["content"],
            similarity=row["similarity"],
        )
        for row in rows
    ]

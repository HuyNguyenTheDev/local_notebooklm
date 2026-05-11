"""
services/vector_store.py — CRUD operations cho Supabase (workspaces, files, chunks).

Dùng Supabase sync client để tối giản complexity.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Optional
from uuid import UUID

from backend.database import get_db_pool, get_supabase_client
from backend.models.chunk import ChunkSearchResult

try:
    from deep_translator import GoogleTranslator
except ImportError:  # pragma: no cover - runtime dependency in BM25 mode
    GoogleTranslator = None

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
    await refresh_bm25_stats()
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
    if result.data:
        await refresh_bm25_stats()
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
# Chat sessions / messages
# ---------------------------------------------------------------------------


async def create_chat_session(workspace_id: UUID, title: str = "New chat") -> dict:
    """Create a chat session for a workspace."""
    sb = get_supabase_client()
    result = (
        sb.table("chat_sessions")
        .insert({"workspace_id": str(workspace_id), "title": title})
        .execute()
    )
    return result.data[0]


async def get_chat_session(session_id: UUID) -> Optional[dict]:
    """Get one chat session by ID."""
    sb = get_supabase_client()
    result = sb.table("chat_sessions").select("*").eq("id", str(session_id)).execute()
    return result.data[0] if result.data else None


async def list_chat_sessions(workspace_id: UUID) -> list[dict]:
    """List chat sessions in a workspace, newest first."""
    sb = get_supabase_client()
    result = (
        sb.table("chat_sessions")
        .select("*")
        .eq("workspace_id", str(workspace_id))
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


async def delete_chat_session(session_id: UUID, workspace_id: UUID) -> bool:
    """Delete a chat session in a workspace."""
    sb = get_supabase_client()
    result = (
        sb.table("chat_sessions")
        .delete()
        .eq("id", str(session_id))
        .eq("workspace_id", str(workspace_id))
        .execute()
    )
    return bool(result.data)


async def rename_chat_session(session_id: UUID, workspace_id: UUID, title: str) -> bool:
    """Rename a chat session."""
    sb = get_supabase_client()
    result = (
        sb.table("chat_sessions")
        .update({"title": title})
        .eq("id", str(session_id))
        .eq("workspace_id", str(workspace_id))
        .execute()
    )
    return bool(result.data)


async def insert_chat_message(
    session_id: UUID,
    role: str,
    content: str,
    source_chunks: Optional[list[UUID]] = None,
) -> dict:
    """Insert one chat message."""
    sb = get_supabase_client()
    payload = {
        "session_id": str(session_id),
        "role": role,
        "content": content,
        "source_chunks": [str(chunk_id) for chunk_id in (source_chunks or [])],
    }
    result = sb.table("messages").insert(payload).execute()
    return result.data[0]


async def list_chat_messages(session_id: UUID) -> list[dict]:
    """List messages in one session, oldest first."""
    sb = get_supabase_client()
    result = (
        sb.table("messages")
        .select("*")
        .eq("session_id", str(session_id))
        .order("created_at")
        .execute()
    )
    return result.data


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


async def refresh_bm25_for_file(file_id: UUID) -> None:
    """
    Rebuild BM25 term frequencies for one file and refresh corpus stats.

    The SQL objects live in `supabase_migration.sql`. This function is best-effort
    so ingestion still succeeds if BM25 has not been migrated yet.
    """
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute("SELECT rebuild_bm25_terms_for_file($1::uuid)", file_id)
            await conn.execute("REFRESH MATERIALIZED VIEW bm25_stats")
            term_count = await conn.fetchval(
                """
                SELECT count(*)
                FROM chunk_terms ct
                JOIN chunks c ON c.id = ct.chunk_id
                WHERE c.file_id = $1::uuid
                """,
                file_id,
            )
            print(f"[INFO] BM25 refreshed for file {file_id}: {term_count} terms.")
    except Exception as exc:
        print(f"[WARN] BM25 refresh for file {file_id} failed: {exc}")


async def refresh_bm25_stats() -> None:
    """Refresh BM25 corpus statistics after deletes or bulk maintenance."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute("REFRESH MATERIALIZED VIEW bm25_stats")
    except Exception as exc:
        print(f"[WARN] BM25 stats refresh failed: {exc}")


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
    embedding_str = f"[{','.join(str(v) for v in query_embedding)}]"

    try:
        pool = await get_db_pool()
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
    except Exception as exc:
        print(f"[WARN] direct pgvector search failed, falling back to Supabase RPC: {exc}")
        return await _similarity_search_via_rpc(
            workspace_id=workspace_id,
            embedding_str=embedding_str,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
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


async def bm25_search(
    workspace_id: UUID,
    query: str,
    top_k: int = 5,
    min_score: float = 0.0,
) -> list[ChunkSearchResult]:
    """
    Search chunks with BM25 over normalized English terms.

    Vietnamese questions are translated to English only inside this BM25 flow,
    leaving the default vector path untouched.
    """
    bm25_query = await _translate_vi_to_en_for_bm25(query)

    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT chunk_id, file_id, content, score
                FROM search_chunks_bm25($1::text, $2::uuid, $3::int, $4::float)
                """,
                bm25_query,
                str(workspace_id),
                top_k,
                min_score,
            )
    except Exception as exc:
        print(f"[WARN] direct BM25 search failed, falling back to Supabase RPC: {exc}")
        return await _bm25_search_via_rpc(
            workspace_id=workspace_id,
            query=bm25_query,
            top_k=top_k,
            min_score=min_score,
        )

    return [
        ChunkSearchResult(
            chunk_id=row["chunk_id"],
            file_id=row["file_id"],
            content=row["content"],
            similarity=float(row["score"]),
        )
        for row in rows
    ]


async def hybrid_search(
    workspace_id: UUID,
    query: str,
    query_embedding: list[float],
    top_k: int = 5,
    similarity_threshold: float = 0.3,
) -> list[ChunkSearchResult]:
    """Blend vector and BM25 rankings with reciprocal rank fusion."""
    vector_task = similarity_search(
        workspace_id=workspace_id,
        query_embedding=query_embedding,
        top_k=top_k * 2,
        similarity_threshold=similarity_threshold,
    )
    bm25_task = bm25_search(
        workspace_id=workspace_id,
        query=query,
        top_k=top_k * 2,
    )
    vector_results, bm25_results = await asyncio.gather(vector_task, bm25_task)
    return _merge_ranked_results([vector_results, bm25_results], top_k=top_k)


async def _translate_vi_to_en_for_bm25(query: str) -> str:
    cleaned = query.strip()
    if not cleaned or GoogleTranslator is None:
        return cleaned

    try:
        translated = await asyncio.to_thread(
            lambda: GoogleTranslator(source="vi", target="en").translate(cleaned)
        )
    except Exception as exc:
        print(f"[WARN] BM25 query translation failed, using original query: {exc}")
        return cleaned

    return translated.strip() or cleaned


def _merge_ranked_results(
    result_groups: list[list[ChunkSearchResult]],
    top_k: int,
) -> list[ChunkSearchResult]:
    fused: dict[str, dict] = {}
    rank_constant = 60

    for results in result_groups:
        for rank, result in enumerate(results, start=1):
            key = str(result.chunk_id)
            if key not in fused:
                fused[key] = {"result": result, "score": 0.0}
            fused[key]["score"] += 1 / (rank_constant + rank)

    ranked = sorted(fused.values(), key=lambda item: item["score"], reverse=True)
    return [
        ChunkSearchResult(
            chunk_id=item["result"].chunk_id,
            file_id=item["result"].file_id,
            content=item["result"].content,
            similarity=item["score"],
        )
        for item in ranked[:top_k]
    ]


async def _similarity_search_via_rpc(
    workspace_id: UUID,
    embedding_str: str,
    top_k: int,
    similarity_threshold: float,
) -> list[ChunkSearchResult]:
    """Fallback vector search through Supabase REST/RPC."""
    try:
        sb = get_supabase_client()
        result = sb.rpc(
            "search_chunks",
            {
                "query_embedding": embedding_str,
                "target_workspace_id": str(workspace_id),
                "match_count": top_k,
                "similarity_threshold": similarity_threshold,
            },
        ).execute()

        return [
            ChunkSearchResult(
                chunk_id=row["chunk_id"],
                file_id=row["file_id"],
                content=row["content"],
                similarity=row["similarity"],
            )
            for row in (result.data or [])
        ]
    except Exception as exc:
        print(f"[ERROR] Supabase RPC search_chunks failed: {exc}")
        return []


async def _bm25_search_via_rpc(
    workspace_id: UUID,
    query: str,
    top_k: int,
    min_score: float,
) -> list[ChunkSearchResult]:
    """Fallback BM25 search through Supabase REST/RPC."""
    try:
        sb = get_supabase_client()
        result = sb.rpc(
            "search_chunks_bm25",
            {
                "p_query": query,
                "target_workspace_id": str(workspace_id),
                "match_count": top_k,
                "min_score": min_score,
            },
        ).execute()

        return [
            ChunkSearchResult(
                chunk_id=row["chunk_id"],
                file_id=row["file_id"],
                content=row["content"],
                similarity=float(row["score"]),
            )
            for row in (result.data or [])
        ]
    except Exception as exc:
        print(f"[ERROR] Supabase RPC search_chunks_bm25 failed: {exc}")
        return []

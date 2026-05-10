"""
routers/chat.py - RAG chat endpoints with persisted sessions/messages.
"""

from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from backend.models.document import (
    ChatMessageRecord,
    ChatRequest,
    ChatResponse,
    ChatSessionCreate,
    ChatSessionPreview,
    ChatSessionUpdate,
)
from backend.services.embedding import embed_query
from backend.services.llm_client import ask_llm
from backend.services.vector_store import (
    create_chat_session,
    delete_chat_session,
    get_chat_session,
    insert_chat_message,
    list_chat_messages,
    list_chat_sessions,
    rename_chat_session,
    resolve_workspace_id,
    similarity_search,
)

router = APIRouter(prefix="/chat", tags=["chat"])

_TOP_K = 5
_SIMILARITY_THRESHOLD = 0.3


@router.get("/sessions", response_model=List[ChatSessionPreview])
async def get_chat_sessions(workspace_id: str = Query(...)) -> List[ChatSessionPreview]:
    resolved = await resolve_workspace_id(workspace_id)
    if resolved is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    rows = await list_chat_sessions(resolved)
    return [_row_to_session(row) for row in rows]


@router.post("/sessions", response_model=ChatSessionPreview, status_code=201)
async def create_chat_session_endpoint(body: ChatSessionCreate) -> ChatSessionPreview:
    resolved = await resolve_workspace_id(body.workspace_id)
    if resolved is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    row = await create_chat_session(resolved, _clean_session_title(body.title))
    return _row_to_session(row)


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageRecord])
async def get_session_messages(session_id: UUID) -> List[ChatMessageRecord]:
    session = await get_chat_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    rows = await list_chat_messages(session_id)
    return [_row_to_message(row) for row in rows]


@router.delete("/sessions/{session_id}")
async def remove_chat_session(session_id: UUID, workspace_id: str = Query(...)) -> dict:
    resolved = await resolve_workspace_id(workspace_id)
    if resolved is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    removed = await delete_chat_session(session_id, resolved)
    if not removed:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {"status": "deleted", "id": str(session_id)}


@router.patch("/sessions/{session_id}", response_model=ChatSessionPreview)
async def update_chat_session(session_id: UUID, body: ChatSessionUpdate) -> ChatSessionPreview:
    resolved = await resolve_workspace_id(body.workspace_id)
    if resolved is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    title = _clean_session_title(body.title)
    renamed = await rename_chat_session(session_id, resolved, title)
    if not renamed:
        raise HTTPException(status_code=404, detail="Chat session not found")

    row = await get_chat_session(session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return _row_to_session(row)


@router.post("", response_model=ChatResponse)
async def chat_with_documents(payload: ChatRequest) -> ChatResponse:
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    resolved_workspace_id = await resolve_workspace_id(payload.workspace_id)
    if resolved_workspace_id is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    session_id = await _resolve_or_create_session(
        payload.session_id,
        resolved_workspace_id,
        title=_title_from_question(question),
    )
    history_rows = await list_chat_messages(session_id)
    await _rename_empty_default_session(
        session_id=session_id,
        workspace_id=resolved_workspace_id,
        history_rows=history_rows,
        first_question=question,
    )

    try:
        query_vector = await embed_query(question)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Embedding service unavailable: {exc}",
        )

    results = await similarity_search(
        workspace_id=resolved_workspace_id,
        query_embedding=query_vector,
        top_k=_TOP_K,
        similarity_threshold=_SIMILARITY_THRESHOLD,
    )

    if results:
        context = _build_context([result.content for result in results])
        sources = [result.content for result in results]
        source_chunk_ids = [result.chunk_id for result in results]
    else:
        context = "Không tìm thấy tài liệu liên quan trong workspace này."
        sources = []
        source_chunk_ids = []

    await insert_chat_message(
        session_id=session_id,
        role="user",
        content=question,
        source_chunks=[],
    )

    answer = await ask_llm(
        question=question,
        context=context,
        history=history_rows,
    )

    await insert_chat_message(
        session_id=session_id,
        role="assistant",
        content=answer,
        source_chunks=source_chunk_ids,
    )

    return ChatResponse(answer=answer, session_id=session_id, sources=sources)


async def _resolve_or_create_session(
    session_id: UUID | None,
    workspace_id: UUID,
    title: str = "New chat",
) -> UUID:
    if session_id is None:
        session = await create_chat_session(workspace_id, title=title)
        return UUID(str(session["id"]))

    session = await get_chat_session(session_id)
    if not session or UUID(str(session["workspace_id"])) != workspace_id:
        raise HTTPException(status_code=404, detail="Chat session not found")

    return session_id


def _build_context(chunks: list[str]) -> str:
    return "\n".join(
        f"[Chunk {index + 1}]: {chunk}"
        for index, chunk in enumerate(chunks)
    )


def _row_to_session(row: dict) -> ChatSessionPreview:
    return ChatSessionPreview(
        id=row["id"],
        workspace_id=row["workspace_id"],
        title=row.get("title") or "New chat",
        created_at=row["created_at"],
    )


def _row_to_message(row: dict) -> ChatMessageRecord:
    return ChatMessageRecord(
        id=row["id"],
        session_id=row["session_id"],
        role=row["role"],
        content=row["content"],
        source_chunks=row.get("source_chunks") or [],
        created_at=row["created_at"],
    )


async def _rename_empty_default_session(
    session_id: UUID,
    workspace_id: UUID,
    history_rows: list[dict],
    first_question: str,
) -> None:
    if history_rows:
        return

    session = await get_chat_session(session_id)
    if not session:
        return

    if (session.get("title") or "New chat") != "New chat":
        return

    await rename_chat_session(session_id, workspace_id, _title_from_question(first_question))


def _clean_session_title(title: str | None) -> str:
    cleaned = (title or "New chat").strip()
    return cleaned[:80] if cleaned else "New chat"


def _title_from_question(question: str) -> str:
    return _clean_session_title(question)

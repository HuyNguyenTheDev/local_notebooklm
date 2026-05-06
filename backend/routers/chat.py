"""
routers/chat.py — RAG chat endpoint.

POST /chat
  1. Embed câu hỏi → query_vector
  2. Vector similarity search (pgvector) trong workspace → top-K chunks
  3. Ghép chunks thành context
  4. Gọi LLM (polling) → answer
  5. Trả về answer + sources
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.models.document import ChatRequest, ChatResponse
from backend.services.embedding import embed_query
from backend.services.llm_client import ask_llm
from backend.services.vector_store import resolve_workspace_id, similarity_search

router = APIRouter(prefix="/chat", tags=["chat"])

_TOP_K = 5
_SIMILARITY_THRESHOLD = 0.3   # cosine similarity tối thiểu (0.0–1.0)


@router.post("", response_model=ChatResponse)
async def chat_with_documents(payload: ChatRequest) -> ChatResponse:
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    resolved = await resolve_workspace_id(payload.workspace_id)
    if resolved is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # --- Bước 1: Embed câu hỏi ---
    try:
        query_vector = await embed_query(question)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Embedding service unavailable: {exc}",
        )

    # --- Bước 2: Vector similarity search ---
    results = await similarity_search(
        workspace_id=resolved,
        query_embedding=query_vector,
        top_k=_TOP_K,
        similarity_threshold=_SIMILARITY_THRESHOLD,
    )

    # --- Bước 3: Build context ---
    if results:
        # Sắp xếp theo similarity DESC (đã sorted từ query)
        context_parts = [r.content for r in results]
        context = "\n\n---\n\n".join(context_parts)
        sources = context_parts
    else:
        context = "Không tìm thấy tài liệu liên quan trong workspace này."
        sources = []

    # --- Bước 4: Gọi LLM ---
    answer = await ask_llm(question=question, context=context)

    return ChatResponse(answer=answer, sources=sources)

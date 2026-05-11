"""
routers/embeddings.py — Embedding endpoint (batch up to 16) and store into chunks.
"""

from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.config import EMBED_MODEL
from backend.services.embedding import embed_texts
from backend.services.vector_store import insert_chunks, refresh_bm25_for_file, resolve_workspace_id

router = APIRouter(prefix="/embeddings", tags=["embeddings"])

_MAX_BATCH = 16


class EmbeddingRequest(BaseModel):
    workspace_id: str
    file_id: UUID
    texts: List[str] = Field(min_length=1)
    embed_model: str | None = None


class EmbeddingItem(BaseModel):
    chunk_index: int
    token_count: int
    content_preview: str
    embedding_dim: int


class EmbeddingResponse(BaseModel):
    status: str
    workspace_id: str
    file_id: str
    count: int
    embed_model: str
    items: List[EmbeddingItem]


@router.post("", response_model=EmbeddingResponse)
async def create_embeddings(payload: EmbeddingRequest) -> EmbeddingResponse:
    if len(payload.texts) > _MAX_BATCH:
        raise HTTPException(status_code=400, detail=f"Batch size exceeds {_MAX_BATCH}")

    resolved = await resolve_workspace_id(payload.workspace_id)
    if resolved is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    texts = [t.strip() for t in payload.texts if t.strip()]
    if not texts:
        raise HTTPException(status_code=400, detail="texts cannot be empty")

    embed_model = payload.embed_model or EMBED_MODEL
    embeddings, token_counts = await embed_texts(texts)
    await insert_chunks(
        file_id=payload.file_id,
        workspace_id=resolved,
        chunks=texts,
        embeddings=embeddings,
        token_counts=token_counts,
        embed_model=embed_model,
    )
    await refresh_bm25_for_file(payload.file_id)

    items: List[EmbeddingItem] = []
    for idx, (text, vec, token_count) in enumerate(zip(texts, embeddings, token_counts)):
        items.append(
            EmbeddingItem(
                chunk_index=idx,
                token_count=token_count,
                content_preview=text[:200],
                embedding_dim=len(vec),
            )
        )

    return EmbeddingResponse(
        status="ok",
        workspace_id=str(resolved),
        file_id=str(payload.file_id),
        count=len(items),
        embed_model=embed_model,
        items=items,
    )

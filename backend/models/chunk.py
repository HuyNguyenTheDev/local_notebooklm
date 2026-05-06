"""
models/chunk.py — Pydantic schemas cho Chunk và kết quả vector search.
"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ChunkRecord(BaseModel):
    """Đại diện một hàng trong bảng `chunks`."""

    id: UUID
    file_id: UUID
    workspace_id: UUID
    chunk_index: int
    content: str
    token_count: Optional[int] = None
    embed_model: Optional[str] = None
    # embedding không expose ra ngoài trong response


class ChunkSearchResult(BaseModel):
    """Kết quả trả về từ vector similarity search."""

    chunk_id: UUID
    file_id: UUID
    content: str
    similarity: float

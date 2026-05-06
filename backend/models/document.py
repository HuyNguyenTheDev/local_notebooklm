"""
models/document.py — Pydantic schemas (cập nhật cho Supabase).

WorkspacePreview: dùng UUID id thay vì workspace_id string cũ.
DocumentPreview : thêm parse_status để frontend biết tiến độ ingest.
"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Workspace
# ---------------------------------------------------------------------------

class WorkspaceCreate(BaseModel):
    name: str


class WorkspacePreview(BaseModel):
    id: UUID
    name: str
    created_at: str


# ---------------------------------------------------------------------------
# File / Document
# ---------------------------------------------------------------------------

class DocumentPreview(BaseModel):
    id: UUID
    workspace_id: UUID
    filename: str
    file_type: str
    parse_status: str           # 'pending' | 'processing' | 'done' | 'failed'
    preview: Optional[str] = None
    created_at: str


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    question: str
    workspace_id: str          # UUID hoặc name của workspace


class ChatResponse(BaseModel):
    answer: str
    sources: list[str] = []     # danh sách chunk content dùng làm context

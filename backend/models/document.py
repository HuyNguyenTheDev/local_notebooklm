"""
models/document.py - Pydantic schemas for workspace, documents, and chat.
"""

from typing import Literal, Optional
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
    parse_status: str
    preview: Optional[str] = None
    created_at: str


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    question: str
    workspace_id: str
    session_id: Optional[UUID] = None
    search_mode: Literal["vector", "bm25", "hybrid"] = "vector"


class ChatResponse(BaseModel):
    answer: str
    session_id: UUID
    sources: list[str] = []


class ChatSessionCreate(BaseModel):
    workspace_id: str
    title: Optional[str] = None


class ChatSessionUpdate(BaseModel):
    workspace_id: str
    title: str


class ChatSessionPreview(BaseModel):
    id: UUID
    workspace_id: UUID
    title: str
    created_at: str


class ChatMessageRecord(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    source_chunks: list[UUID] = []
    created_at: str

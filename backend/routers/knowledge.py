"""
routers/knowledge.py — Workspace và Document management endpoints.

Endpoints:
  GET    /documents/workspaces          → list_workspaces
  POST   /documents/workspaces          → create_workspace
  GET    /documents/workspaces/search   → search_workspaces
  DELETE /documents/workspace/{id}      → delete_workspace
  GET    /documents                     → list files in workspace
  GET    /documents/{file_id}/status    → get ingest status
  DELETE /documents/{file_id}           → delete file
  PATCH  /documents/{file_id}           → rename file
"""

from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from backend.models.document import DocumentPreview, WorkspaceCreate, WorkspacePreview
from backend.services.vector_store import (
    create_workspace,
    delete_file,
    delete_workspace,
    get_file,
    list_files,
    list_workspaces,
    rename_file,
    resolve_workspace_id,
    search_workspaces,
)

router = APIRouter(prefix="/documents", tags=["knowledge"])


# ---------------------------------------------------------------------------
# Workspace endpoints
# ---------------------------------------------------------------------------


@router.get("/workspaces", response_model=List[WorkspacePreview])
async def get_workspaces() -> List[WorkspacePreview]:
    rows = await list_workspaces()
    return [_row_to_workspace(r) for r in rows]


@router.post("/workspaces", response_model=WorkspacePreview, status_code=201)
async def create_workspace_endpoint(body: WorkspaceCreate) -> WorkspacePreview:
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Workspace name cannot be empty")
    row = await create_workspace(body.name.strip())
    return _row_to_workspace(row)


@router.get("/workspaces/search", response_model=List[WorkspacePreview])
async def search_workspaces_endpoint(q: str = Query(default="")) -> List[WorkspacePreview]:
    rows = await search_workspaces(q.strip())
    return [_row_to_workspace(r) for r in rows]


@router.delete("/workspace/{workspace_id}")
async def remove_workspace(workspace_id: str) -> dict:
    resolved = await resolve_workspace_id(workspace_id)
    if resolved is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    deleted_files = await delete_workspace(resolved)
    return {
        "status": "deleted",
        "workspace_id": str(resolved),
        "deleted_files": deleted_files,
    }


# ---------------------------------------------------------------------------
# File/Document endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=List[DocumentPreview])
async def get_documents(workspace_id: str = Query(...)) -> List[DocumentPreview]:
    resolved = await resolve_workspace_id(workspace_id)
    if resolved is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    rows = await list_files(resolved)
    return [_row_to_doc(r) for r in rows]


@router.get("/{file_id}/status")
async def get_file_status(file_id: UUID) -> dict:
    """Polling endpoint để frontend kiểm tra tiến độ ingest."""
    row = await get_file(file_id)
    if not row:
        raise HTTPException(status_code=404, detail="File not found")
    return {
        "file_id": str(file_id),
        "filename": row["filename"],
        "parse_status": row["parse_status"],
    }


@router.delete("/{file_id}")
async def remove_document(file_id: UUID, workspace_id: str = Query(...)) -> dict:
    resolved = await resolve_workspace_id(workspace_id)
    if resolved is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    removed = await delete_file(file_id, resolved)
    if not removed:
        raise HTTPException(status_code=404, detail="File not found")
    return {"status": "deleted", "id": str(file_id)}


@router.patch("/{file_id}")
async def update_document(
    file_id: UUID,
    new_filename: str = Query(...),
    workspace_id: str = Query(...),
) -> dict:
    resolved = await resolve_workspace_id(workspace_id)
    if resolved is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    renamed = await rename_file(file_id, resolved, new_filename)
    if not renamed:
        raise HTTPException(status_code=404, detail="File not found")
    return {"status": "renamed", "id": str(file_id), "new_filename": new_filename}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row_to_workspace(row: dict) -> WorkspacePreview:
    return WorkspacePreview(
        id=row["id"],
        name=row["name"],
        created_at=row["created_at"],
    )


def _row_to_doc(row: dict) -> DocumentPreview:
    return DocumentPreview(
        id=row["id"],
        workspace_id=row["workspace_id"],
        filename=row["filename"],
        file_type=row["file_type"],
        parse_status=row["parse_status"],
        created_at=row["created_at"],
    )

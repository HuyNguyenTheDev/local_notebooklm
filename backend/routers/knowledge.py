from typing import List

from fastapi import APIRouter, HTTPException, Query

from backend.models.document import DocumentPreview, WorkspacePreview
from backend.services.knowledge_store import create_workspace, delete_document, delete_workspace, list_document_previews, list_workspaces, rename_document, search_workspaces


router = APIRouter(prefix="/documents", tags=["knowledge"])


@router.get("/workspaces", response_model=List[WorkspacePreview])
def get_workspaces() -> List[WorkspacePreview]:
    return list_workspaces()


@router.post("/workspaces", response_model=WorkspacePreview)
def create_workspace_endpoint(workspace_id: str = Query(...)) -> WorkspacePreview:
    return create_workspace(workspace_id)


@router.get("/workspaces/search", response_model=List[WorkspacePreview])
def search_workspaces_endpoint(q: str = Query(default="")) -> List[WorkspacePreview]:
    return search_workspaces(q)


@router.get("", response_model=List[DocumentPreview])
def get_documents(workspace_id: str = Query(...)) -> List[DocumentPreview]:
    return list_document_previews(workspace_id=workspace_id)


@router.delete("/{doc_id}")
def remove_document(doc_id: str, workspace_id: str = Query(...)) -> dict:
    removed = delete_document(doc_id, workspace_id=workspace_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Document not found")

    return {"status": "deleted", "id": doc_id}


@router.delete("/workspace/{workspace_id}")
def remove_workspace(workspace_id: str) -> dict:
    deleted_count = delete_workspace(workspace_id=workspace_id)
    return {"status": "deleted", "workspace_id": workspace_id, "deleted_documents": deleted_count}


@router.patch("/{doc_id}")
def update_document(doc_id: str, new_filename: str = Query(...), workspace_id: str = Query(...)) -> dict:
    renamed = rename_document(doc_id, workspace_id, new_filename)
    if not renamed:
        raise HTTPException(status_code=404, detail="Document not found")

    return {"status": "renamed", "id": doc_id, "new_filename": new_filename}

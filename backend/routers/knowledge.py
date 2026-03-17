from typing import List

from fastapi import APIRouter, HTTPException, Query

from backend.models.document import DocumentPreview
from backend.services.knowledge_store import delete_document, list_document_previews, rename_document


router = APIRouter(prefix="/documents", tags=["knowledge"])


@router.get("", response_model=List[DocumentPreview])
def get_documents(workspace_id: str = Query(...)) -> List[DocumentPreview]:
    return list_document_previews(workspace_id=workspace_id)


@router.delete("/{doc_id}")
def remove_document(doc_id: str, workspace_id: str = Query(...)) -> dict:
    removed = delete_document(doc_id, workspace_id=workspace_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Document not found")

    return {"status": "deleted", "id": doc_id}


@router.patch("/{doc_id}")
def update_document(doc_id: str, new_filename: str = Query(...), workspace_id: str = Query(...)) -> dict:
    renamed = rename_document(doc_id, workspace_id, new_filename)
    if not renamed:
        raise HTTPException(status_code=404, detail="Document not found")

    return {"status": "renamed", "id": doc_id, "new_filename": new_filename}

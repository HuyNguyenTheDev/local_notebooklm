from typing import List

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.models.document import DocumentPreview
from backend.services.file_parser import SUPPORTED_EXTENSIONS
from backend.services.knowledge_store import save_uploaded_file


router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("", response_model=List[DocumentPreview])
async def upload_files(
    files: List[UploadFile] = File(...),
    workspace_id: str = Form(...),
) -> List[DocumentPreview]:
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    if not workspace_id.strip():
        raise HTTPException(status_code=400, detail="workspace_id is required")

    uploaded: List[DocumentPreview] = []

    for file in files:
        extension = ("." + file.filename.split(".")[-1].lower()) if "." in file.filename else ""
        if extension not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type for {file.filename}. Allowed: pdf, txt, md",
            )

        content = await file.read()
        document = save_uploaded_file(file.filename, content, workspace_id=workspace_id)

        uploaded.append(
            DocumentPreview(
                id=document.id,
                filename=document.filename,
                type=document.type,
                preview=document.text[:300],
                created_at=document.created_at,
            )
        )

    return uploaded

"""
routers/upload.py — Upload file endpoint.

POST /upload
  - Nhận file(s) + workspace_id (UUID)
  - Lưu file tạm lên disk
  - Insert bản ghi vào bảng `files` (status='pending')
  - Kick off background ingest task
  - Trả về DocumentPreview ngay (không chờ ingest)
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import List
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from backend.models.document import DocumentPreview
from backend.services.file_parser import SUPPORTED_EXTENSIONS
from backend.services.ingest import ingest_file
from backend.services.vector_store import create_file_record, resolve_workspace_id

UPLOADS_DIR = Path(__file__).resolve().parents[1] / "data" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("", response_model=List[DocumentPreview])
async def upload_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    workspace_id: str = Form(...),
) -> List[DocumentPreview]:
    """
    Upload 1 hoặc nhiều file vào workspace.
    File được lưu tạm → ingest pipeline chạy background.
    Response trả về ngay với parse_status='pending'.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    results: List[DocumentPreview] = []

    resolved_workspace_id = await resolve_workspace_id(workspace_id, create_if_missing=True)
    if resolved_workspace_id is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    for file in files:
        # Validate extension
        ext = ("." + file.filename.split(".")[-1].lower()) if "." in file.filename else ""
        if ext not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '{ext}' for {file.filename}. Allowed: pdf, txt, md",
            )

        # Đọc content
        content = await file.read()

        # Lưu file tạm lên disk
        file_id = uuid.uuid4()
        stored_name = f"{file_id}{ext}"
        stored_path = UPLOADS_DIR / stored_name
        stored_path.write_bytes(content)

        # Insert bản ghi vào DB (status='pending')
        file_type = ext.lstrip(".")
        record = await create_file_record(
            workspace_id=resolved_workspace_id,
            filename=file.filename,
            file_type=file_type,
            parse_status="pending",
        )

        file_uuid = UUID(record["id"])

        # Kick off background ingest
        background_tasks.add_task(ingest_file, file_uuid, resolved_workspace_id, stored_path)

        results.append(
            DocumentPreview(
                id=file_uuid,
                workspace_id=resolved_workspace_id,
                filename=file.filename,
                file_type=file_type,
                parse_status="pending",
                created_at=record["created_at"],
            )
        )

    return results

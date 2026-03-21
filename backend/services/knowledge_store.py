import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List
from uuid import uuid4

from backend.models.document import Document, DocumentPreview, WorkspacePreview
from backend.services.file_parser import parse_file


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
METADATA_PATH = DATA_DIR / "metadata.json"

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
if not METADATA_PATH.exists():
    METADATA_PATH.write_text("[]", encoding="utf-8")


def save_uploaded_file(filename: str, content: bytes, workspace_id: str) -> Document:
    file_id = str(uuid4())
    safe_name = Path(filename).name
    extension = Path(safe_name).suffix.lower()
    stored_name = f"{file_id}{extension}"
    stored_path = UPLOADS_DIR / stored_name

    stored_path.write_bytes(content)

    text = parse_file(stored_path)
    created_at = datetime.now(timezone.utc).isoformat()

    document = Document(
        id=file_id,
        workspace_id=workspace_id,
        filename=safe_name,
        type=extension.replace(".", ""),
        text=text,
        created_at=created_at,
        path=str(stored_path),
    )

    docs = _load_documents()
    docs.append(document)
    _save_documents(docs)

    return document


def list_document_previews(workspace_id: str, limit: int = 300) -> List[DocumentPreview]:
    docs = [doc for doc in _load_documents() if doc.workspace_id == workspace_id]
    return [
        DocumentPreview(
            id=doc.id,
            filename=doc.filename,
            type=doc.type,
            preview=doc.text[:limit],
            created_at=doc.created_at,
        )
        for doc in docs
    ]


def list_documents(workspace_id: str) -> List[Document]:
    return [doc for doc in _load_documents() if doc.workspace_id == workspace_id]


def list_workspaces() -> List[WorkspacePreview]:
    workspaces: dict[str, datetime] = {}
    for doc in _load_documents():
        workspace_id = doc.workspace_id.strip()
        if not workspace_id:
            continue

        created_at = _parse_datetime(doc.created_at)
        previous = workspaces.get(workspace_id)
        if previous is None or created_at < previous:
            workspaces[workspace_id] = created_at

    ordered = sorted(workspaces.items(), key=lambda item: item[1], reverse=True)
    return [
        WorkspacePreview(workspace_id=workspace_id, created_at=created_at.isoformat())
        for workspace_id, created_at in ordered
    ]


def delete_document(doc_id: str, workspace_id: str) -> bool:
    docs = _load_documents()
    target = next((doc for doc in docs if doc.id == doc_id and doc.workspace_id == workspace_id), None)
    if target is None:
        return False

    path = Path(target.path)
    if path.exists():
        path.unlink()

    updated = [doc for doc in docs if doc.id != doc_id]
    _save_documents(updated)
    return True


def delete_workspace(workspace_id: str) -> int:
    docs = _load_documents()
    targets = [doc for doc in docs if doc.workspace_id == workspace_id]

    for doc in targets:
        path = Path(doc.path)
        if path.exists():
            path.unlink()

    updated = [doc for doc in docs if doc.workspace_id != workspace_id]
    _save_documents(updated)
    return len(targets)


def rename_document(doc_id: str, workspace_id: str, new_filename: str) -> bool:
    docs = _load_documents()
    target = next((doc for doc in docs if doc.id == doc_id and doc.workspace_id == workspace_id), None)
    if target is None:
        return False

    target.filename = new_filename
    _save_documents(docs)
    return True


def _load_documents() -> List[Document]:
    raw = METADATA_PATH.read_text(encoding="utf-8")
    data = json.loads(raw)
    normalized = []
    for item in data:
        if "workspace_id" not in item:
            item["workspace_id"] = "default"
        normalized.append(Document(**item))
    return normalized


def _save_documents(documents: List[Document]) -> None:
    payload = [doc.model_dump() for doc in documents]
    METADATA_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _parse_datetime(raw_value: str) -> datetime:
    try:
        return datetime.fromisoformat(raw_value)
    except ValueError:
        return datetime.fromtimestamp(0, tz=timezone.utc)

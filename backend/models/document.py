from pydantic import BaseModel


class Document(BaseModel):
    id: str
    workspace_id: str
    filename: str
    type: str
    text: str
    created_at: str
    path: str


class DocumentPreview(BaseModel):
    id: str
    filename: str
    type: str
    preview: str
    created_at: str


class ChatRequest(BaseModel):
    question: str
    workspace_id: str


class ChatResponse(BaseModel):
    answer: str

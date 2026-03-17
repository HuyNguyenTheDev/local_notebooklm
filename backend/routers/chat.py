from fastapi import APIRouter, HTTPException

from backend.models.document import ChatRequest, ChatResponse
from backend.services.knowledge_store import list_documents
from backend.services.llm_client import ask_llm


router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat_with_documents(payload: ChatRequest) -> ChatResponse:
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    workspace_id = payload.workspace_id.strip()
    if not workspace_id:
        raise HTTPException(status_code=400, detail="workspace_id is required")

    documents = list_documents(workspace_id=workspace_id)
    context = "\n\n".join(doc.text for doc in documents if doc.text.strip())

    if not context:
        context = "No documents available in knowledge store."

    answer = await ask_llm(question=question, context=context)
    return ChatResponse(answer=answer)

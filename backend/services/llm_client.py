"""
services/llm_client.py - Worker LLM client for RAG chat.

Expected Worker API:
  POST {LLM_API_URL}
  Authorization: Bearer {LLM_API_KEY}
  JSON: {"prompt": "...", "systemPrompt": "..."}
  Response: {"response": "..."} or any JSON/string fallback.
"""

from __future__ import annotations

from typing import Iterable

import httpx

from backend.config import LLM_API_KEY, LLM_API_URL


SYSTEM_PROMPT = """Bạn là trợ lý AI IT. Hãy trả lời câu hỏi của người dùng dựa trên các đoạn văn bản được cung cấp và lịch sử hội thoại.
Nếu thông tin không có trong context, hãy nói rõ là bạn không tìm thấy thông tin đó.
Không được bịa đặt thông tin ngoài context và lịch sử hội thoại."""


async def ask_llm(
    question: str,
    context: str,
    history: Iterable[dict] | None = None,
) -> str:
    """Send a RAG prompt to the configured Worker LLM API."""
    if not LLM_API_URL:
        return "Chưa cấu hình LLM_API_URL trong .env."

    prompt = _build_rag_prompt(question=question, context=context, history=history or [])
    headers = {"Content-Type": "application/json"}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"

    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                LLM_API_URL,
                headers=headers,
                json={
                    "prompt": prompt,
                    "systemPrompt": SYSTEM_PROMPT,
                },
            )
            response.raise_for_status()
    except Exception as exc:
        print(f"[ERROR] ask_llm worker request failed: {exc}")
        return f"Không thể kết nối tới LLM API: {exc}"

    return _extract_response(response)


def _build_rag_prompt(question: str, context: str, history: Iterable[dict]) -> str:
    history_text = _build_history(history)
    safe_context = context.strip() if context.strip() else "Không có context liên quan."

    return f"""Context:
{safe_context}

Lịch sử hội thoại:
{history_text}

Câu hỏi: {question}"""


def _build_history(history: Iterable[dict]) -> str:
    lines: list[str] = []
    for message in history:
        role = message.get("role", "")
        content = str(message.get("content", "")).strip()
        if not content:
            continue
        label = "Người dùng" if role == "user" else "Trợ lý"
        lines.append(f"{label}: {content}")

    return "\n".join(lines[-12:]) if lines else "Chưa có lịch sử."


def _extract_response(response: httpx.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        return response.text

    if isinstance(data, dict):
        for key in ("response", "answer", "result", "content"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value
        return str(data)

    if isinstance(data, str):
        return data

    return str(data)

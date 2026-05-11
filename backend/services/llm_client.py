"""
services/llm_client.py - LLM client for RAG chat.

Current: DPO Model via ngrok
- POST {BASE_URL}/generate to get job_id
- Poll {BASE_URL}/result/{job_id} until done

Legacy (commented out): Worker LLM API
- POST {LLM_API_URL}
- JSON: {"prompt": "...", "systemPrompt": "..."}
"""

from __future__ import annotations

import asyncio
import time
from typing import Iterable

import httpx
import requests

from backend.config import LLM_API_KEY, LLM_API_URL


# ==========================================
# CẤU HÌNH (COMMENTED OUT - DPO MODEL NGROK)
# ==========================================
# DPO_MODEL_BASE_URL = "https://unamendable-shawanda-unregrettably.ngrok-free.dev"

# ==========================================
# LLAMA 3.1 SYSTEM PROMPT (OPTIMIZED)
# ==========================================
# LLaMA 3.1 is optimized for multilingual dialogue and instruction-following
# This prompt is tuned for RAG scenarios with 128k context support
SYSTEM_PROMPT = """Bạn là một trợ lý AI hỏi đáp về IT hỗ trợ các cuộc trò chuyện với tài liệu tham khảo.
Hướng dẫn:
1. Luôn dựa vào Context được cung cấp để trả lời. Context chứa các đoạn văn bản liên quan nhất.
2. Nếu câu trả lời có trong Context: Hãy trích dẫn và giải thích chi tiết, Nếu câu trả lời không có trong Context: Hãy nói rõ "Tôi không tìm thấy thông tin này trong tài liệu của bạn".
3. Hỗ trợ các ngôn ngữ: Tiếng Việt, Tiếng Anh.
4. Không bao giờ bịa đặt thông tin. Chỉ sử dụng Context + Lịch sử hội thoại.
"""


# ==========================================
# DPO MODEL INTEGRATION (LLaMA 3.1) - COMMENTED OUT
# ==========================================
"""
async def ask_llm(
    question: str,
    context: str,
    history: Iterable[dict] | None = None,
) -> str:
    \"\"\"Send a RAG prompt to DPO model via ngrok.\"\"\"
    prompt = _build_rag_prompt(question=question, context=context, history=history or [])
    
    try:
        # 1. Gửi prompt lên /generate endpoint để lấy job_id
        job_id = await _get_job_id(prompt)
        if not job_id:
            return "❌ Không thể lấy Job ID từ DPO Model."
        
        # 2. Poll /result/{job_id} cho đến khi done
        result = await _poll_result(job_id)
        return result
    
    except Exception as exc:
        print(f"[ERROR] DPO Model request failed: {exc}")
        return f"❌ Lỗi kết nối DPO Model: {exc}"


async def _get_job_id(prompt: str) -> str | None:
    \"\"\"POST /generate để lấy job_id\"\"\"
    try:
        # Chạy request trong thread pool vì requests không async
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.post(
                f"{DPO_MODEL_BASE_URL}/generate",
                json={"text": prompt},
                timeout=10
            )
        )
        response.raise_for_status()
        data = response.json()
        return data.get("job_id")
    except Exception as e:
        print(f"[ERROR] _get_job_id failed: {e}")
        return None


async def _poll_result(job_id: str, max_polls: int = 60) -> str:
    \"\"\"Poll /result/{job_id} cho đến khi done (tối đa 60 lần, mỗi 2 giây)\"\"\"
    loop = asyncio.get_event_loop()
    
    for attempt in range(max_polls):
        try:
            response = await loop.run_in_executor(
                None,
                lambda: requests.get(
                    f"{DPO_MODEL_BASE_URL}/result/{job_id}",
                    timeout=10
                )
            )
            response.raise_for_status()
            result_data = response.json()
            status = result_data.get("status")
            
            if status == "done":
                return result_data.get("result", "")
            elif status == "error":
                return f"❌ Server error: {result_data.get('result')}"
            
            # Chờ 2 giây trước khi poll lại
            await asyncio.sleep(2)
            
        except Exception as e:
            print(f"[ERROR] _poll_result attempt {attempt + 1} failed: {e}")
            if attempt == max_polls - 1:
                return f"❌ Poll timeout sau {max_polls} attempts"
            await asyncio.sleep(2)
    
    return "❌ Poll timeout - model không trả lời kịp thời"
"""


def _build_rag_prompt(question: str, context: str, history: Iterable[dict]) -> str:
    """Build optimized prompt for LLaMA 3.1 (128k context support)."""
    history_text = _build_history(history)
    safe_context = context.strip() if context.strip() else "Không có tài liệu liên quan."

    # LLaMA 3.1 performs better with structured, clear formatting
    return f"""[Context]
{safe_context}
[History]
{history_text}
[Current Question]
{question}
"""


def _build_history(history: Iterable[dict]) -> str:
    """Build conversation history with clear role labels (LLaMA 3.1 format)."""
    lines: list[str] = []
    for message in history:
        role = message.get("role", "")
        content = str(message.get("content", "")).strip()
        if not content:
            continue
        # LLaMA 3.1 responds well to clear role markers
        if role == "user":
            lines.append(f"User: {content}")
        elif role == "assistant":
            lines.append(f"Assistant: {content}")
        else:
            lines.append(f"[{role}]: {content}")

    # Keep last 15 messages to maintain context without exceeding limits
    if lines:
        return "\n".join(lines[-15:])
    return "(Chưa có lịch sử)"


# ==========================================
# CLOUDFLARE LLMs / OPENROUTER / WORKER API
# ==========================================

async def ask_llm(
    question: str,
    context: str,
    history: Iterable[dict] | None = None,
) -> str:
    """Send a RAG prompt to the configured Worker LLM API (Cloudflare/OpenRouter)."""
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
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:500] if exc.response is not None else ""
        print(
            "[ERROR] ask_llm worker HTTP error: "
            f"status={exc.response.status_code if exc.response else 'unknown'} body={body}"
        )
        return f"Không thể kết nối tới LLM API: HTTP {exc.response.status_code if exc.response else 'unknown'}"
    except Exception as exc:
        print(f"[ERROR] ask_llm worker request failed: {exc}")
        return f"Không thể kết nối tới LLM API: {exc}"

    return _extract_response(response)


def _extract_response(response: httpx.Response) -> str:
    """Extract response from LLM API."""
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

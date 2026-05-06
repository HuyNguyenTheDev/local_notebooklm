"""
services/llm_client.py — Goi LLM API voi co che polling.

Giu nguyen polling mechanism tu test_llm_api.py:
  POST /generate -> {"job_id": "..."}
  GET  /result/{job_id} -> {"status": "done"|"pending"|"error", "result": "..."}
"""

import asyncio

import httpx

from backend.config import LLM_API_URL

# Chuan hoa: bo trailing slash va /generate /chat
_base = LLM_API_URL.rstrip("/")
if _base.endswith("/generate"):
    _base = _base[: -len("/generate")]
elif _base.endswith("/chat"):
    _base = _base[: -len("/chat")]
LLM_BASE_URL: str = _base

_POLL_INTERVAL = 1.5
_MAX_POLLS = 120


async def ask_llm(question: str, context: str) -> str:
    """
    Gui cau hoi + context len LLM API (polling mode).
    Prompt duoc xay dung theo format RAG chuan.
    """
    prompt = _build_rag_prompt(question, context)

    job_id = await _submit_job(prompt)
    if not job_id:
        return "Khong the ket noi toi LLM server. Kiem tra LLM_API_URL trong .env"

    return await _poll_result(job_id)


def _build_rag_prompt(question: str, context: str) -> str:
    if context and context.strip():
        return (
            "Dua tren cac doan van ban tham khao sau day, hay tra loi cau hoi.\n"
            "Neu khong tim thay thong tin lien quan trong ngu canh, hay noi ro dieu do.\n\n"
            f"=== NGU CANH ===\n{context}\n\n"
            f"=== CAU HOI ===\n{question}\n\n"
            "=== TRA LOI ==="
        )
    return question


async def _submit_job(prompt: str) -> str | None:
    """POST /generate -> lay job_id."""
    payload = {"text": prompt}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(f"{LLM_BASE_URL}/generate", json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("job_id")
    except Exception as exc:
        print(f"[ERROR] _submit_job: {exc}")
        return None


async def _poll_result(job_id: str) -> str:
    """GET /result/{job_id} voi polling cho den khi done."""
    for poll_num in range(_MAX_POLLS):
        await asyncio.sleep(_POLL_INTERVAL)
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(f"{LLM_BASE_URL}/result/{job_id}")
                response.raise_for_status()
                data = response.json()

            status = data.get("status")
            if status == "done":
                return data.get("result", "Khong co ket qua tu LLM.")
            elif status == "error":
                return f"LLM server bao loi: {data.get('result', 'Unknown error')}"

        except Exception as exc:
            print(f"[WARN] poll #{poll_num + 1}: {exc}")

    return f"Timeout: LLM khong phan hoi sau {_MAX_POLLS * _POLL_INTERVAL:.0f} giay."

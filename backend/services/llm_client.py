import os

import httpx


LLM_API_URL = os.getenv("LLM_API_URL", "http://127.0.0.1:8001/chat")


async def ask_llm(question: str, context: str) -> str:
    payload = {"question": question, "context": context}

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(LLM_API_URL, json=payload)
        response.raise_for_status()
        data = response.json()

    return data.get("answer", "No answer returned from LLM server.")

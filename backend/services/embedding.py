"""
services/embedding.py — Goi Embedding API de tao vector tu text.

Format request (POST EMBEDDING_API_URL):
  {"texts": ["doan 1", "doan 2", ...]}   <- batch

Format response:
  {"embeddings": [[0.1, 0.2, ...], ...]}
  hoac
  {"data": [{"embedding": [...]}, ...]}   <- OpenAI-compatible
"""

import httpx

from backend.config import (
    EMBED_MODEL,
    EMBEDDING_API_URL,
    EMBEDDING_DIM,
    OPENROUTER_API_KEY,
    OPENROUTER_SITE_NAME,
    OPENROUTER_SITE_URL,
)

_BATCH_SIZE = 16


async def embed_texts(texts: list[str]) -> tuple[list[list[float]], list[int]]:
    """
    Nhan list text -> tra ve tuple (list vector embedding, list so token).
    Tu dong chia batch neu len(texts) > _BATCH_SIZE.
    """
    if not texts:
        return [], []

    if not EMBEDDING_API_URL:
        raise RuntimeError(
            "EMBEDDING_API_URL chua duoc set trong .env. "
            "Them dong: EMBEDDING_API_URL=https://xxxx.ngrok-free.app/embed"
        )

    results_vectors: list[list[float]] = []
    results_tokens: list[int] = []
    
    for i in range(0, len(texts), _BATCH_SIZE):
        batch = texts[i : i + _BATCH_SIZE]
        vectors, batch_tokens = await _call_embed_api(batch)
        results_vectors.extend(vectors)
        
        # Phân bổ tổng số token của batch cho từng chunk dựa trên độ dài ký tự
        total_chars = sum(len(t) for t in batch)
        if total_chars > 0 and batch_tokens > 0:
            for t in batch:
                chunk_tokens = max(1, int(batch_tokens * (len(t) / total_chars)))
                results_tokens.append(chunk_tokens)
        else:
            results_tokens.extend([0] * len(batch))
            
    return results_vectors, results_tokens


async def embed_query(text: str) -> list[float]:
    """Embed 1 cau query -> 1 vector."""
    vectors, _ = await embed_texts([text])
    return vectors[0]


async def _call_embed_api(texts: list[str]) -> tuple[list[list[float]], int]:
    """Goi external embedding API va parse ket qua."""
    if not EMBEDDING_API_URL:
        raise RuntimeError("EMBEDDING_API_URL is not set")

    is_openrouter = "openrouter.ai/api/v1/embeddings" in EMBEDDING_API_URL

    if is_openrouter:
        if not OPENROUTER_API_KEY:
            raise RuntimeError("OPENROUTER_API_KEY is not set")

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        if OPENROUTER_SITE_URL:
            headers["HTTP-Referer"] = OPENROUTER_SITE_URL
        if OPENROUTER_SITE_NAME:
            headers["X-OpenRouter-Title"] = OPENROUTER_SITE_NAME

        payload = {
            "model": EMBED_MODEL,
            "input": texts,
            "encoding_format": "float",
        }
        # Thêm dimensions=1024 cho model BAAI/bge-m3 theo yêu cầu
        if "bge-m3" in EMBED_MODEL.lower():
            payload["dimensions"] = 1024
    else:
        headers = {"Content-Type": "application/json"}
        payload = {"texts": texts}

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(EMBEDDING_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    total_tokens = 0
    if "usage" in data:
        total_tokens = data["usage"].get("total_tokens", data["usage"].get("prompt_tokens", 0))

    # Format 1: {"embeddings": [[...]]}
    if "embeddings" in data:
        return data["embeddings"], total_tokens

    # Format 2: {"data": [{"embedding": [...]}, ...]} (OpenAI-compatible)
    if "data" in data:
        vectors = [item["embedding"] for item in data["data"]]
        return vectors, total_tokens

    raise ValueError(f"Unrecognized embedding API response format: {list(data.keys())}")

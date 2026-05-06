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

from backend.config import EMBED_MODEL, EMBEDDING_API_URL, EMBEDDING_DIM

_BATCH_SIZE = 32


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Nhan list text -> tra ve list vector embedding tuong ung.
    Tu dong chia batch neu len(texts) > _BATCH_SIZE.
    """
    if not texts:
        return []

    if not EMBEDDING_API_URL:
        raise RuntimeError(
            "EMBEDDING_API_URL chua duoc set trong .env. "
            "Them dong: EMBEDDING_API_URL=https://xxxx.ngrok-free.app/embed"
        )

    results: list[list[float]] = []
    for i in range(0, len(texts), _BATCH_SIZE):
        batch = texts[i : i + _BATCH_SIZE]
        vectors = await _call_embed_api(batch)
        results.extend(vectors)
    return results


async def embed_query(text: str) -> list[float]:
    """Embed 1 cau query -> 1 vector."""
    vectors = await embed_texts([text])
    return vectors[0]


async def _call_embed_api(texts: list[str]) -> list[list[float]]:
    """Goi external embedding API va parse ket qua."""
    payload = {"texts": texts}

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(EMBEDDING_API_URL, json=payload)
        response.raise_for_status()
        data = response.json()

    # Format 1: {"embeddings": [[...]]}
    if "embeddings" in data:
        return data["embeddings"]

    # Format 2: {"data": [{"embedding": [...]}, ...]} (OpenAI-compatible)
    if "data" in data:
        return [item["embedding"] for item in data["data"]]

    raise ValueError(f"Unrecognized embedding API response format: {list(data.keys())}")

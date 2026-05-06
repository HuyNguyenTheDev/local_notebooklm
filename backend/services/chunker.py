"""
services/chunker.py — Chia raw text thành các chunk có kích thước hợp lý.

Dùng RecursiveCharacterTextSplitter từ langchain-text-splitters:
  - chunk_size   = CHUNK_SIZE env (default 512 tokens)
  - chunk_overlap = CHUNK_OVERLAP env (default 64 tokens)
  - Dùng tiktoken (cl100k_base) để đếm token chính xác.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.config import CHUNK_OVERLAP, CHUNK_SIZE


def _get_splitter() -> RecursiveCharacterTextSplitter:
    """Khởi tạo splitter dùng tiktoken để đếm token."""
    return RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name="cl100k_base",      # GPT-4 tokenizer, gần với bge-m3
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", ".", " ", ""],
    )


def split_text(raw_text: str) -> list[str]:
    """
    Chia raw_text thành list các chunk string.

    Returns:
        List[str] — các đoạn text đã được chia nhỏ.
    """
    if not raw_text or not raw_text.strip():
        return []

    splitter = _get_splitter()
    chunks = splitter.split_text(raw_text)
    # Lọc bỏ chunk rỗng
    return [c.strip() for c in chunks if c.strip()]


def estimate_token_count(text: str) -> int:
    """Ước tính số token của một đoạn text dùng tiktoken."""
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))

"""
services/chunker.py — Chia raw text thành các chunk có kích thước hợp lý.

Dùng RecursiveCharacterTextSplitter từ langchain-text-splitters:
    - chunk_size   = CHUNK_SIZE env
    - chunk_overlap = CHUNK_OVERLAP env
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.config import CHUNK_OVERLAP, CHUNK_SIZE


def _get_splitter() -> RecursiveCharacterTextSplitter:
    """Khởi tạo splitter theo số ký tự (phù hợp với snippet chuẩn)."""
    return RecursiveCharacterTextSplitter(
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

"""
services/chunker.py — Chia raw text thành các chunk có kích thước hợp lý.

Dùng RecursiveCharacterTextSplitter từ langchain-text-splitters:
    - chunk_size   = CHUNK_SIZE env
    - chunk_overlap = CHUNK_OVERLAP env
"""

import re

from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.config import CHUNK_OVERLAP, CHUNK_SIZE

_SECTION_HEADING_RE = re.compile(
    r"^("
    r"abstract|references|acknowledg(e)?ments|appendix|"
    r"\d+(\.\d+)*\.?\s+\S.*"
    r")$",
    re.IGNORECASE,
)
_TITLE_HEADING_RE = re.compile(r"^[A-Z][A-Za-z0-9 ,:/()&-]{0,80}$")
_LIST_OR_CAPTION_RE = re.compile(
    r"^("
    r"[\u2022\-*]\s+|"
    r"\(?[a-zA-Z0-9]{1,3}\)\s+|"
    r"\[[0-9]{1,3}\]\s+|"
    r"(figure|fig\.|table|algorithm|equation)\s+\d+"
    r")",
    re.IGNORECASE,
)
_EMAIL_OR_URL_RE = re.compile(r"(@|https?://|www\.)", re.IGNORECASE)
_SENTENCE_END_RE = re.compile(r"[.!?:;)\]\}\"']$")


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
    chunks = splitter.split_text(normalize_text_for_chunking(raw_text))
    # Lọc bỏ chunk rỗng
    return [c.strip() for c in chunks if c.strip()]


def normalize_text_for_chunking(raw_text: str) -> str:
    """
    Join PDF layout-wrapped prose lines before chunking.

    The stored raw_text remains unchanged; this only prepares text for chunks and
    embeddings. It preserves headings, metadata, lists, captions, and blank-line
    paragraph breaks.
    """
    paragraphs: list[str] = []
    current = ""

    for raw_line in raw_text.replace("\x00", "").splitlines():
        line = _normalize_line(raw_line)
        if not line:
            if current:
                paragraphs.append(current)
                current = ""
            continue

        if not current:
            current = line
            continue

        if _should_start_new_block(current, line):
            paragraphs.append(current)
            current = line
            continue

        current = _join_lines(current, line)

    if current:
        paragraphs.append(current)

    return "\n\n".join(paragraphs)


def _normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def _join_lines(previous: str, current: str) -> str:
    if previous.endswith("-") and current and current[0].islower():
        return previous[:-1] + current
    return f"{previous} {current}"


def _should_start_new_block(previous: str, current: str) -> bool:
    if _is_structural_line(current):
        return True
    if _is_structural_line(previous):
        return True
    if _looks_like_isolated_metadata(previous) or _looks_like_isolated_metadata(current):
        return True
    if _SENTENCE_END_RE.search(previous) and not _looks_like_wrapped_prose(current):
        return True
    if _SENTENCE_END_RE.search(previous) and _is_heading_like(current):
        return True
    return False


def _is_structural_line(line: str) -> bool:
    return (
        _EMAIL_OR_URL_RE.search(line) is not None
        or _LIST_OR_CAPTION_RE.search(line) is not None
        or _is_heading_like(line)
    )


def _is_heading_like(line: str) -> bool:
    words = line.split()
    if len(words) > 12:
        return False
    if _EMAIL_OR_URL_RE.search(line):
        return False
    if _LIST_OR_CAPTION_RE.search(line):
        return True
    if _SECTION_HEADING_RE.match(line):
        return True
    if _TITLE_HEADING_RE.match(line) and not _looks_like_wrapped_prose(line):
        return True
    return False


def _looks_like_wrapped_prose(line: str) -> bool:
    words = line.split()
    alpha_chars = sum(ch.isalpha() for ch in line)
    return len(words) >= 5 and alpha_chars >= max(20, len(line) * 0.55)


def _looks_like_isolated_metadata(line: str) -> bool:
    words = line.split()
    if len(words) > 4:
        return False
    if _EMAIL_OR_URL_RE.search(line):
        return True
    alpha_words = [word for word in words if any(ch.isalpha() for ch in word)]
    if not alpha_words or len(alpha_words) != len(words):
        return False
    return all(_looks_like_name_or_affiliation_word(word) for word in alpha_words)


def _looks_like_name_or_affiliation_word(word: str) -> bool:
    letters = "".join(ch for ch in word if ch.isalpha())
    return bool(letters) and letters[0].isupper()

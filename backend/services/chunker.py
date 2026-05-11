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
    effective_chunk_size = max(256, CHUNK_SIZE - max(0, CHUNK_OVERLAP))
    return RecursiveCharacterTextSplitter(
        chunk_size=effective_chunk_size,
        chunk_overlap=CHUNK_OVERLAP,
        keep_separator="end",
        separators=["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " ", ""],
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
    cleaned_chunks = [_clean_chunk(c) for c in chunks]
    return _add_missing_overlap([c for c in cleaned_chunks if c])


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
    if _SENTENCE_END_RE.search(previous) and _starts_new_sentence_or_block(current):
        return True
    if _SENTENCE_END_RE.search(previous) and _is_heading_like(current):
        return True
    return False


def _starts_new_sentence_or_block(line: str) -> bool:
    first = line[:1]
    if not first:
        return False
    return first.isupper() or first.isdigit() or first in "(["


def _clean_chunk(chunk: str) -> str:
    cleaned = chunk.strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n[ \t]+", "\n", cleaned)
    return cleaned


def _add_missing_overlap(chunks: list[str]) -> list[str]:
    if CHUNK_OVERLAP <= 0 or len(chunks) <= 1:
        return chunks

    overlapped = [chunks[0]]
    for current in chunks[1:]:
        previous = overlapped[-1]
        target_overlap = min(CHUNK_OVERLAP, len(previous))
        if target_overlap <= 0:
            overlapped.append(current)
            continue

        existing_overlap = _shared_suffix_prefix_len(previous, current, target_overlap * 2)
        if existing_overlap >= max(24, target_overlap // 2):
            overlapped.append(current)
            continue

        overlap_prefix = _overlap_prefix(previous, target_overlap)
        if not overlap_prefix:
            overlapped.append(current)
            continue

        if existing_overlap and overlap_prefix.endswith(current[:existing_overlap]):
            current = overlap_prefix + current[existing_overlap:]
        else:
            current = f"{overlap_prefix}\n\n{current}"

        overlapped.append(_clean_chunk(current))

    return overlapped


def _shared_suffix_prefix_len(left: str, right: str, max_chars: int) -> int:
    max_len = min(max_chars, len(left), len(right))
    for size in range(max_len, 0, -1):
        if left[-size:] == right[:size]:
            return size
    return 0


def _overlap_prefix(text: str, max_chars: int) -> str:
    start = max(0, len(text) - max_chars)
    prefix = text[start:]

    if start > 0:
        whitespace_match = re.search(r"\s+", prefix)
        if whitespace_match:
            prefix = prefix[whitespace_match.end():]

    sentence_match = re.search(r"(?<=[.!?;:])\s+[A-Z0-9(\[]", prefix)
    if sentence_match and sentence_match.start() <= max(24, len(prefix) // 3):
        prefix = prefix[sentence_match.start() + 1:]

    return prefix.strip()


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

"""
services/file_parser.py — Parse file thanh raw text.

Chien luoc:
  1. Neu PDF_PARSE_API_URL duoc set -> goi API ngoai.
  2. Fallback -> pypdf local.
  3. txt / md -> doc thang.
"""

from pathlib import Path

import httpx
from pypdf import PdfReader

from backend.config import PDF_PARSE_API_URL

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}


async def parse_file_async(file_path: Path) -> str:
    """Parse file -> raw text string (async)."""
    suffix = file_path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {suffix}")

    if suffix == ".pdf":
        return await _parse_pdf_async(file_path)

    return file_path.read_text(encoding="utf-8", errors="ignore")


async def _parse_pdf_async(file_path: Path) -> str:
    if PDF_PARSE_API_URL:
        try:
            return await _call_pdf_api(file_path)
        except Exception as exc:
            print(f"[WARN] PDF API failed ({exc}), falling back to pypdf")

    return _parse_pdf_local(file_path)


async def _call_pdf_api(file_path: Path) -> str:
    async with httpx.AsyncClient(timeout=120) as client:
        with open(file_path, "rb") as f:
            response = await client.post(
                PDF_PARSE_API_URL,
                files={"file": (file_path.name, f, "application/pdf")},
            )
        response.raise_for_status()
        data = response.json()
        return data.get("text") or data.get("content") or ""


def _parse_pdf_local(file_path: Path) -> str:
    reader = PdfReader(str(file_path))
    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    return "\n".join(page for page in pages if page)

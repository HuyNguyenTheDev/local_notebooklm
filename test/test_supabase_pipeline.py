"""
test_supabase_pipeline.py — Test end-to-end Supabase RAG pipeline.

Chạy: python test_supabase_pipeline.py
Yêu cầu: .env đã cấu hình đúng SUPABASE_URL, DATABASE_URL, EMBEDDING_API_URL
"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env từ backend/
env_path = Path(__file__).parent / "backend" / ".env"
load_dotenv(env_path)

# Thêm project root vào sys.path
sys.path.insert(0, str(Path(__file__).parent))


async def test_workspace_crud():
    """Test tạo/xóa workspace."""
    from backend.services.vector_store import create_workspace, delete_workspace, list_workspaces

    print("\n=== TEST 1: Workspace CRUD ===")

    # Tạo workspace
    ws = await create_workspace("__test_workspace__")
    print(f"✓ Created workspace: id={ws['id']}, name={ws['name']}")

    # List
    all_ws = await list_workspaces()
    assert any(w["id"] == ws["id"] for w in all_ws), "Workspace not found in list"
    print(f"✓ List workspaces: {len(all_ws)} found")

    # Xóa
    import uuid
    deleted = await delete_workspace(uuid.UUID(ws["id"]))
    print(f"✓ Deleted workspace, {deleted} files deleted")


async def test_file_ingest(workspace_id_str: str):
    """Test upload → ingest pipeline với file test."""
    from uuid import UUID
    from backend.services.vector_store import create_file_record, update_file_status
    from backend.services.ingest import ingest_file

    print("\n=== TEST 2: File Ingest Pipeline ===")

    workspace_id = UUID(workspace_id_str)

    # Tạo file test tạm
    test_file = Path(__file__).parent / "backend" / "data" / "uploads" / "__test__.txt"
    test_file.write_text(
        "Supabase là một nền tảng backend mã nguồn mở, "
        "cung cấp cơ sở dữ liệu PostgreSQL, xác thực, lưu trữ file và API tự động. "
        "pgvector là extension của PostgreSQL cho phép lưu trữ và tìm kiếm vector nhúng. "
        "RAG (Retrieval-Augmented Generation) là kỹ thuật kết hợp tìm kiếm ngữ nghĩa với LLM.",
        encoding="utf-8",
    )

    # Tạo record
    record = await create_file_record(
        workspace_id=workspace_id,
        filename="__test__.txt",
        file_type="txt",
        parse_status="pending",
    )
    file_id = UUID(record["id"])
    print(f"✓ File record created: id={file_id}")

    # Chạy ingest
    await ingest_file(file_id, workspace_id, test_file)
    print(f"✓ Ingest pipeline completed")

    return file_id


async def test_vector_search(workspace_id_str: str):
    """Test similarity search."""
    from uuid import UUID
    from backend.services.embedding import embed_query
    from backend.services.vector_store import similarity_search

    print("\n=== TEST 3: Vector Similarity Search ===")

    workspace_id = UUID(workspace_id_str)

    query = "Supabase là gì?"
    query_vector = await embed_query(query)
    print(f"✓ Query embedded: dim={len(query_vector)}")

    results = await similarity_search(workspace_id, query_vector, top_k=3, similarity_threshold=0.1)
    print(f"✓ Found {len(results)} chunks:")
    for r in results:
        print(f"  - similarity={r.similarity:.3f}: {r.content[:80]}...")


async def main():
    print("=" * 60)
    print("LOCAL NOTEBOOKLM — Supabase Pipeline Test")
    print("=" * 60)

    # Test 1: Workspace CRUD (không cần embedding API)
    try:
        await test_workspace_crud()
    except Exception as e:
        print(f"✗ Workspace CRUD failed: {e}")
        return

    # Để test ingest + search, cần workspace_id thực
    # Nhập workspace_id UUID từ Supabase dashboard hoặc tạo mới ở đây
    workspace_id = input("\nNhập workspace_id (UUID) để test ingest+search (hoặc Enter để bỏ qua): ").strip()

    if workspace_id:
        try:
            file_id = await test_file_ingest(workspace_id)
            await test_vector_search(workspace_id)
        except Exception as e:
            print(f"✗ Ingest/Search test failed: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print("Hoàn tất!")


if __name__ == "__main__":
    asyncio.run(main())

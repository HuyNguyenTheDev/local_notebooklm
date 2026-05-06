-- ============================================================
-- Local NotebookLM — Supabase Migration Script
-- Chạy file này trên Supabase SQL Editor
-- ============================================================

-- 1. Extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================
-- 2. Bảng workspaces
-- ============================================================
CREATE TABLE IF NOT EXISTS workspaces (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_workspaces_updated_at ON workspaces;
CREATE TRIGGER trg_workspaces_updated_at
    BEFORE UPDATE ON workspaces
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- 3. Bảng files
-- ============================================================
CREATE TABLE IF NOT EXISTS files (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    filename        TEXT NOT NULL,
    file_type       TEXT NOT NULL,               -- 'pdf' | 'txt' | 'md'
    storage_path    TEXT,                         -- (optional) Supabase Storage path
    raw_text        TEXT,                         -- full extracted text
    parse_status    TEXT NOT NULL DEFAULT 'pending'
                    CHECK (parse_status IN ('pending', 'processing', 'done', 'failed')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_files_workspace ON files(workspace_id);
CREATE INDEX IF NOT EXISTS idx_files_status ON files(parse_status);

-- ============================================================
-- 4. Bảng chunks (tim của RAG)
-- ============================================================
CREATE TABLE IF NOT EXISTS chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id         UUID NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    chunk_index     INTEGER NOT NULL,
    content         TEXT NOT NULL,
    token_count     INTEGER,
    embedding       VECTOR(1024),                -- BAAI/bge-m3 dimension
    embed_model     TEXT DEFAULT 'BAAI/bge-m3',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(file_id, chunk_index)
);

-- Vector index (cosine similarity) — tạo sau khi có đủ data
-- Với ít data (<1000 chunks), exact search nhanh hơn ivfflat
CREATE INDEX IF NOT EXISTS idx_chunks_workspace ON chunks(workspace_id);
CREATE INDEX IF NOT EXISTS idx_chunks_file ON chunks(file_id);

-- Tạo HNSW index (Supabase hỗ trợ từ pgvector 0.5+, tốt hơn ivfflat)
-- Uncomment khi đã có data:
-- CREATE INDEX idx_chunks_embedding ON chunks
--     USING hnsw (embedding vector_cosine_ops)
--     WITH (m = 16, ef_construction = 64);

-- ============================================================
-- 5. Hàm search_chunks (gọi từ Python qua supabase.rpc)
-- ============================================================
CREATE OR REPLACE FUNCTION search_chunks(
    query_embedding VECTOR(1024),
    target_workspace_id UUID,
    match_count INT DEFAULT 5,
    similarity_threshold FLOAT DEFAULT 0.3
)
RETURNS TABLE (
    chunk_id UUID,
    file_id UUID,
    content TEXT,
    similarity FLOAT
)
LANGUAGE sql STABLE
AS $$
    SELECT
        id          AS chunk_id,
        file_id,
        content,
        1 - (embedding <=> query_embedding) AS similarity
    FROM chunks
    WHERE workspace_id = target_workspace_id
      AND 1 - (embedding <=> query_embedding) > similarity_threshold
    ORDER BY embedding <=> query_embedding
    LIMIT match_count;
$$;

-- ============================================================
-- 6. Bảng chat_sessions & messages (optional — lưu lịch sử chat)
-- ============================================================
CREATE TABLE IF NOT EXISTS chat_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content         TEXT NOT NULL,
    source_chunks   UUID[],                       -- chunk IDs dùng làm context
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);

-- ============================================================
-- 7. Row Level Security (RLS) — bật nếu cần multi-tenant
-- Hiện tại disable để backend service role truy cập tự do
-- ============================================================
-- ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE files ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- DONE! Kiểm tra:
-- SELECT table_name FROM information_schema.tables
-- WHERE table_schema = 'public';
-- ============================================================

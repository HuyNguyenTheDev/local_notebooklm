-- ============================================================
-- Local NotebookLM - Supabase one-shot migration
-- Run this whole file once in Supabase SQL Editor.
--
-- Safe to re-run for normal updates:
-- - Tables/indexes use IF NOT EXISTS where possible.
-- - Functions use CREATE OR REPLACE.
-- - Existing user data is not deleted.
-- ============================================================

-- ------------------------------------------------------------
-- 1. Extensions
-- ------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ------------------------------------------------------------
-- 2. Workspaces
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS workspaces (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

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

-- ------------------------------------------------------------
-- 3. Files
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS files (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    filename        TEXT NOT NULL,
    file_type       TEXT NOT NULL, -- pdf | txt | md
    storage_path    TEXT,
    raw_text        TEXT,
    parse_status    TEXT NOT NULL DEFAULT 'pending'
                    CHECK (parse_status IN ('pending', 'processing', 'done', 'failed')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_files_workspace ON files(workspace_id);
CREATE INDEX IF NOT EXISTS idx_files_status ON files(parse_status);

-- ------------------------------------------------------------
-- 4. Chunks and vector search
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id         UUID NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    chunk_index     INTEGER NOT NULL,
    content         TEXT NOT NULL,
    token_count     INTEGER,
    embedding       VECTOR(1024), -- BAAI/bge-m3 dimension
    embed_model     TEXT DEFAULT 'BAAI/bge-m3',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(file_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_chunks_workspace ON chunks(workspace_id);
CREATE INDEX IF NOT EXISTS idx_chunks_file ON chunks(file_id);

-- HNSW index for approximate cosine similarity search.
-- The app queries with ORDER BY embedding <=> query_embedding LIMIT k.
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
    ON chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

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
        id AS chunk_id,
        file_id,
        content,
        1 - (embedding <=> query_embedding) AS similarity
    FROM chunks
    WHERE workspace_id = target_workspace_id
      AND embedding IS NOT NULL
      AND 1 - (embedding <=> query_embedding) > similarity_threshold
    ORDER BY embedding <=> query_embedding
    LIMIT match_count;
$$;

-- ------------------------------------------------------------
-- 5. BM25 lexical search over chunks
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS chunk_terms (
    chunk_id      UUID NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
    workspace_id  UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    term          TEXT NOT NULL,
    tf            INTEGER NOT NULL CHECK (tf > 0),
    PRIMARY KEY (chunk_id, term)
);

CREATE INDEX IF NOT EXISTS idx_chunk_terms_workspace_term
    ON chunk_terms(workspace_id, term);

CREATE INDEX IF NOT EXISTS idx_chunk_terms_chunk
    ON chunk_terms(chunk_id);

CREATE OR REPLACE FUNCTION rebuild_bm25_terms_for_chunk(target_chunk_id UUID)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    DELETE FROM chunk_terms WHERE chunk_id = target_chunk_id;

    INSERT INTO chunk_terms (chunk_id, workspace_id, term, tf)
    SELECT
        c.id,
        c.workspace_id,
        stat.word,
        stat.nentry
    FROM chunks c
    CROSS JOIN LATERAL ts_stat(
        format('SELECT to_tsvector(''english'', %L)', c.content)
    ) AS stat
    WHERE c.id = target_chunk_id
      AND stat.nentry > 0
    ON CONFLICT (chunk_id, term) DO UPDATE
        SET tf = EXCLUDED.tf,
            workspace_id = EXCLUDED.workspace_id;
END;
$$;

CREATE OR REPLACE FUNCTION rebuild_bm25_terms_for_file(target_file_id UUID)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    DELETE FROM chunk_terms
    WHERE chunk_id IN (
        SELECT id FROM chunks WHERE file_id = target_file_id
    );

    INSERT INTO chunk_terms (chunk_id, workspace_id, term, tf)
    SELECT
        c.id,
        c.workspace_id,
        stat.word,
        stat.nentry
    FROM chunks c
    CROSS JOIN LATERAL ts_stat(
        format('SELECT to_tsvector(''english'', %L)', c.content)
    ) AS stat
    WHERE c.file_id = target_file_id
      AND stat.nentry > 0
    ON CONFLICT (chunk_id, term) DO UPDATE
        SET tf = EXCLUDED.tf,
            workspace_id = EXCLUDED.workspace_id;
END;
$$;

CREATE MATERIALIZED VIEW IF NOT EXISTS bm25_stats AS
WITH chunk_lengths AS (
    SELECT
        workspace_id,
        chunk_id,
        sum(tf)::FLOAT AS doc_len
    FROM chunk_terms
    GROUP BY workspace_id, chunk_id
),
workspace_totals AS (
    SELECT
        workspace_id,
        count(*)::INTEGER AS total_docs,
        avg(doc_len)::FLOAT AS avgdl
    FROM chunk_lengths
    GROUP BY workspace_id
)
SELECT
    ct.workspace_id,
    ct.term,
    count(DISTINCT ct.chunk_id)::INTEGER AS doc_freq,
    sum(ct.tf)::INTEGER AS total_tf,
    wt.total_docs,
    wt.avgdl
FROM chunk_terms ct
JOIN workspace_totals wt ON wt.workspace_id = ct.workspace_id
GROUP BY ct.workspace_id, ct.term, wt.total_docs, wt.avgdl;

CREATE UNIQUE INDEX IF NOT EXISTS idx_bm25_stats_workspace_term
    ON bm25_stats(workspace_id, term);

CREATE OR REPLACE FUNCTION bm25_score(
    p_chunk_id UUID,
    p_query TEXT,
    k1 FLOAT DEFAULT 1.2,
    b FLOAT DEFAULT 0.75
) RETURNS FLOAT AS $$
DECLARE
    score FLOAT := 0;
    rec RECORD;
    doc_len FLOAT;
BEGIN
    SELECT sum(tf)::FLOAT INTO doc_len
    FROM chunk_terms
    WHERE chunk_id = p_chunk_id;

    IF doc_len IS NULL OR doc_len = 0 THEN
        RETURN 0;
    END IF;

    FOR rec IN
        WITH query_terms AS (
            SELECT DISTINCT word AS term
            FROM ts_stat(format('SELECT to_tsvector(''english'', %L)', p_query))
        )
        SELECT
            s.term,
            s.doc_freq::FLOAT AS doc_freq,
            s.total_docs::FLOAT AS total_docs,
            s.avgdl::FLOAT AS avgdl,
            COALESCE(ct.tf, 0)::FLOAT AS tf
        FROM chunks c
        JOIN bm25_stats s ON s.workspace_id = c.workspace_id
        JOIN query_terms q ON q.term = s.term
        LEFT JOIN chunk_terms ct
            ON ct.chunk_id = c.id
           AND ct.term = s.term
        WHERE c.id = p_chunk_id
    LOOP
        IF rec.tf > 0 AND rec.avgdl > 0 THEN
            score := score
                + ln((rec.total_docs - rec.doc_freq + 0.5) / (rec.doc_freq + 0.5) + 1)
                * (rec.tf * (k1 + 1))
                / (rec.tf + k1 * (1 - b + b * doc_len / rec.avgdl));
        END IF;
    END LOOP;

    RETURN score;
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION search_chunks_bm25(
    p_query TEXT,
    target_workspace_id UUID,
    match_count INT DEFAULT 5,
    min_score FLOAT DEFAULT 0
)
RETURNS TABLE (
    chunk_id UUID,
    file_id UUID,
    content TEXT,
    score FLOAT
)
LANGUAGE sql STABLE
AS $$
    WITH query_terms AS (
        SELECT DISTINCT word AS term
        FROM ts_stat(format('SELECT to_tsvector(''english'', %L)', p_query))
    ),
    candidates AS (
        SELECT DISTINCT ct.chunk_id
        FROM chunk_terms ct
        JOIN query_terms q ON q.term = ct.term
        WHERE ct.workspace_id = target_workspace_id
    ),
    scored AS (
        SELECT
            c.id AS chunk_id,
            c.file_id,
            c.content,
            bm25_score(c.id, p_query) AS score
        FROM candidates candidate
        JOIN chunks c ON c.id = candidate.chunk_id
        WHERE c.workspace_id = target_workspace_id
    )
    SELECT scored.chunk_id, scored.file_id, scored.content, scored.score
    FROM scored
    WHERE scored.score > min_score
    ORDER BY scored.score DESC
    LIMIT match_count;
$$;

-- ------------------------------------------------------------
-- 6. Chat sessions and messages
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS chat_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    title           TEXT NOT NULL DEFAULT 'New chat',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE chat_sessions
ADD COLUMN IF NOT EXISTS title TEXT NOT NULL DEFAULT 'New chat';

CREATE TABLE IF NOT EXISTS messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content         TEXT NOT NULL,
    source_chunks   UUID[],
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_workspace ON chat_sessions(workspace_id);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);


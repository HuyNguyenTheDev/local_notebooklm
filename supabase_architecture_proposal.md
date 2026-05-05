# Đề xuất kiến trúc: Supabase PostgreSQL + pgvector cho Local NotebookLM

## 1. Hiện trạng codebase

### Những gì đang có
| Thành phần | Hiện tại |
|---|---|
| **Lưu trữ workspace** | `data/workspaces.json` (flat JSON) |
| **Lưu trữ documents** | `data/metadata.json` (flat JSON, chứa cả full text) |
| **File gốc** | `data/uploads/` (local disk) |
| **RAG** | **Không có** — chat gửi toàn bộ text tất cả file lên LLM |
| **Chunking** | **Không có** |
| **Vector search** | **Không có** |
| **Embedding** | **Không có** |
| **PDF parsing** | `pypdf` local (chỉ đọc text layer, không OCR) |

### Vấn đề cốt lõi
`chat.py` hiện tại **ghép toàn bộ text** của mọi tài liệu trong workspace thành 1 `context` rồi nhét thẳng vào prompt LLM. Cách này:
- Không scale được khi có nhiều file
- Tốn token LLM vô ích
- Không có độ chính xác ngữ nghĩa

---

## 2. Mục tiêu sau khi tích hợp Supabase

```
Upload file → Parse text (API) → Chunk → Embed (API) → Lưu pgvector
                                                              ↓
User hỏi → Embed câu hỏi (API) → Vector similarity search → Lấy top-K chunks
                                                              ↓
                                              Ghép context → Gọi LLM (API) → Trả lời
```

---

## 3. Thiết kế Database Schema (PostgreSQL + pgvector)

### 3.1 Extension cần bật trên Supabase

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- Cho BM25/full-text search (optional hybrid)
```

### 3.2 Bảng `workspaces`

```sql
CREATE TABLE workspaces (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL UNIQUE,          -- tên workspace hiển thị
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

> **Lưu ý:** Hiện tại `workspace_id` là string tùy ý (user nhập). Khi migrate sang Supabase nên dùng UUID để tránh collision, nhưng vẫn giữ cột `name` cho backward compat với frontend.

### 3.3 Bảng `files`

```sql
CREATE TABLE files (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    filename        TEXT NOT NULL,              -- tên file gốc
    file_type       TEXT NOT NULL,              -- 'pdf', 'txt', 'md'
    storage_path    TEXT,                       -- path trong Supabase Storage (nếu dùng)
    raw_text        TEXT,                       -- toàn bộ text đã extract (có thể NULL nếu lưu riêng)
    parse_status    TEXT NOT NULL DEFAULT 'pending',  -- 'pending' | 'done' | 'failed'
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_files_workspace ON files(workspace_id);
```

> **Nên lưu `raw_text` không?** Có — để debug, re-chunk sau này mà không cần parse lại. Với file lớn có thể tách ra bảng riêng hoặc dùng Supabase Storage.

### 3.4 Bảng `chunks` (tim của RAG)

```sql
CREATE TABLE chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id         UUID NOT NULL REFERENCES files(id) ON DELETE CASCADE,
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    chunk_index     INTEGER NOT NULL,           -- vị trí chunk trong file (0-based)
    content         TEXT NOT NULL,             -- nội dung text chunk
    token_count     INTEGER,                   -- số token ước tính
    embedding       VECTOR(1024),              -- vector embedding (chiều tuỳ model)
    embed_model     TEXT,                      -- ghi lại model embed dùng, bge-m3
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(file_id, chunk_index)
);

-- Index vector cho cosine similarity search
CREATE INDEX idx_chunks_embedding ON chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Index cho filter theo workspace (quan trọng!)
CREATE INDEX idx_chunks_workspace ON chunks(workspace_id);
CREATE INDEX idx_chunks_file ON chunks(file_id);
```

> **Chiều vector `1024`**: phù hợp với model BAAI bge-m3.

### 3.5 (Optional) Bảng `chat_sessions` & `messages`

```sql
CREATE TABLE chat_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content         TEXT NOT NULL,
    source_chunks   UUID[],                    -- array chunk IDs được dùng làm context
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## 4. Luồng xử lý chi tiết

### 4.1 Upload & Ingest Pipeline

```
[Frontend] POST /upload (file + workspace_id)
    │
    ▼
[Backend - upload.py]
    ├─ Validate file type
    ├─ Upload raw file lên Supabase Storage (bucket "uploads")
    ├─ INSERT INTO files (status='pending')
    └─ Kick off background task: ingest_file(file_id)
         │
         ▼
    [Background Task - ingest_service.py]
         ├─ 1. PARSE: Gọi PDF-to-text API → raw_text
         │        └─ UPDATE files SET raw_text=..., parse_status='done'
         │
         ├─ 2. CHUNK: Chia raw_text thành chunks
         │        └─ Chiến lược: sliding window (chunk_size=512 tokens, overlap=64)
         │
         ├─ 3. EMBED: Gọi Embedding API (batch) → list of vectors
         │
         └─ 4. STORE: INSERT INTO chunks (content, embedding, ...)
```

> **Tại sao Background Task?** PDF lớn có thể mất vài giây - vài phút để parse + embed. Không nên block HTTP request. FastAPI có `BackgroundTasks` built-in, hoặc dùng Celery/ARQ cho production.

### 4.2 RAG Query Pipeline

```
[Frontend] POST /chat {question, workspace_id}
    │
    ▼
[Backend - chat.py]
    ├─ 1. Embed câu hỏi: Gọi Embedding API → query_vector (1536 dims)
    │
    ├─ 2. Vector Search: pgvector cosine similarity trong workspace
    │       SELECT content FROM chunks
    │       WHERE workspace_id = $1
    │       ORDER BY embedding <=> $2   -- cosine distance
    │       LIMIT 5;
    │
    ├─ 3. (Optional) Rerank: BM25 hoặc cross-encoder rerank
    │
    ├─ 4. Build context: Ghép top-K chunks
    │
    └─ 5. Gọi LLM API với {question, context} → answer
```

---

## 5. Chiến lược Chunking

Đây là quyết định quan trọng ảnh hưởng trực tiếp đến chất lượng RAG:

| Chiến lược | Mô tả | Phù hợp |
|---|---|---|
| **Fixed-size** | Chia cố định N ký tự / N token, có overlap | Đơn giản, hiệu quả cho text thuần |
| **Sentence-based** | Chia theo câu (dùng NLTK/spaCy) | Text có cấu trúc câu rõ ràng |
| **Paragraph-based** | Chia theo `\n\n` | Tài liệu có đoạn văn tốt |
| **Recursive** | Thử chia theo đoạn, rồi câu, rồi từ | LangChain `RecursiveTextSplitter` - khuyến nghị |

### Khuyến nghị cho dự án này:
```
chunk_size   = 512 tokens (~400 từ tiếng Việt)
chunk_overlap = 64 tokens (~50 từ)
Dùng: langchain_text_splitters.RecursiveCharacterTextSplitter
```

---

## 6. Cấu trúc thư mục backend mới

```
backend/
├── main.py
├── database.py          # ← MỚI: Supabase client + connection pool
├── models/
│   ├── document.py      # Pydantic models (cập nhật)
│   └── chunk.py         # ← MỚI: Chunk models
├── routers/
│   ├── upload.py        # Cập nhật: trigger background ingest
│   ├── knowledge.py     # Cập nhật: query từ DB thay vì JSON
│   └── chat.py          # Cập nhật: RAG search thay vì ghép toàn bộ text
└── services/
    ├── file_parser.py   # Cập nhật: gọi PDF API thay vì pypdf local
    ├── chunker.py       # ← MỚI: text splitting logic
    ├── embedding.py     # ← MỚI: gọi Embedding API
    ├── vector_store.py  # ← MỚI: pgvector CRUD + similarity search
    ├── ingest.py        # ← MỚI: orchestrate parse→chunk→embed→store
    ├── storage.py       # ← MỚI: Supabase Storage upload/download
    └── llm_client.py    # Cập nhật: giữ nguyên interface
```

---

## 7. Dependencies mới cần thêm

```txt
# requirements.txt (bổ sung)
supabase==2.x.x                  # Supabase Python client
asyncpg==0.30.x                  # Async PostgreSQL driver (cho pgvector)
psycopg[binary,pool]==3.x.x      # Hoặc psycopg3 thay thế asyncpg
pgvector==0.3.x                  # pgvector Python adapter

langchain-text-splitters==0.x.x  # Chunking (chỉ phần text splitter, không cần LangChain full)
tiktoken==0.x.x                  # Đếm token (OpenAI tokenizer, dùng cho chunk_size)
```

---

## 8. Biến môi trường `.env` mới

```env
# Supabase
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...  # Dùng backend-side, KHÔNG expose ra frontend

# Database trực tiếp (cho pgvector queries)
DATABASE_URL=postgresql://postgres:[password]@db.xxxx.supabase.co:5432/postgres

# APIs
LLM_API_URL=https://xxxx.ngrok-free.app/chat
EMBEDDING_API_URL=https://xxxx.ngrok-free.app/embed   # ← MỚI
PDF_PARSE_API_URL=https://xxxx.ngrok-free.app/parse   # ← MỚI (nếu dùng API)

# Chunking config
CHUNK_SIZE=512
CHUNK_OVERLAP=64
```

---

## 9. SQL Functions hữu ích trong Supabase

### 9.1 Similarity search function (gọi từ Python)

```sql
CREATE OR REPLACE FUNCTION search_chunks(
    query_embedding VECTOR(1536),
    target_workspace_id UUID,
    match_count INT DEFAULT 5,
    similarity_threshold FLOAT DEFAULT 0.7
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
        id        AS chunk_id,
        file_id,
        content,
        1 - (embedding <=> query_embedding) AS similarity
    FROM chunks
    WHERE workspace_id = target_workspace_id
      AND 1 - (embedding <=> query_embedding) > similarity_threshold
    ORDER BY embedding <=> query_embedding
    LIMIT match_count;
$$;
```

Gọi từ Python:
```python
result = supabase.rpc("search_chunks", {
    "query_embedding": query_vector,
    "target_workspace_id": workspace_id,
    "match_count": 5
}).execute()
```

### 9.2 File ingest status check

```sql
-- Xem tiến độ ingest của file
SELECT 
    f.filename,
    f.parse_status,
    COUNT(c.id) AS chunk_count,
    COUNT(c.embedding) AS embedded_count
FROM files f
LEFT JOIN chunks c ON c.file_id = f.id
WHERE f.workspace_id = 'xxx'
GROUP BY f.id, f.filename, f.parse_status;
```

---

## 10. Phân tích API calls trong pipeline

| Bước | API Call | Khi nào gọi | Chi phí |
|---|---|---|---|
| **Parse PDF** | PDF-to-text API | Lúc upload, 1 lần / file | Thấp |
| **Embed chunks** | Embedding API | Lúc ingest, 1 lần / chunk | Trung bình |
| **Embed query** | Embedding API | Mỗi lần chat | Rất thấp (1 call) |
| **LLM answer** | LLM API | Mỗi lần chat | Cao |

> **Quan trọng:** Embedding được tính 1 lần lúc ingest và **cache vào pgvector mãi mãi**. Không cần re-embed mỗi khi query.

---

## 11. Lộ trình thực hiện (Phases)

### Phase 1 — Database Setup (1-2 ngày)
- [ ] Tạo project Supabase, enable pgvector extension
- [ ] Chạy migration scripts tạo các bảng
- [ ] Tạo `database.py` với Supabase client
- [ ] Test CRUD cơ bản

### Phase 2 — Migrate Storage (1 ngày)
- [ ] Viết `vector_store.py` cho workspace/file CRUD
- [ ] Refactor `knowledge_store.py` → gọi Supabase thay vì JSON
- [ ] Migrate data cũ từ JSON vào DB (migration script)

### Phase 3 — Ingest Pipeline (2-3 ngày)
- [ ] Viết `chunker.py` với RecursiveTextSplitter
- [ ] Viết `embedding.py` để gọi Embedding API
- [ ] Viết `ingest.py` orchestrator
- [ ] Cập nhật `upload.py` để trigger background ingest
- [ ] Cập nhật `file_parser.py` để gọi PDF API thay vì pypdf local

### Phase 4 — RAG Chat (1-2 ngày)
- [ ] Tạo SQL function `search_chunks` trên Supabase
- [ ] Refactor `chat.py`: embed query → vector search → LLM
- [ ] Test end-to-end RAG flow

### Phase 5 — Polish (tuỳ chọn)
- [ ] Thêm file ingest status polling (frontend polling `/files/{id}/status`)
- [ ] Hybrid search: Vector + BM25 kết hợp
- [ ] Reranking
- [ ] Chat history lưu vào DB

---

## 12. Quyết định cần bạn xác nhận

> [!IMPORTANT]
> Trước khi code, cần thống nhất các điểm sau:

1. **Embedding model nào?** → Quyết định chiều vector (`VECTOR(1536)` cho OpenAI, `VECTOR(768)` cho Gemini `text-embedding-004`, etc.)
2. **PDF API là service nào?** → Chỉ cần biết format request/response để viết `file_parser.py` mới
3. **Embedding API là service nào?** → Tương tự, để viết `embedding.py`
4. **Supabase Storage hay local disk?** → Có cần lưu file gốc lên Supabase Storage không, hay chỉ lưu text đã parse?
5. **Có cần migrate data cũ không?** → Hay reset sạch và bắt đầu lại?
6. **Chunk size?** → 512 tokens như đề xuất, hay khác?

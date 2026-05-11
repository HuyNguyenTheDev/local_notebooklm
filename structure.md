# Local NotebookLM - Codebase Structure and Flow

Tài liệu này mô tả cấu trúc, kỹ thuật chính, endpoint và luồng hoạt động của codebase hiện tại. Ứng dụng là một hệ thống RAG: upload tài liệu vào workspace, parse/chunk/embed tài liệu, lưu vào Supabase pgvector, rồi chat bằng LLM dựa trên các chunks liên quan.

## 1. Tổng Quan Kiến Trúc

```text
Frontend Next.js
  -> gọi REST API qua frontend/lib/api.ts

Backend FastAPI
  -> upload, workspace/file CRUD, chat, embedding endpoint
  -> parse file, chunk text, gọi embedding API, gọi LLM API

Supabase/Postgres + pgvector
  -> lưu workspaces, files, chunks, chat_sessions, messages
  -> similarity search bằng pgvector

External services
  -> Embedding API: OpenRouter hoặc custom embedding endpoint
  -> LLM API: Cloudflare Worker/OpenRouter/custom worker
  -> Optional PDF OCR API
```

Luồng quan trọng nhất:

```text
Upload file
  -> lưu file tạm vào backend/data/uploads
  -> tạo record files status=pending
  -> background ingest
  -> parse raw text
  -> lưu raw_text vào files
  -> normalize text for chunking
  -> split chunks
  -> embed chunks
  -> lưu chunks + embeddings vào Supabase
  -> xóa file tạm

Chat
  -> embed câu hỏi
  -> similarity search chunks trong workspace
  -> build context từ top chunks
  -> gọi LLM API
  -> lưu user/assistant messages
  -> trả answer + sources
```

## 2. Cấu Trúc Thư Mục Chính

```text
backend/
  main.py                 FastAPI app entrypoint, CORS, lifespan, include routers
  config.py               Load .env và expose config
  database.py             Supabase clients + asyncpg pool cho pgvector
  models/
    document.py           Pydantic schemas workspace/file/chat
    chunk.py              Pydantic schemas chunks/search result
  routers/
    upload.py             POST /upload
    knowledge.py          /documents workspace/file CRUD
    chat.py               /chat endpoints + RAG chat flow
    embeddings.py         Manual embedding endpoint
  services/
    file_parser.py        Parse PDF/TXT/MD
    chunker.py            Normalize + split text thành chunks
    embedding.py          Gọi embedding API
    vector_store.py       CRUD Supabase + pgvector search
    llm_client.py         Build prompt + gọi LLM worker
    ingest.py             Background parse -> chunk -> embed -> store
    knowledge_store.py    Legacy local JSON/file store, hầu như không dùng trong flow Supabase hiện tại
  data/
    uploads/              Nơi lưu file upload tạm thời
    backup_*/             Backup local metadata cũ

frontend/
  app/
    layout.tsx            App shell: Sidebar + TopBar + content
    page.tsx              Home/workspace list/create/delete
    workspace/[workspaceId]/page.tsx
                           Main workspace page: chat, sessions, sources, upload modal
  components/
    ChatBox.tsx           Chat UI, gửi question, load history
    ChatSessionsSidebar.tsx
                           List/create/select/rename/delete chat sessions
    FileUpload.tsx        Upload modal/drag-drop
    KnowledgeList.tsx     Sidebar source list, view raw content/chunks, rename/delete
    MessageBubble.tsx     Render user/assistant message
    Sidebar.tsx, TopBar.tsx, WorkspaceTabs.tsx
  lib/
    api.ts                Typed client wrapper gọi backend endpoints
    ui.tsx                UI text/i18n/provider

supabase_migration.sql    Schema Supabase + search_chunks RPC
test_*.py                 Scripts test upload, chunking, Supabase, LLM
```

## 3. Backend Entry Point

File: `backend/main.py`

- Tạo FastAPI app với title/version.
- Bật CORS cho:
  - `http://localhost:3000`
  - `http://127.0.0.1:3000`
- Lifespan startup thử warm up asyncpg DB pool bằng `get_db_pool()`.
- Shutdown đóng pool bằng `close_db_pool()`.
- Include routers:
  - `/upload`
  - `/documents`
  - `/chat`
  - `/embeddings`
- Healthcheck:
  - `GET /` -> `{"status": "ok", "version": "2.0.0"}`

## 4. Config Và Environment

File: `backend/config.py`

Thứ tự load env:

```text
backend/.env
root .env
system environment variables
```

Các config chính:

```text
SUPABASE_URL
SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY
DATABASE_URL

LLM_API_URL
LLM_API_KEY

EMBEDDING_API_URL
OPENROUTER_API_KEY
OPENROUTER_SITE_URL
OPENROUTER_SITE_NAME
EMBED_MODEL
EMBEDDING_DIM

PDF_PARSE_API_URL

CHUNK_SIZE
CHUNK_OVERLAP
```

Ghi chú:

- `DATABASE_URL` tự replace `postgresql+asyncpg://` hoặc `postgres+asyncpg://` thành `postgresql://`.
- Default chunking nếu `.env` không set:
  - `CHUNK_SIZE=512`
  - `CHUNK_OVERLAP=64`
- Default embedding:
  - `EMBED_MODEL=BAAI/bge-m3`
  - `EMBEDDING_DIM=1024`

## 5. Database Và Supabase

File: `backend/database.py`

Có 3 kiểu kết nối:

- `get_supabase_client()`: Supabase sync client, dùng nhiều cho CRUD qua REST.
- `get_supabase()`: Supabase async client, hiện ít dùng.
- `get_db_pool()`: asyncpg pool, dùng cho pgvector raw SQL similarity search.

Vector codec:

- `_register_vector_codec()` đăng ký type `vector` cho asyncpg dạng text codec.
- Không tạo extension trong Python; extension được tạo bằng SQL migration.

Schema chính nằm ở `supabase_migration.sql`:

```text
workspaces
  id UUID PK
  name TEXT UNIQUE
  created_at, updated_at

files
  id UUID PK
  workspace_id UUID FK -> workspaces
  filename
  file_type: pdf/txt/md
  storage_path optional
  raw_text
  parse_status: pending/processing/done/failed
  created_at

chunks
  id UUID PK
  file_id UUID FK -> files
  workspace_id UUID FK -> workspaces
  chunk_index
  content
  token_count
  embedding VECTOR(1024)
  embed_model
  created_at
  UNIQUE(file_id, chunk_index)

chat_sessions
  id UUID PK
  workspace_id UUID FK -> workspaces
  title
  created_at

messages
  id UUID PK
  session_id UUID FK -> chat_sessions
  role: user/assistant
  content
  source_chunks UUID[]
  created_at
```

Search function:

```sql
search_chunks(query_embedding, target_workspace_id, match_count, similarity_threshold)
```

Trả về:

```text
chunk_id, file_id, content, similarity
```

Similarity dùng cosine distance:

```sql
1 - (embedding <=> query_embedding)
```

## 6. Backend Models

File: `backend/models/document.py`

- `WorkspaceCreate`: body tạo workspace.
- `WorkspacePreview`: response workspace.
- `DocumentPreview`: metadata file/document.
- `ChatRequest`: question, workspace_id, optional session_id.
- `ChatResponse`: answer, session_id, sources.
- `ChatSessionCreate`, `ChatSessionUpdate`, `ChatSessionPreview`.
- `ChatMessageRecord`: chat message đã lưu.

File: `backend/models/chunk.py`

- `ChunkRecord`: chunk trả ra frontend, không expose embedding.
- `ChunkSearchResult`: kết quả similarity search nội bộ.

## 7. Upload Và Ingest Flow

### Endpoint: `POST /upload`

File: `backend/routers/upload.py`

Input:

- `multipart/form-data`
- `files`: một hoặc nhiều file
- `workspace_id`: UUID hoặc workspace name

Supported extensions:

```text
.pdf, .txt, .md
```

Flow:

1. Resolve workspace bằng `resolve_workspace_id(workspace_id, create_if_missing=True)`.
2. Validate extension.
3. Read file bytes.
4. Lưu file tạm:

```text
backend/data/uploads/{generated_uuid}.{ext}
```

5. Insert record vào bảng `files` với `parse_status="pending"`.
6. Add background task:

```python
background_tasks.add_task(ingest_file, file_uuid, resolved_workspace_id, stored_path)
```

7. Trả `DocumentPreview` ngay, không chờ ingest xong.

### Background ingest

File: `backend/services/ingest.py`

Flow:

1. Set file status `processing`.
2. Parse file bằng `parse_file_async()`.
3. Nếu PDF parse rỗng -> status `failed`.
4. Lưu `raw_text` vào bảng `files`.
5. Chunk text bằng `split_text(raw_text)`.
6. Embed chunks bằng `embed_texts(chunks)`.
7. Xóa chunks cũ theo file bằng `delete_chunks_by_file(file_id)`.
8. Insert/upsert chunks mới vào bảng `chunks`.
9. Mark file `done`.
10. Cuối cùng xóa file tạm khỏi `backend/data/uploads`.

Quan trọng:

- File gốc không được giữ lâu dài ở disk.
- Dữ liệu lâu dài nằm trong Supabase: `files.raw_text`, `chunks.content`, `chunks.embedding`.

## 8. Parse File

File: `backend/services/file_parser.py`

Strategy:

- PDF:
  1. Ưu tiên pypdf local:
     ```python
     PdfReader(...).pages[i].extract_text()
     ```
  2. Nếu pypdf fail hoặc empty và có `PDF_PARSE_API_URL`, gọi OCR API.
  3. Nếu vẫn fail -> trả empty string.

- TXT/MD:
  - đọc UTF-8 với `errors="replace"`.
  - remove null character `\x00` để tránh lỗi PostgreSQL.

## 9. Chunking Strategy

File: `backend/services/chunker.py`

Hiện tại chunking là:

```text
normalize PDF-like raw text
  -> RecursiveCharacterTextSplitter
  -> filter empty chunks
```

### Normalize trước chunking

`normalize_text_for_chunking(raw_text)` chỉ dùng cho chunks/embeddings, không sửa raw_text gốc đã lưu.

Mục tiêu:

- Gộp các dòng prose bị pypdf xuống dòng theo layout PDF.
- Giữ riêng heading, title, author/email/url, list, caption, table/figure markers.
- Xử lý hyphenated words:

```text
transduc-
tion
```

thành:

```text
transduction
```

Các regex/heuristic chính:

- `_SECTION_HEADING_RE`: abstract, references, appendix, heading dạng `1 Introduction`, `3.2 Attention`.
- `_TITLE_HEADING_RE`: title ngắn dạng chữ hoa đầu dòng.
- `_LIST_OR_CAPTION_RE`: bullet, list marker, `[1]`, `Figure 1`, `Table 2`, `Algorithm`.
- `_EMAIL_OR_URL_RE`: email/url.
- `_SENTENCE_END_RE`: nhận diện dấu kết thúc câu.

### Splitter

Dùng `RecursiveCharacterTextSplitter`:

```python
RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", "。", ".", " ", ""],
)
```

Thứ tự ưu tiên tách:

1. đoạn `\n\n`
2. dòng `\n`
3. dấu `。`
4. dấu `.`
5. khoảng trắng
6. ký tự thô

Đây là character-based recursive chunking, không phải semantic chunking theo AST/section tree.

## 10. Embedding

File: `backend/services/embedding.py`

Hàm chính:

- `embed_texts(texts)`: embed list texts theo batch.
- `embed_query(text)`: embed một query.

Batch size:

```python
_BATCH_SIZE = 16
```

Nếu `EMBEDDING_API_URL` chứa:

```text
openrouter.ai/api/v1/embeddings
```

thì dùng OpenRouter-compatible payload:

```json
{
  "model": "BAAI/bge-m3",
  "input": ["..."],
  "encoding_format": "float",
  "dimensions": 1024
}
```

Headers:

```text
Authorization: Bearer OPENROUTER_API_KEY
HTTP-Referer: OPENROUTER_SITE_URL optional
X-OpenRouter-Title: OPENROUTER_SITE_NAME optional
```

Nếu không phải OpenRouter thì dùng custom payload:

```json
{"texts": ["chunk 1", "chunk 2"]}
```

Supported response formats:

```json
{"embeddings": [[...]]}
```

hoặc OpenAI-compatible:

```json
{"data": [{"embedding": [...]}]}
```

Token count:

- Nếu API trả `usage.total_tokens` hoặc `usage.prompt_tokens`, code chia tương đối theo độ dài ký tự từng chunk.
- Nếu không có usage thì token_count = 0.

## 11. Vector Store Và Similarity Search

File: `backend/services/vector_store.py`

Nhóm chức năng:

- Workspace CRUD:
  - create/list/search/delete/resolve by UUID or name.
- File CRUD:
  - create record, update raw_text/status, list, get, delete, rename.
- Chat sessions/messages:
  - create/list/get/delete/rename sessions.
  - insert/list messages.
- Chunks:
  - insert/upsert chunks.
  - delete chunks by file.
  - list chunks by file.
  - similarity search.

### Insert chunks

`insert_chunks()` tạo records gồm:

```text
id
file_id
workspace_id
chunk_index
content
token_count
embedding as "[...]" string
embed_model
```

Upsert theo batch 100, conflict key:

```text
file_id, chunk_index
```

### Similarity search

`similarity_search()`:

- Nhận workspace_id, query_embedding, top_k, threshold.
- Trước tiên dùng asyncpg raw SQL:

```sql
SELECT
  id AS chunk_id,
  file_id,
  content,
  1 - (embedding <=> $1::vector) AS similarity
FROM chunks
WHERE workspace_id = $2
  AND 1 - (embedding <=> $1::vector) > $3
ORDER BY embedding <=> $1::vector
LIMIT $4
```

- Nếu direct pgvector fail, fallback sang Supabase RPC `search_chunks`.

Trong chat route, config search hiện tại:

```python
_TOP_K = 5
_SIMILARITY_THRESHOLD = 0.3
```

## 12. Chat/RAG Flow

File: `backend/routers/chat.py`

### Chat session endpoints

```text
GET    /chat/sessions?workspace_id=...
POST   /chat/sessions
GET    /chat/sessions/{session_id}/messages
DELETE /chat/sessions/{session_id}?workspace_id=...
PATCH  /chat/sessions/{session_id}
```

Ý nghĩa:

- Mỗi workspace có nhiều chat session.
- Mỗi session có nhiều messages.
- Khi rename/delete session, backend kiểm tra workspace_id để tránh thao tác nhầm workspace.

### Main endpoint: `POST /chat`

Body:

```json
{
  "question": "...",
  "workspace_id": "...",
  "session_id": "optional UUID"
}
```

Flow:

1. Validate question không rỗng.
2. Resolve workspace.
3. Resolve hoặc create chat session.
   - Nếu `session_id` null -> tạo session mới.
   - Nếu có `session_id` -> kiểm tra session thuộc workspace đó.
4. Load history messages.
5. Nếu session title là `New chat` và chưa có history, rename session theo câu hỏi đầu tiên.
6. Embed question bằng `embed_query(question)`.
7. Similarity search top chunks trong workspace.
8. Build context từ chunks.
9. Insert user message.
10. Gọi LLM bằng `ask_llm(question, context, history)`.
11. Insert assistant message với `source_chunks`.
12. Return:

```json
{
  "answer": "...",
  "session_id": "...",
  "sources": ["..."]
}
```

### Context trimming

Trong `chat.py`:

```python
_MAX_CONTEXT_CHARS = 12000
_MAX_CHUNK_CHARS = 2500
_MAX_SOURCE_CHARS = 1200
```

Ý nghĩa:

- Context gửi sang LLM bị giới hạn tổng 12k ký tự.
- Mỗi chunk context tối đa 2.5k ký tự.
- Sources trả về frontend tối đa 1.2k ký tự/source.
- Answer của LLM không bị cắt ở frontend/backend.

## 13. LLM Client

File: `backend/services/llm_client.py`

Chức năng:

- Build RAG prompt từ:
  - context
  - history
  - current question
- Gọi `LLM_API_URL`.
- Parse response.

Prompt hiện tại:

```text
[Context]
...
[History]
...
[Current Question]
...
```

Payload gửi Worker:

```json
{
  "prompt": "...",
  "systemPrompt": "..."
}
```

Headers:

```text
Content-Type: application/json
Authorization: Bearer LLM_API_KEY optional
```

Timeout:

```python
httpx.AsyncClient(timeout=90)
```

Response parser chấp nhận các key:

```text
response
answer
result
content
```

Nếu response không phải JSON thì trả `response.text`.

Trong file còn có code DPO/ngrok cũ đã comment out.

## 14. Knowledge/Documents Endpoints

File: `backend/routers/knowledge.py`

### Workspace endpoints

```text
GET /documents/workspaces
```

List toàn bộ workspaces, mới nhất trước.

```text
POST /documents/workspaces
```

Body:

```json
{"name": "..."}
```

Tạo workspace. Nếu name rỗng -> 400.

```text
GET /documents/workspaces/search?q=...
```

Search workspace bằng Supabase `ilike`.

```text
DELETE /documents/workspace/{workspace_id}
```

Resolve UUID/name, xóa workspace. Nhờ cascade, files/chunks/chat sessions/messages liên quan cũng bị xóa.

### File/document endpoints

```text
GET /documents?workspace_id=...
```

List files trong workspace.

```text
GET /documents/{file_id}/status
```

Trả parse_status để polling ingest.

```text
GET /documents/{file_id}
```

Trả raw_text đã parse.

```text
GET /documents/{file_id}/chunks
```

Trả chunks đã tạo, không trả embedding.

```text
DELETE /documents/{file_id}?workspace_id=...
```

Xóa file trong workspace. Chunks tự xóa theo cascade.

```text
PATCH /documents/{file_id}?workspace_id=...&new_filename=...
```

Rename file.

## 15. Manual Embeddings Endpoint

File: `backend/routers/embeddings.py`

Endpoint:

```text
POST /embeddings
```

Body:

```json
{
  "workspace_id": "...",
  "file_id": "...",
  "texts": ["..."],
  "embed_model": "optional"
}
```

Giới hạn:

```python
_MAX_BATCH = 16
```

Flow:

1. Resolve workspace.
2. Strip empty texts.
3. Embed texts.
4. Insert chunks vào DB.
5. Return preview gồm chunk_index, token_count, content_preview, embedding_dim.

Endpoint này hữu ích để test/manual insert chunks, nhưng flow upload chính dùng `ingest.py`.

## 16. Frontend Architecture

Frontend là Next.js App Router.

### API wrapper

File: `frontend/lib/api.ts`

Đây là layer duy nhất frontend dùng để gọi backend. Base URL:

```ts
const API_BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://127.0.0.1:8000";
```

Các function chính:

- `uploadFile(files, workspaceId)`
- `getDocuments(workspaceId)`
- `getDocumentContent(fileId)`
- `getDocumentChunks(fileId)`
- `createWorkspace(name)`
- `searchWorkspaces(query)`
- `getWorkspaces()`
- `deleteDocument(id, workspaceId)`
- `deleteWorkspace(workspaceId)`
- `renameDocument(id, newFilename, workspaceId)`
- `getChatSessions(workspaceId)`
- `createChatSession(workspaceId, title)`
- `renameChatSession(sessionId, workspaceId, title)`
- `getChatMessages(sessionId)`
- `deleteChatSession(sessionId, workspaceId)`
- `sendChat(question, workspaceId, sessionId)`

### App layout

File: `frontend/app/layout.tsx`

Shell:

```text
Sidebar
TopBar
main content
UiProvider
```

UI text/i18n nằm ở `frontend/lib/ui.tsx`.

### Home page

File: `frontend/app/page.tsx`

Chức năng:

- Load workspace từ localStorage trước để UI có data offline.
- Gọi `getWorkspaces()` để merge với backend.
- Tạo workspace bằng `createWorkspaceApi()`.
- Delete workspace bằng `deleteWorkspaceApi()`.
- Navigate tới:

```text
/workspace/{workspaceName}
```

Ghi chú:

- Có fallback localStorage nếu backend lỗi.
- Workspace route dùng name đã encode URI, backend có thể resolve name sang UUID.

### Workspace page

File: `frontend/app/workspace/[workspaceId]/page.tsx`

State chính:

- `documents`
- `chatSessions`
- `activeChatSessionId`
- `activeView`: `"chat"` hoặc `"sources"`
- `showUploadModal`

Flow:

- Decode `workspaceId` từ route.
- Load documents bằng `getDocuments(workspaceId)`.
- Load chat sessions bằng `getChatSessions(workspaceId)`.
- Khi đổi workspace, reset active chat session.
- Nếu có file status chưa final (`pending` hoặc `processing`), polling documents mỗi 2 giây.
- Chat view gồm:
  - `ChatSessionsSidebar`
  - `ChatBox`
  - `KnowledgeList`
- Sources view gồm document grid, upload, view raw content/chunks, rename/delete.

### FileUpload

File: `frontend/components/FileUpload.tsx`

Chức năng:

- Drag/drop hoặc select file.
- Chỉ accept:
  - `.pdf`
  - `.txt`
  - `.md`
- Gọi `uploadFile(files, workspaceId)`.
- Sau upload gọi callback `onUploaded()` để workspace page refresh documents.

### KnowledgeList

File: `frontend/components/KnowledgeList.tsx`

Chức năng:

- Hiển thị files trong workspace.
- Badge file_type và parse_status.
- View raw content:
  - `GET /documents/{file_id}`
- View chunks:
  - `GET /documents/{file_id}/chunks`
- Rename/delete document.

### ChatSessionsSidebar

File: `frontend/components/ChatSessionsSidebar.tsx`

Chức năng:

- List sessions.
- New chat -> parent set active session null.
- Select session -> load messages in ChatBox.
- Rename/delete session.

### ChatBox

File: `frontend/components/ChatBox.tsx`

Flow:

1. Nếu `activeSessionId` đổi, gọi `getChatMessages(activeSessionId)`.
2. User gửi question:
   - optimistic add user message vào UI.
   - gọi `sendChat(question, workspaceId, activeSessionId)`.
   - backend trả `answer` và `session_id`.
   - set active session theo `data.session_id`.
   - append assistant answer.
   - refresh session list.
3. Nếu lỗi, append assistant message:

```text
Unable to answer now: ...
```

### MessageBubble

File: `frontend/components/MessageBubble.tsx`

Render nguyên `message.content` bằng:

```tsx
<p className="whitespace-pre-wrap">{message.content}</p>
```

Không cắt answer ở UI.

## 17. Error/Status Behavior

### Upload/ingest statuses

File statuses:

```text
pending     vừa upload, chưa ingest
processing  đang parse/chunk/embed
done        ingest thành công
failed      parse/embed/store lỗi hoặc PDF parse rỗng
```

Frontend polling mỗi 2 giây nếu có file chưa `done` hoặc `failed`.

### Embedding errors

Nếu chat lỗi:

```text
Embedding service unavailable: ...
```

thì lỗi xảy ra trước LLM, ở bước embed question. Nguyên nhân thường là `EMBEDDING_API_URL`, API key, DNS/network.

### LLM errors

`llm_client.py` bắt:

- HTTPStatusError -> log status/body, trả message HTTP code.
- Exception khác -> trả message connection error.

Frontend sẽ hiển thị:

```text
Unable to answer now: Chat failed: ...
```

## 18. Các Kỹ Thuật Chính Đang Dùng

Backend:

- FastAPI cho REST API.
- Pydantic cho request/response schemas.
- Supabase Python client cho CRUD.
- asyncpg cho raw pgvector search.
- pgvector cosine similarity.
- FastAPI BackgroundTasks cho ingest không blocking upload response.
- pypdf parse PDF local.
- Optional OCR API cho PDF fallback.
- LangChain `RecursiveCharacterTextSplitter` cho chunking.
- Custom normalize heuristic cho PDF line wrapping.
- httpx async client gọi Embedding API và LLM API.

Frontend:

- Next.js App Router.
- React client components.
- TypeScript typed API wrapper.
- Tailwind CSS.
- LocalStorage fallback/merge cho workspace list.
- Polling ingest status thông qua `getDocuments`.

Data/RAG:

- Workspace-level isolation: files, chunks, sessions đều filter theo workspace_id.
- Query embedding -> pgvector search -> top chunks -> context prompt -> LLM.
- Chat history persisted theo session.
- Context trimming để tránh payload quá lớn.

## 19. Những Điểm Cần Nhớ Khi Debug

1. Upload trả về ngay, ingest chạy background. File có thể vẫn `pending/processing`.
2. File gốc nằm tạm ở `backend/data/uploads` rồi bị xóa sau ingest.
3. Raw text gốc lưu ở `files.raw_text`.
4. Chunks đã normalize lưu ở `chunks.content`.
5. Nếu đổi logic chunking, file cũ không tự đổi; cần upload lại hoặc re-ingest.
6. Chat fail ở embedding nghĩa là chưa tới LLM.
7. Chat session phải thuộc đúng workspace; backend sẽ 404 nếu session_id/workspace_id không khớp.
8. `sources` bị cắt 1200 ký tự/source, context bị cắt 12000 ký tự, nhưng answer không bị cắt bởi app.
9. Supabase service role key được backend dùng để bypass RLS; không nên expose key này ra frontend.
10. `frontend/lib/api.ts` là nơi tốt nhất để kiểm tra frontend đang gọi endpoint nào.

## 20. Mapping Endpoint Nhanh

```text
GET    /                         healthcheck

POST   /upload                   upload files + start ingest

GET    /documents/workspaces     list workspaces
POST   /documents/workspaces     create workspace
GET    /documents/workspaces/search?q=...
DELETE /documents/workspace/{workspace_id}

GET    /documents?workspace_id=...
GET    /documents/{file_id}/status
GET    /documents/{file_id}
GET    /documents/{file_id}/chunks
DELETE /documents/{file_id}?workspace_id=...
PATCH  /documents/{file_id}?workspace_id=...&new_filename=...

GET    /chat/sessions?workspace_id=...
POST   /chat/sessions
GET    /chat/sessions/{session_id}/messages
DELETE /chat/sessions/{session_id}?workspace_id=...
PATCH  /chat/sessions/{session_id}
POST   /chat

POST   /embeddings
```

## 21. Cách Chạy Thường Dùng

Backend:

```powershell
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd frontend
npm run dev
```

Mặc định frontend gọi backend:

```text
http://127.0.0.1:8000
```

trừ khi set `NEXT_PUBLIC_BACKEND_URL`.

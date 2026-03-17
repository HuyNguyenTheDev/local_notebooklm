# Local NotebookLM

Ứng dụng web giống NotebookLM, chạy hoàn toàn local với 3 tầng:

- **Frontend**: Next.js 15 + TypeScript + TailwindCSS
- **Backend**: FastAPI (Python)
- **LLM API**: Server Python trên Google Colab (qua ngrok tunnel)

Cho phép upload PDF/TXT/MD, lưu kiến thức locally, và chat dựa trên nội dung tài liệu đã upload.

## Yêu cầu hệ thống

- **Node.js**: 20 LTS hoặc mới hơn (kiểm tra: `node --version`)
- **Python**: 3.10+ (kiểm tra: `python --version`)
- **npm** hoặc **pnpm**
- **OS**: Windows, macOS, hoặc Linux

## Cấu trúc dự án

```
local_notebooklm/
├── frontend/                 # Next.js app
│   ├── app/                 # Pages & layouts
│   ├── components/          # React components
│   ├── lib/                 # Utilities & API calls
│   ├── package.json
│   └── .env.local.example
├── backend/                 # FastAPI app
│   ├── main.py             # Entry point
│   ├── routers/            # API endpoints
│   ├── services/           # Business logic
│   ├── models/             # Pydantic models
│   ├── requirements.txt
│   └── .env.example
├── .venv/                   # Python virtual env (sẽ tạo)
└── README.md
```

## Clone và cài đặt nhanh

## 1. Setup Backend (FastAPI + Python venv)

**Bước 1: Clone repo**

```bash
git clone https://github.com/HuyNguyenTheDev/local_notebooklm.git
cd local_notebooklm
```

**Bước 2: Tạo Python virtual environment (ở ROOT của project)**

```bash
python -m venv .venv
```

**Bước 3: Kích hoạt virtual environment**

**Windows (PowerShell):**
```powershell
.\.venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```cmd
.venv\Scripts\activate.bat
```

**macOS / Linux:**
```bash
source .venv/bin/activate
```

Sau khi kích hoạt thành công, bạn sẽ thấy `(.venv)` ở đầu dòng lệnh.

**Bước 4: Cài đặt dependencies backend**

```bash
pip install --upgrade pip
pip install -r backend/requirements.txt
```

**Bước 5: Tạo file `.env` cho backend**

```bash
cd backend
```

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

**Windows (CMD) / macOS / Linux:**
```bash
cp .env.example .env
```

**Bước 6: Cập nhật `backend/.env`**

Mở file `backend/.env` và điền ngrok URL (sau khi setup Colab):

```env
LLM_API_URL=https://xxxx.ngrok-free.app/chat
```

Quay lại root project:
```bash
cd ..
```

**Bước 7: Chạy backend**

```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Backend sẽ chạy tại: **http://127.0.0.1:8000**

**Để kiểm tra**:
- Health check: http://127.0.0.1:8000 (trả về status)
- Swagger API docs: http://127.0.0.1:8000/docs

## 2. Setup Frontend (Next.js)

**Bước 1: Mở terminal mới** (giữ terminal backend chạy)

```bash
cd local_notebooklm/frontend
```

**Bước 2: Cài đặt dependencies**

```bash
npm install
```

Hoặc nếu dùng `pnpm`:
```bash
pnpm install
```

**Bước 3: Tạo file `.env.local`**

**Windows (PowerShell):**
```powershell
Copy-Item .env.local.example .env.local
```

**Windows (CMD) / macOS / Linux:**
```bash
cp .env.local.example .env.local
```

**Bước 4: Cập nhật `frontend/.env.local`**

Mở file `frontend/.env.local` và kiểm tra backend URL:

```env
NEXT_PUBLIC_BACKEND_URL=http://127.0.0.1:8000
```

**Bước 5: Chạy frontend**

```bash
npm run dev
```

Frontend sẽ chạy tại: **http://localhost:3000**

Mở trình duyệt và truy cập: http://localhost:3000

## 3. Setup LLM Server (Google Colab + ngrok)

Backend sẽ gọi endpoint LLM Server để trả lời câu hỏi.

**API Backend gọi:**
```
POST {LLM_API_URL}
```

**Request từ Backend:**
```json
{
  "question": "Câu hỏi từ người dùng",
  "context": "Nội dung từ các tài liệu liên quan"
}
```

**Response dự kiến từ LLM Server:**
```json
{
  "answer": "Câu trả lời từ LLM"
}
```

**Lưu ý:**
- Nếu ngrok URL thay đổi sau khi chạy Colab, hãy cập nhật lại `backend/.env`
- Đảm bảo Colab server vẫn đang chạy khi gửi request từ frontend

## Cách sử dụng

1. **Tạo workspace**: Nhập tên workspace trên trang chủ
2. **Upload tài liệu**: Kéo-thả hoặc chọn file PDF/TXT/MD trong mỗi workspace
3. **Sửa tên file**: Kích đúp vào tên hoặc dùng nút 3 chấm (⋮)
4. **Chat**: Hỏi câu hỏi dựa trên nội dung các tài liệu đã upload
5. **Xóa tài liệu**: Dùng nút 3 chấm (⋮) → Delete
6. **Xóa workspace**: Từ trang chủ, xóa workspace hoàn toàn

## API Chính

| Endpoint | Method | Mô tả |
|----------|--------|-------|
| `/upload` | POST | Upload tài liệu (PDF/TXT/MD) |
| `/documents` | GET | Lấy danh sách tài liệu của workspace |
| `/documents/{id}` | DELETE | Xóa tài liệu |
| `/documents/{id}` | PATCH | Sửa tên tài liệu |
| `/chat` | POST | Gửi câu hỏi, nhận câu trả lời |

**Query Parameters:**
- `workspace_id`: ID của workspace (bắt buộc cho hầu hết endpoints)

**Example - Upload:**
```bash
curl -X POST http://127.0.0.1:8000/upload \
  -F "files=@document.pdf" \
  -F "workspace_id=workspace123"
```

**Example - Chat:**
```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Nội dung tài liệu nói gì?",
    "workspace_id": "workspace123"
  }'
```

## Lưu trữ dữ liệu

- **Tải lên tài liệu**: `backend/data/uploads/`
- **Metadata**: `backend/data/metadata.json` (JSON file lưu trữ thông tin tất cả tài liệu)
- **Workspace**: Lưu trong `localStorage` của trình duyệt (client-side)

## Lệnh thường dùng

**Chạy cả bộ (2 terminal)**

Terminal 1 (Backend):
```bash
# Từ root project
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2 (Frontend):
```bash
# Từ frontend/
npm run dev
```

**Build Frontend cho production:**
```bash
cd frontend
npm run build
npm start
```

**Xem Swagger API docs:**
- http://127.0.0.1:8000/docs (Swagger UI)
- http://127.0.0.1:8000/redoc (ReDoc)

## Xử lý sự cố

### Backend không khởi động

**Lỗi: "ModuleNotFoundError: No module named 'backend'"**
- ✅ Đảm bảo đang ở **ROOT** của project khi chạy `uvicorn`
- ✅ Đảm bảo `.venv` đã được kích hoạt (thấy `(.venv)` ở dòng lệnh)
- ✅ Đảm bảo chạy `pip install -r backend/requirements.txt` thành công

**Lỗi: "Address already in use"**
- Port 8000 đang bị chiếm dụng
- **Cách fix**: Chạy trên port khác:
  ```bash
  uvicorn backend.main:app --reload --host 127.0.0.1 --port 8001
  ```

### Frontend không kết nối backend

**Lỗi: "Failed to fetch from http://127.0.0.1:8000"**
- ✅ Kiểm tra `frontend/.env.local` có `NEXT_PUBLIC_BACKEND_URL=http://127.0.0.1:8000`
- ✅ Backend có chạy trên port 8000 không?
- ✅ Thử trực tiếp: http://127.0.0.1:8000 trên trình duyệt (nên thấy status)

**Lỗi: CORS (Cross-Origin Request)**
- Backend không cho phép frontend call
- Đảm bảo backend chạy từ root với `uvicorn backend.main:app ...`

### Chat không hoạt động

**Lỗi: "Chat failed" hoặc timeout**
- ✅ `LLM_API_URL` trong `backend/.env` có đúng không?
- ✅ Colab server có đang chạy không?
- ✅ ngrok tunnel có còn active không? (ngrok URL thay đổi mỗi lần restart)

**Cách kiểm tra LLM endpoint:**
```bash
curl -X POST https://xxxx.ngrok-free.app/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "test", "context": "test"}'
```

### PDF không được đọc

**Lỗi: "Unable to parse PDF"**
- PDF phải có **text layer** (không phải scan)
- Dùng OCR tool để convert nếu là scan image
- Hỗ trợ format: PDF, TXT, MD

### Node.js / npm lỗi

**Lỗi: "npm: The term 'npm' is not recognized"**
- Node.js chưa được cài hoặc không trong PATH
- **Cách fix**:
  1. Cài Node.js 20 LTS từ https://nodejs.org
  2. Restart terminal
  3. Kiểm tra: `node --version` và `npm --version`

### Python venv không hoạt động

**Lỗi kích hoạt venv**

Windows PowerShell không cho phép chạy script:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# Rồi thử lại
.\.venv\Scripts\Activate.ps1
```

## Deployment (Production)

Hiện tại setup này là cho **development local**. Để deploy production, thêm:

- ✅ **Reverse Proxy**: Nginx hoặc Caddy
- ✅ **Database**: SQLite/PostgreSQL (thay vì JSON file)
- ✅ **Authentication**: User login
- ✅ **CORS Configuration**: Chỉ cho phép domain mình
- ✅ **Logging & Monitoring**: Ghi log request/response
- ✅ **Backup**: Tự động backup metadata

## Hỗ trợ & Đóng góp

- Bug reports: Tạo issue trên GitHub
- Suggestions: Discussions hoặc Pull Requests

---

**Version**: 1.0.0 | **Last Updated**: March 2026

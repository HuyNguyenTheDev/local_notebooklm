"""
Test script để upload PDF file lên ngrok API và poll kết quả
Ngrok API endpoints: /extract-text/ và /result/{job_id}
"""

import requests
import json
import os
import sys
import time
from pathlib import Path

# Ngrok API
API_URL = "https://4bae-34-126-75-40.ngrok-free.app"
POLL_INTERVAL = 2  # seconds


def extract_text_from_pdf(pdf_path: str, poll_interval: int = POLL_INTERVAL):
    """
    Upload PDF file lên ngrok API và poll kết quả
    
    Flow:
    1. POST /extract-text/ → nhận job_id
    2. GET /result/{job_id} → poll status (queued/processing/done/error)
    3. Return result
    """
    
    if not os.path.exists(pdf_path):
        print(f"[ERROR] File không tồn tại: {pdf_path}")
        return None

    filename = os.path.basename(pdf_path)
    print(f"[INFO] Đang upload: {filename}")
    print(f"[INFO] Server: {API_URL}/extract-text/\n")

    # ── 1. Upload PDF ──────────────────────────────────────────
    try:
        with open(pdf_path, "rb") as f:
            response = requests.post(
                f"{API_URL}/extract-text/",
                files={"file": (filename, f, "application/pdf")},
                timeout=30
            )

        print(f"[INFO] Upload Status Code: {response.status_code}")

        if response.status_code != 200:
            print(f"[ERROR] Upload thất bại!")
            print(f"Response: {response.text}")
            return None

        upload_data = response.json()
        job_id = upload_data.get("job_id")
        
        print(f"[✓] Upload thành công!")
        print(f"[INFO] Job ID: {job_id}")
        print(f"[INFO] File size: {upload_data.get('file_size_bytes'):,} bytes\n")

    except requests.exceptions.ConnectionError:
        print(f"[ERROR] Không thể kết nối tới {API_URL}")
        print("Kiểm tra ngrok tunnel có còn sống không")
        return None
    except Exception as e:
        print(f"[ERROR] Lỗi upload: {e}")
        return None

    # ── 2. Poll kết quả ────────────────────────────────────────
    print(f"[INFO] Đang chờ xử lý (poll mỗi {poll_interval}s)...\n")
    
    spinner = ["|", "/", "─", "\\"]
    spin_idx = 0
    timeout = 600  # 10 phút
    elapsed = 0

    while elapsed < timeout:
        time.sleep(poll_interval)
        elapsed += poll_interval

        try:
            res = requests.get(f"{API_URL}/result/{job_id}", timeout=10)
            
            if res.status_code != 200:
                print(f"[ERROR] Không lấy được kết quả: {res.status_code}")
                return None

            result_data = res.json()
            status = result_data.get("status")

            print(f"\r[{spinner[spin_idx % len(spinner)]}] Status: {status:<12} (elapsed: {elapsed}s)", end="", flush=True)
            spin_idx += 1

            if status == "done":
                print("\n")
                return result_data.get("result")

            if status == "error":
                error_msg = result_data.get("result", "Unknown error")
                print(f"\n[ERROR] Server báo lỗi: {error_msg}")
                return None

        except Exception as e:
            print(f"\n[ERROR] Lỗi khi poll: {e}")
            return None

    print(f"\n[ERROR] Timeout sau {timeout}s")
    return None


def print_extracted_text(document: dict):
    """Hiển thị extracted text từ PDF"""
    if not document:
        print("[ERROR] Không có dữ liệu để hiển thị")
        return
    print("         KẾT QUẢ TRÍCH XUẤT VĂN BẢN TỪ PDF")

    if isinstance(document, dict):
        for page_key, text in document.items():
            page_num = page_key.replace("page_", "Trang ")
            print(f"  {page_num.upper()}")

            if text and str(text).strip():
                print(str(text).strip()[:500])  # Show first 500 chars
                if len(str(text).strip()) > 500:
                    print("  ... [truncated]")
            else:
                print("  [Không nhận dạng được văn bản]")

        print("\n" + "=" * 10)
        print(f"Tổng số trang: {len(document)}")
        print("=" * 10)
    else:
        print(f"Result type: {type(document)}")
        print(json.dumps(document, indent=2, ensure_ascii=False)[:1000])


def main():
    # Tìm file PDF để test
    pdf_files = "D:\\BKDN_KHDL\\HKI8_BKDN\\PBL7\\local_notebooklm\\1706.03762v7.pdf"
    
    # Kiểm tra nếu là string đầy đủ (hardcoded path)
    if isinstance(pdf_files, str):
        pdf_path = pdf_files
    else:
        # Nếu là list of Path objects từ glob
        if not pdf_files:
            print("[ERROR] Không tìm thấy file PDF trong thư mục hiện tại")
            print("Đặt 1 file PDF trong thư mục và chạy lại script")
            sys.exit(1)
        pdf_path = str(pdf_files[0])
    
    print(f"Tìm thấy file PDF: {pdf_path}\n")

    # Extract text từ PDF
    document = extract_text_from_pdf(pdf_path, poll_interval=POLL_INTERVAL)
    
    # Hiển thị kết quả
    if document:
        print_extracted_text(document)
    else:
        print("[ERROR] Không lấy được kết quả từ server")


if __name__ == "__main__":
    main()

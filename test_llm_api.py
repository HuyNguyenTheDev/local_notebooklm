"""
Test script để gọi LLM API qua ngrok với polling mechanism
"""

import requests
import time
import sys

# ==========================================
# 1. CẤU HÌNH ĐƯỜNG DẪN SERVER
# ==========================================
BASE_URL = "https://unamendable-shawanda-unregrettably.ngrok-free.dev"

HEADERS = {
    "Content-Type": "application/json"
}

# ==========================================
# 2. HÀM XỬ LÝ GỌI API (CƠ CHẾ POLLING)
# ==========================================
def ask_llm(prompt: str):
    """
    Gửi prompt lên LLM API và polling kết quả.
    
    Args:
        prompt: Câu hỏi/instruction từ user
    
    Returns:
        Câu trả lời từ LLM hoặc thông báo lỗi
    """
    print("\n[💭 AI đang suy nghĩ...]")
    
    # Chuẩn bị payload (đúng format của server)
    payload = {
        "text": prompt
    }
    
    # BƯỚC 1: Gửi yêu cầu tới LLM
    try:
        print(f"[INFO] Gửi request tới: {BASE_URL}/generate")
        response = requests.post(
            f"{BASE_URL}/generate", 
            json=payload, 
            headers=HEADERS,
            timeout=15
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError as e:
        return f"[❌ LỖI KẾT NỐI] Không thể kết nối tới server.\nKiểm tra lại ngrok URL.\nChi tiết: {e}"
    except requests.exceptions.Timeout:
        return "[❌ TIMEOUT] Server không phản hồi trong 15 giây"
    except requests.exceptions.RequestException as e:
        return f"[❌ LỖI REQUEST] {e}"

    try:
        job_data = response.json()
    except:
        return f"[❌ LỖI PARSE] Không thể parse response: {response.text}"
    
    job_id = job_data.get("job_id")
    
    if not job_id:
        return f"[❌ LỖI SERVER] Không nhận được Job ID.\nResponse: {job_data}"

    print(f"[✓] Job ID: {job_id}")

    # BƯỚC 2: Polling kết quả
    spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    spin_idx = 0
    poll_count = 0
    max_polls = 120  # 120 * 1.5 = 180 giây = 3 phút timeout
    
    while poll_count < max_polls:
        try:
            res = requests.get(f"{BASE_URL}/result/{job_id}", headers=HEADERS, timeout=10)
            res.raise_for_status()
            data = res.json()
            status = data.get("status")
            poll_count += 1
            
            # Hiển thị spinner
            sys.stdout.write(f"\r {spinner[spin_idx % len(spinner)]} Status: {status:<12} (poll #{poll_count})")
            sys.stdout.flush()
            spin_idx += 1
            
            # Nếu AI đã xử lý xong
            if status == "done":
                print("\r" + " " * 60 + "\r", end="")  # Xóa dòng trạng thái
                return data.get("result", "[Không có dữ liệu trả về]")
            
            # Nếu Server báo lỗi
            elif status == "error":
                print("\r" + " " * 60 + "\r", end="")
                error_msg = data.get('result', 'Unknown error')
                return f"[❌ LỖI MODEL] {error_msg}"
                
        except requests.exceptions.RequestException as e:
            poll_count += 1
            print(f"\r[⚠️  Lỗi poll #{poll_count}] {str(e)[:30]}", end="", flush=True)
        
        # Đợi 1.5 giây trước khi poll lại
        time.sleep(1.5)
    
    print("\r" + " " * 60 + "\r", end="")
    return f"[❌ TIMEOUT] Không nhận được kết quả sau {poll_count * 1.5:.0f} giây"


# ==========================================
# 3. GIAO DIỆN CHAT TRÊN TERMINAL
# ==========================================
def main():
    print("=" * 70)
    print("🤖 CHƯƠNG TRÌNH TEST LLM API QUA NGROK")
    print(f"🔗 Server: {BASE_URL}")
    print("💡 Gõ 'exit' hoặc 'quit' để thoát")
    print("=" * 70)
    
    while True:
        try:
            # Nhập prompt
            prompt = input("\n🧑 Bạn: ").strip()
            
            if not prompt:
                print("[ℹ️  ] Vui lòng nhập câu hỏi/instruction")
                continue
                
            if prompt.lower() in ['exit', 'quit']:
                print("👋 Tạm biệt!")
                break
            
            # Gọi LLM
            print()
            result = ask_llm(prompt)
            
            # Hiển thị kết quả
            print("🤖 AI:\n")
            print(result)
            print("-" * 70)
            
        except KeyboardInterrupt:
            print("\n👋 Tạm biệt!")
            break
        except Exception as e:
            print(f"[❌ LỖI] {e}")


# ==========================================
# 4. DEMO MODE (Không cần nhập từ terminal)
# ==========================================
def demo_mode():
    """Chế độ demo tự động test với mấy câu hỏi mẫu"""
    print("=" * 70)
    print("🤖 DEMO MODE - TEST LLM API")
    print(f"🔗 Server: {BASE_URL}")
    print("=" * 70)
    
    test_prompts = [
        "Xin chào, bạn là ai?",
        "Hãy giải thích Python là ngôn ngữ lập trình nào?",
        "Toán học là khoa học về cái gì?"
    ]
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n📌 Test {i}/{len(test_prompts)}")
        print(f"❓ Prompt: {prompt}")
        
        result = ask_llm(prompt)
        
        print(f"\n✅ Kết quả:\n{result}")
        print("-" * 70)


if __name__ == "__main__":
    import sys
    
    # Kiểm tra argument
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        demo_mode()
    else:
        main()

"""
Test script để kiểm tra kết nối Supabase (REST API method)
"""

import httpx
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

print("=" * 70)
print("🧪 TEST SUPABASE CONNECTION")
print("=" * 70)

# ─────────────────────────────────────────
# Test 1: HTTP reach (basic connectivity)
# ─────────────────────────────────────────
print("\n[1️⃣] Testing HTTP connectivity...")
try:
    r = httpx.get(SUPABASE_URL, timeout=10)
    print(f"    ✓ HTTP Status: {r.status_code}")
except Exception as e:
    print(f"    ✗ HTTP Error: {e}")

# ─────────────────────────────────────────
# Test 2: Sync client (basic)
# ─────────────────────────────────────────
print("\n[2️⃣] Testing Supabase sync client...")
try:
    client = create_client(SUPABASE_URL, SERVICE_KEY)
    print(f"    ✓ Client created successfully")
except Exception as e:
    print(f"    ✗ Client Error: {e}")

# ─────────────────────────────────────────
# Test 3: REST API (list tables)
# ─────────────────────────────────────────
print("\n[3️⃣] Testing REST API (list tables)...")
try:
    r = httpx.get(
        f"{SUPABASE_URL}/rest/v1/",
        headers={
            "apikey": SERVICE_KEY,
            "Authorization": f"Bearer {SERVICE_KEY}"
        },
        timeout=10
    )
    print(f"    ✓ REST API Status: {r.status_code}")
    
    # Try to parse
    try:
        data = r.json()
        if isinstance(data, list):
            print(f"    ✓ Tables found: {len(data)}")
            if data:
                for table in data[:3]:  # Show first 3
                    print(f"      - {table}")
        else:
            print(f"    Response type: {type(data)}")
    except:
        print(f"    Response (first 200 chars): {r.text[:200]}")
        
except Exception as e:
    print(f"    ✗ REST API Error: {e}")

# ─────────────────────────────────────────
# Test 4: Async version
# ─────────────────────────────────────────
print("\n[4️⃣] Testing async httpx client...")

import asyncio

async def test_async():
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{SUPABASE_URL}/rest/v1/",
                headers={
                    "apikey": SERVICE_KEY,
                    "Authorization": f"Bearer {SERVICE_KEY}"
                },
                timeout=10
            )
            print(f"    ✓ Async REST API Status: {r.status_code}")
            return True
    except Exception as e:
        print(f"    ✗ Async Error: {e}")
        return False

result = asyncio.run(test_async())

# ─────────────────────────────────────────
# Summary
# ─────────────────────────────────────────
print("\n" + "=" * 70)
if result:
    print("✅ Supabase connection looks good!")
    print("   Use REST API via httpx (async) to avoid password encoding issues")
else:
    print("⚠️ Some tests failed. Check your SUPABASE_URL and SERVICE_KEY")
print("=" * 70)

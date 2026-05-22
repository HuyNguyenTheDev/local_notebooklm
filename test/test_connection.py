"""
test_connection.py -- Chan doan ket noi Supabase toan dien.

Chay: python test_connection.py
"""
# Fix Windows terminal encoding
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import asyncio
import os
import socket
import ssl
import time
from pathlib import Path

from dotenv import load_dotenv

# Load .env
for p in [Path(".") / ".env", Path(".") / "backend" / ".env"]:
    if p.exists():
        load_dotenv(p, override=True)
        print(f"[ENV] Loaded: {p.resolve()}")
        break

RAW_URL = os.environ.get("DATABASE_URL", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

SEP = "-" * 60


def section(title: str):
    print(f"\n{SEP}\n  {title}\n{SEP}")


def parse_url(url: str) -> dict:
    try:
        no_scheme = url.split("://", 1)[1]
        userinfo, hostinfo = no_scheme.rsplit("@", 1)
        user, password = userinfo.split(":", 1)
        hostport, db = hostinfo.split("/", 1)
        host, port = hostport.rsplit(":", 1) if ":" in hostport else (hostport, "5432")
        return {"user": user, "password": password, "host": host, "port": int(port), "db": db}
    except Exception as e:
        return {"error": str(e)}


def check_tcp(host: str, port: int, timeout: float = 6.0) -> tuple:
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True, "TCP OK"
    except socket.timeout:
        return False, f"TIMEOUT ({timeout}s)"
    except socket.gaierror as e:
        return False, f"DNS FAIL: {e}"
    except ConnectionRefusedError:
        return False, "CONNECTION REFUSED"
    except OSError as e:
        return False, str(e)


def check_dns(host: str) -> tuple:
    try:
        results = socket.getaddrinfo(host, None)
        ips = list({r[4][0] for r in results})
        ipv4 = [ip for ip in ips if ":" not in ip]
        ipv6 = [ip for ip in ips if ":" in ip]
        parts = []
        if ipv4:
            parts.append(f"IPv4: {', '.join(ipv4)}")
        if ipv6:
            parts.append(f"IPv6: {ipv6[0][:20]}...")
        return True, " | ".join(parts)
    except socket.gaierror as e:
        return False, f"DNS FAIL: {e}"


async def check_asyncpg(url: str, label: str) -> tuple:
    try:
        import asyncpg
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        start = time.time()
        conn = await asyncpg.connect(url, ssl=ssl_ctx, timeout=10)
        db = await conn.fetchval("SELECT current_database()")
        ver = await conn.fetchval("SELECT version()")
        await conn.close()
        elapsed = time.time() - start
        return True, f"OK ({elapsed:.2f}s) | DB={db} | {ver[:50]}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


async def check_supabase_rest() -> tuple:
    try:
        from supabase import acreate_client
        client = await acreate_client(SUPABASE_URL, SERVICE_KEY)
        result = await client.table("workspaces").select("id").limit(1).execute()
        return True, f"OK | {len(result.data)} rows returned"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


async def check_http() -> tuple:
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(SUPABASE_URL)
        return True, f"HTTP {r.status_code}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


async def main():
    print("\n" + "=" * 60)
    print("  SUPABASE CONNECTION DIAGNOSTICS")
    print("=" * 60)

    # --- Section 0 ---
    section("0. Cau hinh hien tai")
    print(f"  SUPABASE_URL : {SUPABASE_URL}")
    print(f"  SERVICE_KEY  : {SERVICE_KEY[:30]}...")
    print(f"  DATABASE_URL : {RAW_URL}")

    if not RAW_URL:
        print("\n[FATAL] DATABASE_URL chua duoc set!")
        return

    info = parse_url(RAW_URL)
    if "error" in info:
        print(f"\n[FATAL] Khong parse duoc DATABASE_URL: {info['error']}")
        return

    host = info["host"]
    port = info["port"]
    user = info["user"]
    password = info["password"]
    db = info["db"]
    ref = SUPABASE_URL.split("//")[1].split(".")[0] if SUPABASE_URL else ""

    print(f"\n  -> Host    : {host}")
    print(f"  -> Port    : {port}")
    print(f"  -> User    : {user}")
    print(f"  -> DB      : {db}")
    print(f"  -> Ref ID  : {ref}")

    # --- Section 1: HTTP ---
    section("1. HTTP toi Supabase HTTPS endpoint")
    ok, msg = await check_http()
    print(f"  [{'OK' if ok else 'FAIL'}] {msg}")

    # --- Section 2: DNS ---
    section("2. DNS Resolution")
    check_hosts = [
        host,
        f"aws-0-ap-southeast-1.pooler.{ref}.supabase.co",
        f"aws-0-us-east-1.pooler.{ref}.supabase.co",
    ]
    for h in check_hosts:
        ok, msg = check_dns(h)
        print(f"  [{'OK' if ok else 'FAIL'}] {h}")
        print(f"         -> {msg}")

    # --- Section 3: TCP ---
    section("3. TCP Port Check (raw socket, khong can auth)")
    tcp_tests = [
        (host, 5432),
        (f"aws-0-ap-southeast-1.pooler.{ref}.supabase.co", 5432),
        (f"aws-0-ap-southeast-1.pooler.{ref}.supabase.co", 6543),
    ]
    for h, p in tcp_tests:
        ok, msg = check_tcp(h, p)
        print(f"  [{'OK' if ok else 'FAIL'}] {h}:{p} -> {msg}")

    # --- Section 4: asyncpg ---
    section("4. asyncpg Connection Test (voi SSL)")
    pooler_host = f"aws-0-ap-southeast-1.pooler.{ref}.supabase.co"
    urls_to_test = [
        (RAW_URL,
         "Direct (tu .env)"),
        (f"postgresql://{user}:{password}@{host}:{port}/{db}?sslmode=require",
         "Direct + sslmode=require"),
        (f"postgresql://postgres.{ref}:{password}@{pooler_host}:5432/{db}",
         "Session Pooler port 5432"),
        (f"postgresql://postgres.{ref}:{password}@{pooler_host}:6543/{db}",
         "Transaction Pooler port 6543"),
        (f"postgresql://{user}:{password}@{pooler_host}:5432/{db}",
         "Session Pooler (user goc, port 5432)"),
    ]

    working_url = None
    for url, label in urls_to_test:
        print(f"\n  >> {label}")
        ok, msg = await check_asyncpg(url, label)
        print(f"     [{'OK' if ok else 'FAIL'}] {msg}")
        if ok and not working_url:
            working_url = url

    # --- Section 5: Supabase REST ---
    section("5. Supabase REST API (supabase-py client)")
    ok, msg = await check_supabase_rest()
    print(f"  [{'OK' if ok else 'FAIL'}] {msg}")

    # --- Section 6: Ket luan ---
    section("6. KET LUAN")
    if working_url:
        print(f"\n  [SUCCESS] URL hoat dong:\n    {working_url}")
        print(f"\n  -> Cap nhat DATABASE_URL trong .env thanh URL tren")
    else:
        print("\n  [FAIL] Khong co URL nao hoat dong.")
        print()
        print("  NGUYEN NHAN PHO BIEN:")
        print()
        print("  [A] Supabase project bi PAUSED (free tier tu pause sau 1 tuan)")
        print("      -> Vao Supabase Dashboard -> Nhan 'Resume project'")
        print("      -> https://supabase.com/dashboard/project/" + ref)
        print()
        print("  [B] Sai password trong DATABASE_URL")
        print("      -> Vao Settings -> Database -> Reset database password")
        print("      -> Sau do copy lai connection string moi")
        print()
        print("  [C] Firewall/ISP block port 5432 va 6543")
        print("      -> Thu doi mang (dung mobile hotspot)")
        print("      -> Hoac dung Supabase REST API thay vi direct connection")
        print()
        print("  [D] Neu REST API (Section 5) OK nhung asyncpg FAIL:")
        print("      -> Co the chi can dung supabase-py REST API thay asyncpg")
        print("      -> Kien truc van hoat dong, chi mat vector search truc tiep")


if __name__ == "__main__":
    asyncio.run(main())

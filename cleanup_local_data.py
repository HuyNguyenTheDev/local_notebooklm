"""
Script để clear local workspace data và chuẩn bị cho Supabase migration
"""

import os
import json
from pathlib import Path
from datetime import datetime

# ==========================================
# 1. Tìm local data files
# ==========================================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "backend" / "data"
UPLOADS_DIR = DATA_DIR / "uploads"

FILES_TO_CLEAR = [
    DATA_DIR / "workspaces.json",
    DATA_DIR / "metadata.json"
]

print("=" * 70)
print("🗑️  LOCAL DATA CLEANUP — SUPABASE MIGRATION PREP")
print("=" * 70)

# ==========================================
# 2. Backup before clear
# ==========================================
print("\n[1️⃣] Backup existing data...")

BACKUP_DIR = DATA_DIR / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

try:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    for file_path in FILES_TO_CLEAR:
        if file_path.exists():
            backup_file = BACKUP_DIR / file_path.name
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"    ✓ Backed up: {file_path.name} → {backup_file}")
        else:
            print(f"    - {file_path.name} (không tồn tại)")
    
    print(f"\n    📦 Backup folder: {BACKUP_DIR}")
    
except Exception as e:
    print(f"    ✗ Backup failed: {e}")
    exit(1)

# ==========================================
# 3. Show data before clear
# ==========================================
print("\n[2️⃣] Current local data:")

for file_path in FILES_TO_CLEAR:
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"\n    📄 {file_path.name}:")
        print(f"       Items: {len(data)}")
        if data:
            print(f"       Preview: {json.dumps(data[:1], ensure_ascii=False, indent=6)}")
    else:
        print(f"\n    📄 {file_path.name}: (không tồn tại)")

# ==========================================
# 4. Show uploads
# ==========================================
print("\n[3️⃣] Local uploaded files:")

if UPLOADS_DIR.exists():
    files = list(UPLOADS_DIR.glob("*"))
    print(f"    Total files: {len(files)}")
    for f in files[:5]:
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"    - {f.name} ({size_mb:.2f} MB)")
    if len(files) > 5:
        print(f"    ... and {len(files) - 5} more")
else:
    print(f"    (uploads folder doesn't exist)")

# ==========================================
# 5. Ask confirmation
# ==========================================
print("\n" + "=" * 70)
response = input("\n❓ Clear local data và giữ backup? (y/n): ").strip().lower()

if response != 'y':
    print("❌ Cancelled. Local data kept.")
    exit(0)

# ==========================================
# 6. Clear data
# ==========================================
print("\n[4️⃣] Clearing local data...")

try:
    for file_path in FILES_TO_CLEAR:
        if file_path.exists():
            # Clear but keep structure (empty array)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False)
            print(f"    ✓ Cleared: {file_path.name}")
        
except Exception as e:
    print(f"    ✗ Clear failed: {e}")
    exit(1)

# ==========================================
# 7. Optional: Ask if clear uploads too
# ==========================================
print("\n[5️⃣] Uploaded files:")
response2 = input("   Clear uploads folder? (y/n): ").strip().lower()

if response2 == 'y':
    try:
        if UPLOADS_DIR.exists():
            for file in UPLOADS_DIR.glob("*"):
                file.unlink()
                print(f"    ✓ Deleted: {file.name}")
            print(f"    ✓ Uploads folder cleared")
    except Exception as e:
        print(f"    ✗ Error: {e}")

# ==========================================
# 8. Summary
# ==========================================
print("\n" + "=" * 70)
print("✅ CLEANUP COMPLETE!")
print("=" * 70)
print(f"""
Next steps:
1. Run Supabase migration (supabase_migration.sql)
2. Configure .env with Supabase credentials
3. Update routers to use supabase_rest client
4. Test API endpoints
5. Upload files to Supabase

Backup saved at: {BACKUP_DIR}
""")

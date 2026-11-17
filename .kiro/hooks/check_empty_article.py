#!/usr/bin/env python3
"""
Hook: PostFileSave + PostFileCreate
Fires when any content/*.md file is saved or created.
Exits 2 (Kiro shows error) if the file is empty.
"""
import json
import os
import sys

# --- 1. Try every possible way Kiro might pass the file path ---

file_path = ""

# 1a. Command-line argument
if not file_path and len(sys.argv) > 1:
    file_path = sys.argv[1]

# 1b. Environment variables Kiro might set
if not file_path:
    for env_key in ("KIRO_FILE_PATH", "KIRO_FILE", "FILE_PATH", "FILE"):
        file_path = os.environ.get(env_key, "")
        if file_path:
            break

# 1c. stdin JSON — try reading without blocking
if not file_path:
    try:
        import select
        if select.select([sys.stdin], [], [], 0.5)[0]:
            raw = sys.stdin.read()
            if raw.strip():
                data = json.loads(raw)
                for key in ("filePath", "file", "path", "absolutePath", "uri"):
                    file_path = data.get(key, "")
                    if file_path:
                        # strip file:// prefix if present
                        if file_path.startswith("file://"):
                            file_path = file_path[7:]
                        break
    except Exception:
        pass

# --- 2. If we still have no path, log to a debug file and exit cleanly ---
if not file_path:
    debug_log = os.path.join(
        os.path.dirname(__file__), "hook_debug.log"
    )
    with open(debug_log, "a") as f:
        import datetime
        f.write(f"{datetime.datetime.now().isoformat()} | no file_path | argv={sys.argv} | env_keys={list(os.environ.keys())}\n")
    sys.exit(0)

# --- 3. Check if the file is empty ---
if not os.path.isfile(file_path):
    sys.exit(0)

if os.path.getsize(file_path) == 0:
    msg = (
        f"\n"
        f"⚠️  EMPTY ARTICLE — PELICAN WILL SKIP THIS FILE\n"
        f"   {file_path}\n"
        f"\n"
        f"   Add Title, Date, and body content, then save again.\n"
        f"   It will NOT appear in devserver or after publish until it has content.\n"
    )
    print(msg, file=sys.stderr)
    sys.exit(2)

sys.exit(0)

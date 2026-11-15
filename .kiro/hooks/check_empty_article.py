#!/usr/bin/env python3
"""
Hook script: PostFileSave
Checks if a saved content/*.md file is empty.
Exits 2 (blocks + shows error in Kiro) if the file has no content.
"""
import json
import os
import sys

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

# Kiro passes the saved file path under one of these keys
file_path = (
    data.get("filePath")
    or data.get("file")
    or data.get("path")
    or ""
)

if not file_path:
    sys.exit(0)

if not os.path.isfile(file_path):
    sys.exit(0)

if os.path.getsize(file_path) == 0:
    print(
        f"\n⚠️  EMPTY ARTICLE DETECTED\n"
        f"   File : {file_path}\n"
        f"   Fix  : Add content (Title, Date, body) then save again.\n"
        f"   Until then Pelican will silently skip this article —\n"
        f"   it will NOT appear in devserver or after publish.\n",
        file=sys.stderr,
    )
    sys.exit(2)

sys.exit(0)

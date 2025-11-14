#!/usr/bin/env python3
"""
Tripo3D Task 응답 구조 디버깅
"""

import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

TRIPO_API_KEY = os.getenv("TRIPO_API_KEY")
TRIPO_BASE_URL = "https://api.tripo3d.ai/v2/openapi"

TASK_IDS = [
    ("spaceship", os.getenv("MESH_SPACESHIP_TASK_ID")),
    ("locket", os.getenv("MESH_LOCKET_TASK_ID")),
    ("character", os.getenv("MESH_CHARACTER_TASK_ID")),
]

for name, task_id in TASK_IDS:
    if not task_id:
        print(f"⚠️ {name} Task ID 없음")
        continue

    print(f"\n{'='*80}")
    print(f"📊 {name.upper()} - Task ID: {task_id}")
    print(f"{'='*80}")

    url = f"{TRIPO_BASE_URL}/task/{task_id}"
    headers = {"Authorization": f"Bearer {TRIPO_API_KEY}"}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json()
        print("\n전체 응답:")
        print(json.dumps(data, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"❌ 오류: {e}")

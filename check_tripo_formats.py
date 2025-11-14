#!/usr/bin/env python3
"""
Tripo3D에서 제공하는 모든 출력 형식 확인
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

TRIPO_API_KEY = os.getenv("TRIPO_API_KEY")
TRIPO_BASE_URL = "https://api.tripo3d.ai/v2/openapi"

# 우리의 Task ID들
TASK_IDS = {
    "spaceship": os.getenv("MESH_SPACESHIP_TASK_ID"),
    "locket": os.getenv("MESH_LOCKET_TASK_ID"),
    "character": os.getenv("MESH_CHARACTER_TASK_ID"),
}

print("=" * 80)
print("🔍 Tripo3D 출력 형식 분석")
print("=" * 80)

for name, task_id in list(TASK_IDS.items())[:1]:  # 첫번째만 확인
    if not task_id:
        continue

    url = f"{TRIPO_BASE_URL}/task/{task_id}"
    headers = {"Authorization": f"Bearer {TRIPO_API_KEY}"}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        data = response.json().get("data", {})
        result = data.get("result", {})
        output = data.get("output", {})

        print(f"\n📋 Task: {name}")
        print(f"Type: {data.get('type')}")
        print(f"\n🔹 result 섹션:")
        for key, value in result.items():
            if isinstance(value, dict):
                print(f"  - {key}:")
                for k, v in value.items():
                    if k != "url":
                        print(f"      {k}: {v}")
                    else:
                        print(f"      {k}: {v[:60]}...")
            else:
                print(f"  - {key}: {value}")

        print(f"\n🔹 output 섹션:")
        for key, value in output.items():
            if isinstance(value, str) and "http" in value:
                print(f"  - {key}: {value[:60]}...")
            else:
                print(f"  - {key}: {value}")

        print(f"\n🔹 input 섹션 (요청 파라미터):")
        input_data = data.get("input", {})
        for key, value in input_data.items():
            if key not in ["file", "object"]:
                print(f"  - {key}: {value}")

    except Exception as e:
        print(f"❌ 오류: {e}")

print("\n" + "=" * 80)
print("📝 분석:")
print("=" * 80)
print("""
1. result 섹션: 구조화된 형식 (type 정보 포함)
2. output 섹션: 직접 다운로드 가능한 URL
3. 현재 모든 파일이 .glb 형식인 이유:
   - Tripo3D texture_model: glb 반환
   - Tripo3D image_to_model: pbr_model (glb)

4. FBX가 필요하면:
   - API 파라미터로 형식 지정 가능?
   - 아니면 glb → fbx 변환 필요?
""")

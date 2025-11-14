#!/usr/bin/env python3
"""
Tripo3D image_to_model API 성능 테스트
data/TEST.png를 사용하여 이미지에서 바로 3D 생성

시간 측정:
1. 이미지 업로드
2. image_to_model API 호출
3. Task 완료 대기
4. GLB 다운로드

총 소요 시간과 기존 방식 비교
"""

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

TRIPO_API_KEY = os.getenv("TRIPO_API_KEY")
TRIPO_BASE_URL = "https://api.tripo3d.ai/v2/openapi"

print("=" * 80)
print("🧪 Tripo3D image_to_model 성능 테스트")
print("=" * 80)

# 테스트 이미지 경로
test_image_path = "/mnt/d/UbuntuProjects/tw_project/data/TEST.png"

if not os.path.exists(test_image_path):
    print(f"❌ 파일 없음: {test_image_path}")
    exit(1)

print(f"📸 사용 이미지: {test_image_path}")

# ============================================================
# 1️⃣ 이미지 업로드
# ============================================================
print("\n" + "=" * 80)
print("1️⃣ 이미지 업로드")
print("=" * 80)

start_upload = time.time()

with open(test_image_path, 'rb') as f:
    image_bytes = f.read()

upload_url = f"{TRIPO_BASE_URL}/upload/sts"
headers = {"Authorization": f"Bearer {TRIPO_API_KEY}"}
files = {"file": ("TEST.png", image_bytes, "image/png")}

print(f"📤 업로드 중... ({len(image_bytes) / 1024:.1f} KB)")
response = requests.post(upload_url, headers=headers, files=files, timeout=30)
result = response.json()

if result.get("code") != 0:
    print(f"❌ 업로드 실패: {result}")
    exit(1)

image_token = result.get("data", {}).get("image_token")
upload_time = time.time() - start_upload

print(f"✅ 업로드 완료")
print(f"⏱️  소요 시간: {upload_time:.2f}초")
print(f"   토큰: {image_token[:30]}...")

# ============================================================
# 2️⃣ image_to_model API 호출
# ============================================================
print("\n" + "=" * 80)
print("2️⃣ image_to_model API 호출")
print("=" * 80)

start_api = time.time()

payload = {
    "type": "image_to_model",
    "file": {
        "type": "png",
        "file_token": image_token
    },
    "texture": True,
    "pbr": True,
    "model_version": "v2.5-20250123",
}

print(f"📤 image_to_model 요청 전송...")
response = requests.post(
    f"{TRIPO_BASE_URL}/task",
    headers=headers,
    json=payload,
    timeout=30
)

result = response.json()
task_id = result.get("data", {}).get("task_id")
api_time = time.time() - start_api

if not task_id:
    print(f"❌ API 호출 실패: {result}")
    exit(1)

print(f"✅ Task 생성 완료")
print(f"   Task ID: {task_id}")
print(f"⏱️  소요 시간: {api_time:.2f}초")

# ============================================================
# 3️⃣ Task 완료 대기 (polling)
# ============================================================
print("\n" + "=" * 80)
print("3️⃣ Task 완료 대기 (최대 10분)")
print("=" * 80)

start_polling = time.time()
max_wait = 600
poll_interval = 5

model_url = None

for i in range(0, max_wait, poll_interval):
    response = requests.get(
        f"{TRIPO_BASE_URL}/task/{task_id}",
        headers=headers,
        timeout=30
    )

    task_data = response.json().get("data", {})
    status = task_data.get("status")
    progress = task_data.get("progress", 0)

    elapsed_poll = time.time() - start_polling
    print(f"⏳ 진행률: {progress:3d}% | 상태: {status:8s} | 경과: {elapsed_poll:6.1f}초", end="\r")

    if status == "success":
        print(f"\n✅ Task 완료!")
        result = task_data.get("result", {})
        output = task_data.get("output", {})

        # GLB URL 추출
        model_url = (
            result.get("pbr_model", {}).get("url") or
            output.get("pbr_model")
        )

        if model_url:
            print(f"   GLB URL 획득")
        break

    elif status in ["failed", "error"]:
        print(f"\n❌ Task 실패!")
        exit(1)

    time.sleep(poll_interval)

polling_time = time.time() - start_polling

if not model_url:
    print(f"❌ GLB URL을 찾을 수 없음")
    exit(1)

print(f"⏱️  소요 시간: {polling_time:.2f}초")

# ============================================================
# 4️⃣ GLB 다운로드
# ============================================================
print("\n" + "=" * 80)
print("4️⃣ GLB 파일 다운로드")
print("=" * 80)

start_download = time.time()

print(f"📥 다운로드 중...")
response = requests.get(model_url, timeout=60)

glb_bytes = response.content
download_time = time.time() - start_download

glb_path = "/mnt/d/UbuntuProjects/tw_project/test_output_image_to_3d.glb"
with open(glb_path, "wb") as f:
    f.write(glb_bytes)

glb_size_mb = len(glb_bytes) / 1024 / 1024

print(f"✅ 다운로드 완료")
print(f"   저장: {glb_path}")
print(f"   파일 크기: {glb_size_mb:.2f} MB")
print(f"⏱️  소요 시간: {download_time:.2f}초")

# ============================================================
# 📊 전체 요약
# ============================================================
total_time = time.time() - start_upload

print("\n" + "=" * 80)
print("📊 성능 분석 요약")
print("=" * 80)

print(f"\n⏱️  단계별 소요 시간:")
print(f"  1️⃣  이미지 업로드:     {upload_time:6.2f}초")
print(f"  2️⃣  API 호출:          {api_time:6.2f}초")
print(f"  3️⃣  Task 대기 (생성):   {polling_time:6.2f}초  ⭐ 가장 오래 걸림")
print(f"  4️⃣  GLB 다운로드:      {download_time:6.2f}초")
print(f"  {'─' * 40}")
print(f"  💯 전체 소요 시간:      {total_time:6.2f}초")

print(f"\n📈 시간 분석:")
if total_time > 0:
    print(f"  - Task 생성: {polling_time / total_time * 100:.1f}% (가장 오래 걸리는 부분)")
    print(f"  - 나머지:    {(total_time - polling_time) / total_time * 100:.1f}%")

print(f"\n📊 파일 크기:")
print(f"  - 입력 이미지: {len(image_bytes) / 1024:.1f} KB")
print(f"  - 출력 GLB:   {glb_size_mb:.2f} MB")

# ============================================================
# 결론
# ============================================================
print("\n" + "=" * 80)
print("🎯 결론")
print("=" * 80)

print(f"""
image_to_model (이미지에서 바로 3D 생성):
  💯 전체 시간: {total_time:.2f}초 ({int(total_time // 60)}분 {int(total_time % 60)}초)

주요 특징:
  ✅ 기존 메시 제약 없음
  ✅ 아이의 그림 스타일 그대로 반영
  ✅ 더 창의적인 모양 가능
  ✅ 관리가 간단함 (메시 3개 따로 저장 필요 없음)
""")

print("=" * 80)

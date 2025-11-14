#!/usr/bin/env python3
"""
최종 테스트: image_to_model을 사용하는 새로운 워크플로우
- Vision 모델로 도안명 + 아이 이름 추출
- image_to_model로 3D 생성
- 전체 파이프라인 성능 측정
"""

import os
import time
import requests
import base64
from dotenv import load_dotenv
from backend.tripo_client import Tripo3DClient
from backend.vision_model import analyze_drawing_text

load_dotenv()

TRIPO_API_KEY = os.getenv("TRIPO_API_KEY")

print("=" * 80)
print("🧪 최종 테스트: Image-to-Model 파이프라인 성능")
print("=" * 80)

# 테스트 이미지 경로
test_image_path = "/mnt/d/UbuntuProjects/tw_project/data/TEST.png"

if not os.path.exists(test_image_path):
    print(f"❌ 파일 없음: {test_image_path}")
    exit(1)

print(f"📸 사용 이미지: {test_image_path}")

# ============================================================
# 1️⃣ 이미지 읽기
# ============================================================
print("\n" + "=" * 80)
print("1️⃣ 이미지 읽기")
print("=" * 80)

start_total = time.time()
start_read = time.time()

with open(test_image_path, 'rb') as f:
    image_bytes = f.read()

image_b64 = base64.b64encode(image_bytes).decode("utf-8")
read_time = time.time() - start_read

print(f"✅ 읽기 완료")
print(f"⏱️  소요 시간: {read_time:.2f}초")
print(f"📊 파일 크기: {len(image_bytes) / 1024:.1f} KB")

# ============================================================
# 2️⃣ Vision 모델로 도안명 & 아이 이름 추출
# ============================================================
print("\n" + "=" * 80)
print("2️⃣ Vision 모델 분석")
print("=" * 80)

start_vision = time.time()
vision_result = analyze_drawing_text(image_b64)
design = vision_result.get("design", "Unknown")
child_name = vision_result.get("child_name", "Unknown")
vision_time = time.time() - start_vision

print(f"✅ 분석 완료")
print(f"⏱️  소요 시간: {vision_time:.2f}초")
print(f"📊 결과:")
print(f"   - 도안명: {design}")
print(f"   - 아이 이름: {child_name}")

# ============================================================
# 3️⃣ Tripo3D Client 초기화 및 이미지 업로드
# ============================================================
print("\n" + "=" * 80)
print("3️⃣ 이미지 업로드")
print("=" * 80)

tripo_client = Tripo3DClient()

start_upload = time.time()
image_token = tripo_client.upload_image(image_bytes, file_type="png")
upload_time = time.time() - start_upload

if not image_token:
    print(f"❌ 이미지 업로드 실패")
    exit(1)

print(f"✅ 업로드 완료")
print(f"⏱️  소요 시간: {upload_time:.2f}초")
print(f"   토큰: {image_token[:30]}...")

# ============================================================
# 4️⃣ image_to_model API 호출
# ============================================================
print("\n" + "=" * 80)
print("4️⃣ image_to_model API 호출")
print("=" * 80)

start_api = time.time()
tripo_result = tripo_client.image_to_model(
    image_token=image_token,
    model_version="v2.5-20250123"
)
api_time = time.time() - start_api

task_id = tripo_result.get("data", {}).get("task_id")
if not task_id:
    print(f"❌ Task 생성 실패: {tripo_result}")
    exit(1)

print(f"✅ Task 생성 완료")
print(f"⏱️  소요 시간: {api_time:.2f}초")
print(f"   Task ID: {task_id}")

# ============================================================
# 5️⃣ Task 완료 대기 (polling)
# ============================================================
print("\n" + "=" * 80)
print("5️⃣ Task 완료 대기 (최대 10분)")
print("=" * 80)

import asyncio

async def wait_for_completion():
    start_polling = time.time()
    result = await tripo_client.wait_for_task_completion(task_id, max_wait=600)
    polling_time = time.time() - start_polling
    return result, polling_time

result, polling_time = asyncio.run(wait_for_completion())

if not result:
    print(f"❌ Task 실패 또는 타임아웃")
    exit(1)

model_url = result.get("model_url")
print(f"✅ Task 완료!")
print(f"⏱️  소요 시간: {polling_time:.2f}초")
print(f"   GLB URL 획득: {model_url[:50]}...")

# ============================================================
# 6️⃣ GLB 다운로드
# ============================================================
print("\n" + "=" * 80)
print("6️⃣ GLB 파일 다운로드")
print("=" * 80)

start_download = time.time()
response = requests.get(model_url, timeout=60)
glb_bytes = response.content
download_time = time.time() - start_download

glb_path = "/mnt/d/UbuntuProjects/tw_project/test_output_final.glb"
with open(glb_path, "wb") as f:
    f.write(glb_bytes)

glb_size_mb = len(glb_bytes) / 1024 / 1024

print(f"✅ 다운로드 완료")
print(f"⏱️  소요 시간: {download_time:.2f}초")
print(f"   저장: {glb_path}")
print(f"   파일 크기: {glb_size_mb:.2f} MB")

# ============================================================
# 📊 전체 요약
# ============================================================
total_time = time.time() - start_total

print("\n" + "=" * 80)
print("📊 성능 분석 요약")
print("=" * 80)

print(f"\n⏱️  단계별 소요 시간:")
print(f"  1️⃣  이미지 읽기:     {read_time:6.2f}초")
print(f"  2️⃣  Vision 분석:     {vision_time:6.2f}초")
print(f"  3️⃣  이미지 업로드:   {upload_time:6.2f}초")
print(f"  4️⃣  API 호출:        {api_time:6.2f}초")
print(f"  5️⃣  Task 대기:       {polling_time:6.2f}초  ⭐ 가장 오래 걸림")
print(f"  6️⃣  GLB 다운로드:    {download_time:6.2f}초")
print(f"  {'─' * 40}")
print(f"  💯 전체 소요 시간:    {total_time:6.2f}초 ({int(total_time // 60)}분 {int(total_time % 60)}초)")

print(f"\n📈 시간 분석:")
if total_time > 0:
    print(f"  - Task 대기: {polling_time / total_time * 100:.1f}% (가장 오래 걸리는 부분)")
    print(f"  - 나머지:    {(total_time - polling_time) / total_time * 100:.1f}%")

print(f"\n📊 파일 크기:")
print(f"  - 입력 이미지:  {len(image_bytes) / 1024:.1f} KB")
print(f"  - 출력 GLB:    {glb_size_mb:.2f} MB")

# ============================================================
# 결론
# ============================================================
print("\n" + "=" * 80)
print("🎯 결론")
print("=" * 80)

print(f"""
✅ image_to_model (이미지에서 바로 3D 생성):
  💯 전체 시간: {total_time:.2f}초 ({int(total_time // 60)}분 {int(total_time % 60)}초)

주요 특징:
  ✅ 아이의 그림 스타일 그대로 반영
  ✅ 더 창의적인 모양 가능
  ✅ 관리가 간단함 (메시 3개 따로 저장 필요 없음)
  ✅ Vision 모델로 도안명 & 아이 이름 자동 추출

아키텍처:
  📦 Simple: 이미지 → 업로드 → image_to_model → 3D 모델 완성
  🔄 Workflow: 도안명/이름 추출 → 3D 생성 → Unity에 전달
""")

print("=" * 80)

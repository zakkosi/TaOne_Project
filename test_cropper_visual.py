#!/usr/bin/env python3
"""
이미지 크로퍼 시각 테스트
- 원본 이미지와 크로핑된 이미지를 frontend/uploaded에 저장
- 실제로 어떻게 잘리는지 확인 가능
"""

import os
from Utils.image_cropper import crop_top_section

# 경로 설정
test_image_path = "/mnt/d/UbuntuProjects/tw_project/data/TEST.png"
output_dir = "/mnt/d/UbuntuProjects/tw_project/frontend/uploaded"

os.makedirs(output_dir, exist_ok=True)

print("=" * 80)
print("🖼️  이미지 크로퍼 시각 테스트")
print("=" * 80)

if not os.path.exists(test_image_path):
    print(f"❌ 파일 없음: {test_image_path}")
    exit(1)

# 원본 이미지 읽기
with open(test_image_path, 'rb') as f:
    original_bytes = f.read()

print(f"\n📸 원본 이미지")
print(f"   경로: {test_image_path}")
print(f"   크기: {len(original_bytes) / 1024:.1f} KB")

# 원본 저장
original_path = os.path.join(output_dir, "TEST_original.png")
with open(original_path, "wb") as f:
    f.write(original_bytes)
print(f"   저장: {original_path}")

# 크로핑 (상단 15% 제거)
print(f"\n🔪 크로핑 중...")
print(f"   방식: 상단 15% 제거 (텍스트 부분)")
cropped_bytes = crop_top_section(original_bytes, ratio=0.15)

print(f"\n✂️  크로핑된 이미지")
print(f"   크기: {len(cropped_bytes) / 1024:.1f} KB")
print(f"   감소량: {len(original_bytes) - len(cropped_bytes)} bytes")

# 크로핑된 이미지 저장
cropped_path = os.path.join(output_dir, "TEST_cropped_15pct.jpg")
with open(cropped_path, "wb") as f:
    f.write(cropped_bytes)
print(f"   저장: {cropped_path}")

# 다른 비율도 테스트
print(f"\n" + "=" * 80)
print("📊 다양한 비율로 테스트")
print("=" * 80)

for ratio in [0.10, 0.15, 0.20, 0.25]:
    cropped = crop_top_section(original_bytes, ratio=ratio)
    filename = f"TEST_cropped_{int(ratio*100)}pct.jpg"
    filepath = os.path.join(output_dir, filename)
    with open(filepath, "wb") as f:
        f.write(cropped)
    pct_reduction = (1 - len(cropped) / len(original_bytes)) * 100
    print(f"   {ratio*100:3.0f}% 제거: {len(cropped)/1024:6.1f} KB ({pct_reduction:.1f}% 감소) → {filename}")

print(f"\n" + "=" * 80)
print("💾 업로드 폴더 목록")
print("=" * 80)

files = sorted(os.listdir(output_dir))
for filename in files:
    filepath = os.path.join(output_dir, filename)
    if os.path.isfile(filepath):
        size_kb = os.path.getsize(filepath) / 1024
        print(f"   {filename} ({size_kb:.1f} KB)")

print(f"\n✨ 완료! frontend/uploaded 폴더에서 이미지 확인 가능")
print(f"   원본과 크로핑된 이미지를 비교해보세요!")

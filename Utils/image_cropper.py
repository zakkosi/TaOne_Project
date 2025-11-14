# backend/utils/image_cropper.py
from PIL import Image
from io import BytesIO

def crop_top_section(image_bytes: bytes, ratio: float = 0.15, orientation: str = "auto", rotate_cw: int = 90) -> bytes:
    """
    이미지를 처리하는 함수 (회전 → 크로핑)

    Args:
        image_bytes: 원본 이미지 (bytes)
        ratio: 잘라낼 비율 (기본값 0.15 = 상단 15% 제거)
        orientation: "auto" (자동감지), "portrait" (세로-상단자르기), "landscape" (가로-좌측자르기)
        rotate_cw: 시계방향 회전 각도 (기본값 90도)

    Returns:
        bytes: 처리된 이미지 (JPEG)
    """
    img = Image.open(BytesIO(image_bytes))

    # 1️⃣ 시계방향으로 회전 (카메라가 가로로 찍은 이미지를 세로로)
    if rotate_cw != 0:
        print(f"[ImageCropper] 🔄 이미지를 시계방향 {rotate_cw}도 회전 중...")
        img = img.rotate(-rotate_cw, expand=True)  # PIL은 반시계방향이므로 음수

    width, height = img.size

    # 2️⃣ 방향 자동 감지
    if orientation == "auto":
        is_landscape = width > height  # 가로가 더 길면 가로 방향
        orientation = "landscape" if is_landscape else "portrait"

    print(f"[ImageCropper] 📐 이미지 크기: {width}x{height}px")
    print(f"[ImageCropper] 📍 감지된 방향: {orientation}")
    print(f"[ImageCropper] ✂️ 자르기 비율: {ratio * 100:.1f}%")

    if orientation == "landscape":
        # 가로 방향: 좌측 자르기
        pixels_to_cut = int(width * ratio)
        pixels_to_cut = min(pixels_to_cut, int(width * 0.5))  # 최대 50% 제한

        print(f"[ImageCropper] 🔪 가로 모드 - 좌측 {pixels_to_cut}px ({ratio * 100:.1f}%) 제거")
        cropped_img = img.crop((pixels_to_cut, 0, width, height))

    else:
        # 세로 방향: 상단 자르기
        pixels_to_cut = int(height * ratio)
        pixels_to_cut = min(pixels_to_cut, int(height * 0.5))  # 최대 50% 제한

        print(f"[ImageCropper] 🔪 세로 모드 - 상단 {pixels_to_cut}px ({ratio * 100:.1f}%) 제거")
        cropped_img = img.crop((0, pixels_to_cut, width, height))

    # 결과 크기 출력
    new_width, new_height = cropped_img.size
    print(f"[ImageCropper] ✅ 결과 크기: {new_width}x{new_height}px")

    # RGBA → RGB 변환 (PNG는 RGBA, JPEG는 RGB만 지원)
    if cropped_img.mode in ('RGBA', 'LA', 'P'):
        rgb_img = Image.new('RGB', cropped_img.size, (255, 255, 255))
        rgb_img.paste(cropped_img, mask=cropped_img.split()[-1] if cropped_img.mode == 'RGBA' else None)
        cropped_img = rgb_img

    # JPEG로 저장
    output = BytesIO()
    cropped_img.save(output, format="JPEG", quality=95)
    return output.getvalue()


# 사용 예시
if __name__ == "__main__":
    # 테스트 코드
    with open("test_image.jpg", "rb") as f:
        image_bytes = f.read()
    
    # 자동 감지 (기본)
    result = crop_top_section(image_bytes, cm_to_cut=5.0)
    
    with open("cropped_output.jpg", "wb") as f:
        f.write(result)
    
    print("✅ 크롭 완료!")
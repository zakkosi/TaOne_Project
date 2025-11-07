# backend/utils/image_cropper.py
from PIL import Image
from io import BytesIO

def crop_top_section(image_bytes: bytes, cm_to_cut: float = 5.0, orientation: str = "auto") -> bytes:
    """
    이미지 상단(세로) 또는 좌측(가로)을 A4 기준 약 cm_to_cut cm 만큼 잘라냄.
    
    Args:
        image_bytes: 원본 이미지 (bytes)
        cm_to_cut: 잘라낼 길이 (cm, 기본값 5.0cm - 도안명/이름 텍스트 영역)
        orientation: "auto" (자동감지), "portrait" (세로-상단자르기), "landscape" (가로-좌측자르기)
    
    Returns:
        bytes: 잘린 이미지 (JPEG)
    """
    img = Image.open(BytesIO(image_bytes))
    
    # DPI 정보 가져오기 (기본 300dpi)
    dpi = img.info.get("dpi", (300, 300))
    dpi_horizontal = dpi[0] if isinstance(dpi, tuple) else dpi
    dpi_vertical = dpi[1] if isinstance(dpi, tuple) else dpi
    
    width, height = img.size
    
    # 📌 방향 자동 감지
    if orientation == "auto":
        is_landscape = width > height  # 가로가 더 길면 가로 방향
        orientation = "landscape" if is_landscape else "portrait"
    
    print(f"[ImageCropper] 이미지 크기: {width}x{height}px")
    print(f"[ImageCropper] 감지된 방향: {orientation}")
    print(f"[ImageCropper] DPI: {dpi_horizontal} x {dpi_vertical}")
    
    if orientation == "landscape":
        # 가로 방향: 좌측 자르기
        pixels_to_cut = int((cm_to_cut / 2.54) * dpi_horizontal)  # cm → inch → pixels
        pixels_to_cut = min(pixels_to_cut, int(width * 0.5))  # 최대 50% 제한
        
        print(f"[ImageCropper] 가로 모드 - 좌측 {pixels_to_cut}px ({cm_to_cut}cm) 제거")
        cropped_img = img.crop((pixels_to_cut, 0, width, height))
        
    else:
        # 세로 방향: 상단 자르기
        pixels_to_cut = int((cm_to_cut / 2.54) * dpi_vertical)  # cm → inch → pixels
        pixels_to_cut = min(pixels_to_cut, int(height * 0.5))  # 최대 50% 제한
        
        print(f"[ImageCropper] 세로 모드 - 상단 {pixels_to_cut}px ({cm_to_cut}cm) 제거")
        cropped_img = img.crop((0, pixels_to_cut, width, height))
    
    # 결과 크기 출력
    new_width, new_height = cropped_img.size
    print(f"[ImageCropper] 결과 크기: {new_width}x{new_height}px")
    
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
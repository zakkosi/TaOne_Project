# backend/utils/image_cropper.py
from PIL import Image
from io import BytesIO

def crop_top_section(image_bytes: bytes, cm_to_cut: float = 3.0) -> bytes:
    """
    이미지 상단을 A4 기준 약 cm_to_cut cm 만큼 잘라냄.
    Args:
        image_bytes: 원본 이미지 (bytes)
        cm_to_cut: 잘라낼 세로 길이 (cm)
    Returns:
        bytes: 잘린 이미지 (JPEG)
    """
    img = Image.open(BytesIO(image_bytes))
    dpi = img.info.get("dpi", (300, 300))[1]  # 기본 300dpi 가정
    pixels_to_cut = int((cm_to_cut / 2.54) * dpi)  # cm → inch → pixels

    width, height = img.size
    cropped_img = img.crop((0, pixels_to_cut, width, height))

    output = BytesIO()
    cropped_img.save(output, format="JPEG", quality=95)
    return output.getvalue()

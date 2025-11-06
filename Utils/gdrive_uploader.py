# backend/utils/gdrive_uploader.py
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from io import BytesIO

def upload_to_gdrive(image_bytes: bytes, filename: str = "cropped_image.jpg") -> str:
    """
    Google Drive에 이미지 업로드 후 shareable URL 반환.
    """
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()  # 처음 1회 인증 필요
    drive = GoogleDrive(gauth)

    file = drive.CreateFile({'title': filename})
    file.SetContentString(image_bytes.decode('latin1'))  # 바이너리 변환
    file.Upload()

    # 파일 공유 설정
    file.InsertPermission({
        'type': 'anyone',
        'value': 'anyone',
        'role': 'reader'
    })

    return f"https://drive.google.com/uc?id={file['id']}"

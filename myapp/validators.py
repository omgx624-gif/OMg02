"""validators ใช้ร่วมกัน — ไฟล์อัปโหลด"""

from django.core.exceptions import ValidationError

# ขนาดไฟล์รูปสูงสุด (ตรงกับที่ฟอร์มเดิมเคยจำกัดไว้ 10MB)
MAX_IMAGE_MB = 10


def validate_image_file(value):
    """ตรวจไฟล์รูปภาพ: ขนาดไม่เกิน 10MB + เป็นรูปจริงที่ Pillow เปิดได้

    ใช้กับ ImageField ทุกจุด (โมเดล/ฟอร์ม/API) กันไฟล์ใหญ่เกินไป
    และไฟล์ปลอมที่แค่เปลี่ยนนามสกุลเป็น .png
    """
    max_bytes = MAX_IMAGE_MB * 1024 * 1024
    if value.size > max_bytes:
        raise ValidationError(
            f'ไฟล์รูปภาพต้องมีขนาดไม่เกิน {MAX_IMAGE_MB} MB '
            f'(ตอนนี้ {value.size // (1024 * 1024)} MB)'
        )

    content_type = getattr(value, 'content_type', '') or ''
    if content_type and not content_type.startswith('image/'):
        raise ValidationError('ไฟล์ต้องเป็นรูปภาพ (JPG/PNG/WebP/GIF)')

    try:
        from PIL import Image

        if hasattr(value, 'seek'):
            value.seek(0)
        with Image.open(value) as img:
            img.verify()
        if hasattr(value, 'seek'):
            value.seek(0)
    except Exception as exc:
        raise ValidationError(
            'ไฟล์รูปภาพเสียหายหรือไม่ใช่ไฟล์รูปที่ถูกต้อง'
        ) from exc

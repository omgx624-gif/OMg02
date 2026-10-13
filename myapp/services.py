"""บริการเสริมของระบบ: PromptPay QR + แจ้งเตือนผ่าน Line Notify / Email + Geocoding

- `promptpay_payload`: สร้าง payload มาตรฐาน EMVCo QR สำหรับ PromptPay (คำนวณ CRC16/XModem)
- `notify_line` / `notify_email`: ส่งการแจ้งเตือนไปยัง Line Notify หรืออีเมล
- `line_notify_status` / `mask_token`: ตรวจสอบ token Line Notify / ปิดบัง token หน้าเว็บ
- `geocode_address`: API ภายนอก (Nominatim/OpenStreetMap) เปลี่ยนที่อยู่ → พิกัด GPS สำหรับเดลิเวอร์รี่
- `announce_*`: แจ้งอีเวนต์สำคัญ (ออเดอร์ใหม่ / จองโต๊ะ / รีวิว) ตามการตั้งค่าร้าน
"""

import io
import time
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

from django.core.mail import send_mail

if TYPE_CHECKING:
    from .models import StoreLocation


# ----------------------------------------------------------------------
# PromptPay QR (EMVCo)
# ----------------------------------------------------------------------

def _tlv(tag: str, value: str) -> str:
    """สร้าง TLV (Tag-Length-Value) เป็นรูปแบบ QR PromptPay"""
    return f"{tag}{len(value):02d}{value}"


def crc16_xmodem(data: bytes) -> int:
    """CRC16/CCITT-XModem — ใช้ในส่วนตรวจสอบของ QR PromptPay"""
    crc = 0x0000
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def promptpay_payload(promptpay_id, amount):
    """สร้าง payload QR PromptPay จาก ID (เบอร์โทร/เลขประจําตัว) และยอดเงิน (บาท)

    ตัวอย่าง: ถ้า promptpay_id เป็นเบอร์โทร => ใช้ "0066" + เลข 9 หลัก
    ถ้าเป็นเลขประจำตัวประชาชน 13 หลัก => ใช้เลขตรงๆ
    คืนค่าเป็น string (ให้เอาไปวาด QR ได้) หรือ None ถ้าข้อมูลไม่พร้อม
    """
    if not promptpay_id:
        return None
    try:
        amount = Decimal(str(amount)).quantize(Decimal('0.01'))
    except (InvalidOperation, ValueError):
        return None
    if amount <= 0:
        return None

    digits = ''.join(ch for ch in str(promptpay_id) if ch.isdigit())

    # เบอร์โทรไทย: ขึ้นต้น 0 และมี 10 หลัก → แปลงเป็น "0066" + 9 หลัก
    if len(digits) == 10 and digits.startswith('0'):
        merchant = '00' + '66' + digits[1:]
        account_info = _tlv('01', merchant)
    else:
        account_info = _tlv('02', digits)

    payload = '000201010212'  # รูปแบบ EMVCo + dynamic QR
    payload += _tlv('29', account_info)
    payload += '5303' + '764'  # สกุลเงินบาท (THB)
    payload += '5802' + 'TH'
    amt = f'{amount:.2f}'
    payload += _tlv('54', amt)
    payload += '6304'

    crc = crc16_xmodem(payload.encode('ascii'))
    return payload + f'{crc:04X}'.upper()


def render_qrcode_base64(payload):
    """วาด QR เป็นรูป PNG แล้วคืนเป็น data URI (ใช้กับ <img>)"""
    import base64

    import qrcode

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=3,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode('ascii')


# ----------------------------------------------------------------------
# คูปอง — ตรรกะตรวจสิทธิ์ใช้ร่วมกัน (หน้าเว็บ + API)
# ----------------------------------------------------------------------

def order_coupon_status(order):
    """สถานะว่าออเดอร์นี้เปิดให้ใช้คูปองได้หรือไม่ (คืนคูปองที่ใช้ไปแล้วด้วย)

    คืน `(can_apply: bool, used_coupon: Coupon | None)`
    """
    from .models import Coupon

    if order.status in ('paid', 'cancelled', 'refunded', 'completed'):
        return False, None
    if order.coupon_code:
        coupon = Coupon.objects.filter(code=order.coupon_code).first()
        return False, coupon
    return True, None


def validate_coupon(code, order_price, user, *, owned_only=False):
    """ตรวจสิทธิ์คูปองจุดเดียว — ใช้ทั้งหน้าเว็บ order_apply_coupon และ API

    คืน `(coupon, discount, error)` โดย `error` เป็น `None` เมื่อผ่านทุกเงื่อนไข
    ไม่งั้นเป็น tuple `(error_code, message)`:
      - `empty`       ไม่ได้กรอกรหัส
      - `not_found`   ไม่พบรหัส/ปิดใช้งาน (หรือใน owned_only คือของคนอื่น → ไม่บอกว่ามี)
      - `owner`       คูปองเป็นของสมาชิกท่านอื่น
      - `invalid`     หมดอายุ/ครบจำนวนครั้ง/ยอดไม่ถึงขั้นต่ำ
      - `no_discount` คำนวณส่วนลดได้ 0

    `owned_only=True` มองเฉพาะคูปองสาธารณะ/ของตัวเอง (ใช้ตอน "ตรวจสอบคูปอง"
    ที่ยังไม่ผูกกับออเดอร์) — Staff มองได้ทุกคูปองเหมือนเดิม
    """
    from decimal import Decimal

    from django.db.models import Q

    from .models import Coupon

    code = (code or '').strip()
    if not code:
        return None, None, ('empty', 'กรุณากรอกรหัสคูปอง')

    qs = Coupon.objects.filter(code__iexact=code, is_active=True)
    if owned_only and not getattr(user, 'is_staff', False):
        qs = qs.filter(Q(owner__isnull=True) | Q(owner=user))
    coupon = qs.first()
    if coupon is None:
        return None, None, ('not_found', 'ไม่พบรหัสคูปองนี้ในระบบ หรือคูปองถูกปิดใช้งาน')

    if coupon.owner_id is not None and not (
        coupon.owner_id == getattr(user, 'id', None) or getattr(user, 'is_staff', False)
    ):
        return None, None, ('owner', 'คูปองนี้เป็นของสมาชิกท่านอื่น ไม่สามารถใช้ได้')

    if not coupon.is_valid(order_price=order_price):
        return None, None, (
            'invalid',
            f'คูปองนี้ใช้ไม่ได้ (หมดอายุ/ครบจำนวนครั้ง/ยอดไม่ถึงขั้นต่ำ {coupon.min_order:.0f} บาท)',
        )

    discount = coupon.discount_for(order_price)
    if discount <= Decimal('0'):
        return None, None, ('no_discount', 'คูปองนี้ไม่ให้ส่วนลดในยอดนี้ กรุณาตรวจสอบอีกครั้ง')
    return coupon, discount, None


# ----------------------------------------------------------------------
# การแจ้งเตือน Line Notify
# ----------------------------------------------------------------------

def notify_line(token, message):
    """ส่งข้อความไปยัง Line Notify (คืน True เมื่อสำเร็จ / False เมื่อล้มเหลวหรือปิด)

    - หมดเวลาครั้งละ 8 วินาที และลองใหม่ (retry) รวมทั้งหมด 3 ครั้ง
    - Error ชัดเจนที่ไม่ใช่ความผิดชั่วคราว (เช่น token ผิด 400) ให้ผลลัพธ์ทันที ไม่เสียเวลาลองซ้ำ
    - อาการที่ควรลองใหม่: HTTP 429 / 500 / 502 / 503 / 504 หรือเน็ตหลุด (RequestException)
    """
    import requests

    if not token:
        return False
    for attempt in range(3):
        try:
            resp = requests.post(
                'https://notify-api.line.me/api/notify',
                headers={'Authorization': f'Bearer {token}'},
                data={'message': message},
                timeout=8,
            )
            if resp.status_code in (200, 201, 202):
                return True
            if resp.status_code not in (429, 500, 502, 503, 504):
                return False
        except requests.RequestException:
            pass  # เน็ตหลุด/หมดเวลา → ลองใหม่รอบถัดไป
        if attempt < 2:
            # กันยิงถี่เกินไปเมื่อเจอ Rate limit หรือ API ขัดข้องชั่วคราว
            time.sleep(1)
    return False


def line_notify_status(token):
    """ตรวจสอบว่า Line Notify token ยังใช้ได้หรือไม่ (LINE /api/status)
    คืน True เมื่อ token ถูกต้อง / False เมื่อปิด ว่าง หรือเชื่อมต่อไม่ได้
    """
    import requests

    if not token:
        return False
    try:
        resp = requests.get(
            'https://notify-api.line.me/api/status',
            headers={'Authorization': f'Bearer {token}'},
            timeout=8,
        )
        return resp.status_code == 200
    except requests.RequestException:
        return False


def mask_token(token):
    """ปิดบัง token ก่อนแสดงบนหน้าเว็บ เช่น `••••••••wxyz` (โชว์ท้ายสุด 4 ตัว)
    ถ้าสั้นมากก็ซ่อนทั้งหมด → กันคนอื่นก๊อปปี้ token เต็มจากหน้าจอ
    """
    if not token:
        return ''
    token = str(token).strip()
    if len(token) <= 8:
        return '•' * 8
    return '•' * 8 + token[-4:]


# ----------------------------------------------------------------------
# การแจ้งเตือน Email
# ----------------------------------------------------------------------

def notify_email(to_emails, subject, message):
    """ส่งอีเมล (ยอมรับ list/str) — พร้อม fallback ถ้ายังไม่ตั้งค่า SMTP ก็ไม่พัง"""
    if not to_emails:
        return False
    if isinstance(to_emails, str):
        to_emails = [to_emails]
    to_emails = [e for e in to_emails if e]
    if not to_emails:
        return False
    try:
        send_mail(
            subject,
            message,
            None,  # ใช้ DEFAULT_FROM_EMAIL
            to_emails,
            fail_silently=True,
        )
        return True
    except Exception:
        return False


# ----------------------------------------------------------------------
# ประกาศอีเวนต์สำคัญ (ตามการตั้งค่าร้าน)
# ----------------------------------------------------------------------

def _store() -> 'StoreLocation':
    from .models import StoreLocation
    return StoreLocation.get_setting()


def _line_token():
    """Token Line Notify ที่ใช้จริง: เอา token ใน DB ก่อน (ตั้งทาง Admin)
    ถ้ายังไม่ตั้ง ก็ fallback ไปใช้ตัวแปรสภาพแวดล้อม LINE_NOTIFY_TOKEN (settings.py)
    """
    from django.conf import settings

    store = _store()
    return (store.line_notify_token or '').strip() or getattr(settings, 'LINE_NOTIFY_TOKEN', '') or ''


def announce_new_order(order):
    """แจ้งออเดอร์ใหม่ (Line + Email) ตามการตั้งค่าร้าน"""
    store = _store()
    if not store.notify_order:
        return
    link_line = (
        f"🛎️ ออเดอร์ใหม่: {order.display_code} {order.table_display}\n"
        f"สถานะ: {order.get_status_display()}\nยอด: {order.discounted_total:,.2f} บาท"
    )
    notify_line(_line_token(), link_line)
    notify_email(store.notification_email, f'ออเดอร์ใหม่ {order.display_code}', link_line)


def announce_new_reservation(reservation):
    """แจ้งการจองโต๊ะใหม่"""
    store = _store()
    if not store.notify_reservation:
        return
    msg = (
        f"📅 จองโต๊ะใหม่: {reservation.customer_name}\n"
        f"{reservation.party_size} คน @ {reservation.reservation_date:%d/%m/%Y} "
        f"{reservation.reservation_time:%H:%M}"
        + (f"\nโต๊ะ {reservation.table_number}" if reservation.table_number else '')
    )
    notify_line(_line_token(), msg)
    notify_email(store.notification_email, 'การจองโต๊ะใหม่', msg)


def announce_new_review(review):
    """แจ้งรีวิวใหม่"""
    store = _store()
    if not store.notify_review:
        return
    msg = (
        f"⭐ รีวิวใหม่: {review.menu.name} ★{review.rating}\n"
        f'"{review.comment}" — โดย {review.user.username}'
    )
    notify_line(_line_token(), msg)
    notify_email(store.notification_email, f'รีวิวใหม่ {review.menu.name}', msg)


# ----------------------------------------------------------------------
# API ภายนอก: Geocoding (ที่อยู่ → พิกัด GPS) ผ่าน Nominatim / OpenStreetMap
# ----------------------------------------------------------------------
# บริการนี้ฟรี ไม่ต้องใช้ API Key แต่มีเงื่อนไขการใช้งาน:
# 1. ต้องส่ง User-Agent ระบุตัวตนทุกครั้ง ตามนโยบายของ OSM
# 2. ห้ามยิงถี่เกิน 1 คำขอ/วินาที (ระบบนี้ใช้เฉพาะเมื่อกดปุ่ม "ค้นหาพิกัด")
# อ้างอิง: https://operations.osmfoundation.org/policies/nominatim/

GEOCODE_URL = 'https://nominatim.openstreetmap.org/search'
GEOCODE_USER_AGENT = 'aroyker-baen-restaurant/1.0 (educational project; no rate abuse)'


def geocode_address(address, country_codes='th'):
    """ค้นหาพิกัด GPS จากที่อยู่ (ข้อความ) ผ่าน API Nominatim ของ OpenStreetMap

    - รับ address (str) → คืน `(lat: float, lng: float)` หรือ `None` ถ้าหาไม่เจอ/API ล่ม
    - `country_codes` จำกัดพื้นที่การค้น (ค่าเริ่มต้น 'th' = ไทย) ว่าง = ค้นทั้งโลก
    - จับ error ทั้งหมดแล้วคืน None เสมอ เพื่อไม่ให้การสั่งอาหารพังเพราะเน็ตติดขัด
    """
    import requests

    if not address or not str(address).strip():
        return None
    try:
        resp = requests.get(
            GEOCODE_URL,
            params={
                'q': str(address).strip(),
                'format': 'json',
                'limit': 1,
                'countrycodes': country_codes or '',
                'addressdetails': 0,
            },
            headers={'User-Agent': GEOCODE_USER_AGENT},
            timeout=8,
        )
        resp.raise_for_status()
        results = resp.json()
        if not results:
            return None
        return float(results[0]['lat']), float(results[0]['lon'])
    except (requests.RequestException, ValueError, KeyError, TypeError, IndexError):
        return None
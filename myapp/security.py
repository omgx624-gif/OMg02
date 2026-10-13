"""ระบบกันการถล่ม (Brute-force protection)

จำกัดจำนวนครั้งที่พยายามล็อกอิน/สมัคร/จองภายในช่วงเวลาหนึ่ง ต่อ IP และ/
หรือ ชื่อผู้ใช้ โดยใช้ Django cache (ไม่มี dependency เพิ่มเติม ถ้าไม่มี Redis
จะใช้ LocMemCache ที่ตั้งค่าไว้ใน settings)
"""

from functools import wraps
from os import environ
from time import time

from django.core.cache import cache

# เก็บ timestamp สูงสุดต่อ key (กัน memory บวมเมื่อถูกยิงรัวๆ ในช่วง window)
_MAX_TIMESTAMPS = 200


def _trust_proxy():
    """เชื่อ X-Forwarded-For เฉพาะเมื่อตั้ง DJANGO_TRUSTED_PROXY=1
    (รันหลัง reverse proxy ที่เขียนทับ header เอง — ถ้าไม่มี proxy
    ผู้ร้ายปลอม header นี้เพื่อหมุน IP หลบ rate limit ได้)"""
    return environ.get('DJANGO_TRUSTED_PROXY', '').lower() in ('1', 'true', 'yes', 'on')


def get_client_ip(request):
    """ดึง IP ของผู้ใช้

    ค่า X-Forwarded-For ถูกปลอมได้ง่าย จึงใช้เฉพาะเมื่อเปิด
    DJANGO_TRUSTED_PROXY=1 เท่านั้น — ปกติใช้ REMOTE_ADDR ตรงๆ
    """
    if _trust_proxy():
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            ip = xff.split(',')[0].strip()
            if ip:
                return ip
    return request.META.get('REMOTE_ADDR', '') or 'unknown'


def _keys(namespace, *parts):
    return [f'ratelimit:{namespace}:{p}' for p in parts]


def _increment(key, window):
    """เพิ่ม counter แบบ best-effort (get → กรอง → set)

    ไม่ atomic จริงภายใต้ concurrent request — สอง request ที่วิ่งพร้อมกัน
    อาจเขียนทับกันแล้วนับพลาดได้บ้าง แต่ยังเพียงพอสำหรับกัน brute-force
    และใช้ได้กับทุก cache backend (ไม่ต้องพึ่ง atomic incr)
    """
    now = time()
    value = cache.get(key)
    if value is None:
        cache.set(key, [now], timeout=window)
        return 1
    # กรองรายการที่เกินเวลาแล้ว
    recent = [t for t in value if now - t < window]
    recent.append(now)
    if len(recent) > _MAX_TIMESTAMPS:
        recent = recent[-_MAX_TIMESTAMPS:]
    cache.set(key, recent, timeout=window)
    return len(recent)


def _clear(key):
    cache.delete(key)


def _too_many(key, limit, window):
    value = cache.get(key) or []
    active = [t for t in value if time() - t < window]
    if len(active) != len(value):
        cache.set(key, active, timeout=window)
    return len(active) >= limit


def record_failed_login(request, username=''):
    """บันทึกความพยายามล็อกอินที่ล้มเหลว (นับต่อ IP + ต่อชื่อผู้ใช้)"""
    ip = get_client_ip(request)
    _increment(_keys('login-ip', ip)[0], window=900)
    if username:
        _increment(_keys('login-user', username)[0], window=900)


def too_many_login_attempts(request, username=''):
    """ล็อกอินถูกบล็อกชั่วคราวหรือยัง (IP มากกว่า 10 ครั้ง/15 นาที
    หรือชื่อผู้ใช้เดียว มากกว่า 5 ครั้ง/15 นาที)"""
    ip = get_client_ip(request)
    if _too_many(_keys('login-ip', ip)[0], limit=10, window=900):
        return True
    if username and _too_many(_keys('login-user', username)[0], limit=5, window=900):
        return True
    return False


def clear_login_attempts(request, username=''):
    """รีเซ็ต counter เมื่อล็อกอินสำเร็จ"""
    ip = get_client_ip(request)
    _clear(_keys('login-ip', ip)[0])
    if username:
        _clear(_keys('login-user', username)[0])


def rate_limit(namespace, limit, window, key_parts=(lambda r: ()), message='กรุณารอสักครู่แล้วลองใหม่'):
    """Decorator จำกัดความถี่จาก function ที่รับ request เป็นตัวแรก
    ใช้งาน: @rate_limit('reservation', 5, 3600, key_parts=lambda r: (get_client_ip(r),))
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            from django.contrib import messages
            from django.shortcuts import redirect, reverse
            from django.utils.http import url_has_allowed_host_and_scheme
            parts = tuple(str(p) for p in key_parts(request))
            key = _keys(namespace, *parts)[0]
            # นับเฉพาะ POST (การส่งข้อมูลจริง) ไม่นับการโหลดหน้า
            if request.method == 'POST':
                if _too_many(key, limit, window):
                    messages.error(request, message)
                    # กลับหน้าเดิมเฉพาะเมื่อเป็น URL ภายใน — กัน open redirect
                    referer = request.META.get('HTTP_REFERER', '')
                    if referer and url_has_allowed_host_and_scheme(
                        referer, allowed_hosts={request.get_host()}
                    ):
                        return redirect(referer)
                    return redirect(reverse('home'))
                _increment(key, window)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
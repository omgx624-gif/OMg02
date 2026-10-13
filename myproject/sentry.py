"""Sentry error tracking (optional) — เปิดใช้เมื่อกำหนด DJANGO_SENTRY_DSN เท่านั้น

ไม่ตั้ง DSN = ไม่โหลดอะไรเลย จึงไม่กระทบงานพัฒนา/เทสต์
เรียกจาก myproject/settings.py ตอนท้าย (ครอบคลุม runserver/gunicorn/test)
"""

import os


def init_sentry():
    """เริ่ม Sentry SDK ถ้ามี DSN — คืน True เมื่อ init แล้ว, False เมื่อข้าม

    ค่าที่ปรับได้ผ่าน environment:
    - DJANGO_SENTRY_DSN         : DSN ของโปรเจกต์บน Sentry (บังคับถ้าจะใช้)
    - DJANGO_SENTRY_TRACES_RATE : สัดส่วนเก็บ performance trace (0.0 = ปิด, ค่าเริ่มต้น 0.0)
    - DJANGO_SENTRY_ENVIRONMENT : เช่น production/staging (ค่าเริ่มต้น = ไม่ระบุ)
    """
    dsn = (os.environ.get('DJANGO_SENTRY_DSN') or '').strip()
    if not dsn:
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
    except ImportError:
        import sys
        sys.stderr.write(
            'WARNING: ตั้ง DJANGO_SENTRY_DSN แต่ยังไม่ได้ติดตั้ง sentry-sdk '
            '(pip install sentry-sdk) — ข้ามการส่ง error ไป Sentry\n'
        )
        return False

    sentry_sdk.init(
        dsn=dsn,
        integrations=[DjangoIntegration()],
        traces_sample_rate=float(os.environ.get('DJANGO_SENTRY_TRACES_RATE') or '0.0'),
        environment=(os.environ.get('DJANGO_SENTRY_ENVIRONMENT') or '').strip() or None,
        # ไม่ส่งข้อมูลส่วนตัว (ชื่อ/อีเมล/cookie) ของผู้ใช้ไป Sentry
        send_default_pii=False,
    )
    return True

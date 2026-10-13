"""เลือก backend ฐานข้อมูลจาก environment

- ค่าเริ่มต้น (และตอน develop): SQLite — ไม่ต้องติดตั้งอะไรเพิ่ม
- Production แนะนำ PostgreSQL: ตั้ง DJANGO_DB_ENGINE=postgresql แล้วกรอก
  DJANGO_POSTGRES_* (ดู .env.example) — เหมาะกับ gunicorn หลาย worker
  และการใช้ SELECT ... FOR UPDATE ล็อกแถวจริง (กันตัดสต็อกซ้ำ)
- รองรับ Render: ถ้ามี DATABASE_URL (เช่น postgres://user:pass@host/db) จะใช้ค่านั้น
  อัตโนมัติ แม้ไม่ได้ตั้ง DJANGO_POSTGRES_* เอง
"""

import os
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured

_SQLITE = 'sqlite3'
_POSTGRES_ENGINES = {'postgres', 'postgresql', 'pgsql', 'pg'}
_POSTGRES_SCHEMES = _POSTGRES_ENGINES | {'postgres+psycopg', 'postgresql+psycopg'}
_KNOWN_ENGINES = {_SQLITE} | _POSTGRES_ENGINES


def _postgres_from_url(url, env):
    parsed = urlparse(url)
    if parsed.scheme.lower() not in _POSTGRES_SCHEMES:
        raise ImproperlyConfigured(
            f"DATABASE_URL scheme ไม่รองรับ: {parsed.scheme!r} "
            f"(ต้องเป็น postgres/postgresql)"
        )

    host = parsed.hostname or '127.0.0.1'
    port = str(parsed.port) if parsed.port else '5432'
    name = (parsed.path or '').lstrip('/') or 'postgres'
    user = unquote(parsed.username) if parsed.username else ''
    password = unquote(parsed.password) if parsed.password is not None else ''

    conn_max_age = int(env.get('DJANGO_POSTGRES_CONN_MAX_AGE') or '60')

    config = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': name,
        'USER': user,
        'PASSWORD': password,
        'HOST': host,
        'PORT': port,
        'CONN_MAX_AGE': conn_max_age,
        'CONN_HEALTH_CHECKS': True,
    }

    # sslmode — ใช้จาก query string ถ้ามี ไม่งั้นบังคับ require สำหรับ remote host
    query = parse_qs(parsed.query)
    sslmode = (query.get('sslmode') or [None])[0]
    if not sslmode and host not in ('localhost', '127.0.0.1', ''):
        sslmode = 'require'
    if sslmode:
        config['OPTIONS'] = {'sslmode': sslmode}

    return config


def build_database(environ=None, base_dir=None):
    """คืนค่า dict สำหรับ DATABASES['default'] ตาม environment ที่กำหนด

    environ: mapping ของตัวแปรสภาพแวดล้อม (ค่าเริ่มต้น = os.environ)
    base_dir: โฟลเดอร์โปรเจกต์ สำหรับหา db.sqlite3 (ค่าเริ่มต้น = โฟลเดอร์ myproject/)
    """
    env = os.environ if environ is None else environ
    base = Path(base_dir) if base_dir is not None else Path(__file__).resolve().parent.parent

    database_url = (env.get('DATABASE_URL') or '').strip()
    engine = (env.get('DJANGO_DB_ENGINE') or '').strip().lower()

    # เลือกจาก DATABASE_URL ถ้ามี และไม่ได้บังคับเป็น sqlite ชัดเจน
    if database_url and engine not in _KNOWN_ENGINES and engine != _SQLITE:
        # engine ว่าง หรือค่าอื่นที่ไม่รู้จัก → ลองแปลง scheme
        try:
            return _postgres_from_url(database_url, env)
        except ImproperlyConfigured:
            # ถ้า scheme ไม่ใช่ postgres ให้ fall through ไป logic ปกติ
            pass

    if engine and engine not in _KNOWN_ENGINES:
        raise ImproperlyConfigured(
            f"DJANGO_DB_ENGINE ไม่ถูกต้อง: {engine!r} "
            f"(ต้องเป็นหนึ่งใน: {', '.join(sorted(_KNOWN_ENGINES))})"
        )

    if engine == _SQLITE and not database_url:
        # SQLite แบบเดิม
        pass

    if engine in _POSTGRES_ENGINES:
        # ถ้ามี DATABASE_URL ให้ใช้ค่านั้น (Render) แทนการกรอก DJANGO_POSTGRES_* เอง
        if database_url:
            return _postgres_from_url(database_url, env)
        return {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env.get('DJANGO_POSTGRES_DB') or 'restaurant',
            'USER': env.get('DJANGO_POSTGRES_USER') or 'restaurant',
            'PASSWORD': env.get('DJANGO_POSTGRES_PASSWORD') or '',
            'HOST': env.get('DJANGO_POSTGRES_HOST') or '127.0.0.1',
            'PORT': env.get('DJANGO_POSTGRES_PORT') or '5432',
            # reuse connection ระหว่าง request (ค่าเริ่มต้น 60 วินาที)
            'CONN_MAX_AGE': int(env.get('DJANGO_POSTGRES_CONN_MAX_AGE') or '60'),
            'CONN_HEALTH_CHECKS': True,
        }

    # default: ถ้ามี DATABASE_URL ที่เป็น postgres ให้ใช้ (แม้ DJANGO_DB_ENGINE ว่าง)
    if database_url:
        try:
            return _postgres_from_url(database_url, env)
        except ImproperlyConfigured:
            pass

    return {
        'ENGINE': 'django.db.backends.sqlite3',
        # Docker ตั้ง DJANGO_SQLITE_PATH ให้ชี้ไปยัง volume ที่ mount ไว้ (เช่น /data/db.sqlite3)
        # เพื่อไม่ให้ named volume ที่ mount ที่ /app กลบทับไฟล์โค้ดใน image
        'NAME': env.get('DJANGO_SQLITE_PATH') or (base / 'db.sqlite3'),
    }

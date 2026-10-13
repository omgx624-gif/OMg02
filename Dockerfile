FROM python:3.14-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Runtime ---
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY . .

# collectstatic ด้วย config แบบ production (DEBUG=false) เพื่อให้ WhiteNoise ถูกใช้จริง
RUN DJANGO_DEBUG=false DJANGO_SECRET_KEY=build-time-only-key \
    python manage.py collectstatic --noinput

# /data ใช้สำหรับ mount volume ของ SQLite (DJANGO_SQLITE_PATH=/data/db.sqlite3)
RUN mkdir -p /app/media /data \
    && chown -R appuser:appuser /app /data

# Render inject PORT (ค่าเริ่มต้น 10000) — ใช้ค่านี้เป็น port ของ gunicorn
ENV PORT=8000

USER appuser

EXPOSE 8000

# healthcheck ผ่าน /healthz (ตรวจ DB จริง) — ยกเว้น HTTPS redirect ด้วย
# SECURE_REDIRECT_EXEMPT จึงใช้ HTTP ตรงๆ ได้แม้เปิด DJANGO_SECURE=1
# ถ้าตอบ 503 (DB ใช้ไม่ได้) urlopen จะ raise → container = unhealthy
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4)"

CMD ["sh", "-c", "exec gunicorn myproject.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3 --timeout 120"]

@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo กำลังเริ่มต้นเซิร์ฟเวอร์ Django...
echo เข้าใช้งานได้ที่: http://127.0.0.1:8000/
echo (กด Ctrl+C เพื่อหยุดการทำงาน)
echo.
if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe manage.py runserver
) else (
    python manage.py runserver
)
pause

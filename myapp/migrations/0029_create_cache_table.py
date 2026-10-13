"""สร้างตารางสำหรับ DatabaseCache (ใช้เมื่อ cache backend เป็น db)

ความสำคัญ: เมื่อ DEBUG=False ค่าเริ่มต้นของ CACHES คือ DatabaseCache —
ถ้าไม่มีตาราง rate limit จะพังทันที คำสั่ง createcachetable เป็น idempotent
(ข้ามถ้าตารางมีอยู่แล้ว / ข้ามถ้าตั้ง backend เป็น Redis หรืออื่น ๆ)
"""

from django.conf import settings
from django.db import migrations


def create_cache_table(apps, schema_editor):
    backend = settings.CACHES.get('default', {}).get('BACKEND', '')
    if 'django.core.cache.backends.db.' not in backend:
        return
    from django.core.management import call_command

    call_command('createcachetable', verbosity=0)


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0028_add_phone_to_storelocation'),
    ]

    operations = [
        migrations.RunPython(create_cache_table, migrations.RunPython.noop),
    ]

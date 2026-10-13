from django.core.management.base import BaseCommand

from myapp.delivery_auto import maybe_auto_dispatch


class Command(BaseCommand):
    help = (
        'เรียกใช้ระบบจัดสรรงานเดลิเวอร์รี่อัตโนมัติ '
        '(จัดสรรงานให้ไรเดอร์ + ปล่อยงานค้าง) — แนะนำตั้งให้รันทุก 1 นาที'
    )

    def handle(self, *args, **options):
        maybe_auto_dispatch()
        self.stdout.write(self.style.SUCCESS('จัดสรรงานเดลิเวอร์รี่อัตโนมัติเรียบร้อย'))
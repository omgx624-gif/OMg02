from django.core.management.base import BaseCommand

from myapp.automation import run_all


class Command(BaseCommand):
    help = (
        'เรียกใช้ระบบอัตโนมัติทั้งหมด (Full Autopilot): เดินสถานะออเดอร์/จัดส่ง, '
        'จัดสรรไรเดอร์, สะสมคะแนนสมาชิก, สร้างรายงานและแจ้งเตือน — '
        'แนะนำตั้งให้รันทุก 1 นาที'
    )

    def handle(self, *args, **options):
        # force=True — cron/CLI ต้องรันเสมอ ไม่ถูกจำกัดความถี่ของ AUTOMATION_MIN_INTERVAL
        result = run_all(force=True)
        self.stdout.write(
            self.style.SUCCESS(
                f'ระบบอัตโนมัติเรียบร้อย — สถานะออเดอร์ {result["order"]} รายการ, '
                f'การจัดส่ง {result["delivery"]} รายการ'
            )
        )

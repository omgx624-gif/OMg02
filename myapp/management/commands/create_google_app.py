from allauth.socialaccount.models import SocialApp
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        'สร้าง/อัปเดต Google OAuth app สำหรับระบบล็อกอินด้วยบัญชี Google '
        '(จากตัวแปรสภาพแวดล้อม GOOGLE_OAUTH_CLIENT_ID / GOOGLE_OAUTH_CLIENT_SECRET)'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--client-id',
            default=settings.GOOGLE_OAUTH_CLIENT_ID,
            help='Google OAuth 2.0 Client ID',
        )
        parser.add_argument(
            '--client-secret',
            default=settings.GOOGLE_OAUTH_CLIENT_SECRET,
            help='Google OAuth 2.0 Client Secret',
        )
        parser.add_argument(
            '--domain',
            default='localhost',
            help='โดเมนของเว็บไซต์ (Site framework) เช่น example.com, localhost',
        )

    def handle(self, *args, **options):
        client_id = options['client_id'].strip()
        client_secret = options['client_secret'].strip()
        if not client_id or not client_secret:
            self.stdout.write(
                self.style.WARNING(
                    'ข้ามการตั้งค่า Google OAuth: ไม่พบ GOOGLE_OAUTH_CLIENT_ID / '
                    'GOOGLE_OAUTH_CLIENT_SECRET (กำหนดเพื่อเปิดปุ่มและล็อกอินด้วย Google จริง)'
                )
            )
            return

        domain = options['domain'].strip()
        site, _ = Site.objects.get_or_create(
            id=settings.SITE_ID,
            defaults={'domain': domain, 'name': domain},
        )
        site.domain = domain
        site.name = options.get('name') or domain
        site.save()

        app, created = SocialApp.objects.update_or_create(
            provider='google',
            defaults={
                'name': 'Google',
                'client_id': client_id,
                'secret': client_secret,
            },
        )
        app.sites.add(site)

        self.stdout.write(
            self.style.SUCCESS(
                f'{"สร้าง" if created else "อัปเดต"} SocialApp "Google" สำเร็จ '
                f'(Client ID: ...{client_id[-8:]}) @ {domain}'
            )
        )
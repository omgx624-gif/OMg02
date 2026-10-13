from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from myapp.models import Profile


class Command(BaseCommand):
    help = 'สร้างหรืออัปเดตรหัสผ่านบัญชีผู้ใช้เริ่มต้นสำหรับทดสอบระบบ (admin, staff, customer)'

    def handle(self, *args, **options):
        User = get_user_model()
        staff_group, _ = Group.objects.get_or_create(name='Staff')

        accounts = [
            {
                'username': 'admin',
                'email': 'admin@restaurant.local',
                'password': 'Admin1234!',
                'is_staff': True,
                'is_superuser': True,
                'roles': ['Staff'],
            },
            {
                'username': 'staff',
                'email': 'staff@restaurant.local',
                'password': 'Staff1234!',
                'is_staff': True,
                'is_superuser': False,
                'roles': ['Staff'],
            },
            {
                'username': 'Jj12',
                'email': 'jj12@restaurant.local',
                'password': 'Staff1234!',
                'is_staff': True,
                'is_superuser': False,
                'roles': ['Staff'],
            },
            {
                'username': 'customer',
                'email': 'customer@restaurant.local',
                'password': 'User1234!',
                'is_staff': False,
                'is_superuser': False,
                'roles': [],
            },
            {
                'username': 'Ff12',
                'email': 'ff12@restaurant.local',
                'password': 'User1234!',
                'is_staff': False,
                'is_superuser': False,
                'roles': [],
            },
        ]

        for acc in accounts:
            user, created = User.objects.get_or_create(
                username=acc['username'],
                defaults={'email': acc['email']},
            )
            user.set_password(acc['password'])
            user.is_staff = acc['is_staff']
            user.is_superuser = acc['is_superuser']
            user.is_active = True
            user.save()

            if 'Staff' in acc['roles']:
                user.groups.add(staff_group)

            Profile.objects.get_or_create(user=user)

            action = 'สร้าง' if created else 'อัปเดตรหัสผ่าน'
            self.stdout.write(
                self.style.SUCCESS(
                    f'{action} บัญชี {acc["username"]} (รหัสผ่าน: {acc["password"]}) เรียบร้อย'
                )
            )

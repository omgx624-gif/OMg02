"""Google Sign-In adapter สำหรับ django-allauth

ทำให้การล็อกอิน/สมัครด้วย Google ทำงานแบบ "สมบูรณ์" กับระบบนี้:

1. ผู้ใช้ใหม่ที่เข้ามาผ่าน Google → เปิดให้สมัคร (autosignup) ได้เลย
   เพราะ Google ยืนยันอีเมลมาแล้ว จึงไม่ต้องรอผู้ดูแลอนุมัติเหมือนสมัครฟอร์ม
2. ถ้าอีเมลของ Google ตรงกับบัญชี username/รหัสผ่าน ที่มีอยู่แล้วในระบบ
   → ลิงก์บัญชี Google เข้ากับบัญชีเดิม (ไม่สร้างผู้ใช้ซ้ำซ้อน) แล้วเข้าสู่ระบบทันที
   และเปิดใช้งานบัญชีถ้าค้างรออนุมัติ (อีเมลผ่านการยืนยันของ Google แล้ว)
3. กรอกชื่อ/นามสกุล จากโปรไฟล์ Google ให้อัตโนมัติ
"""

from allauth.account.utils import perform_login
from allauth.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


class GoogleAccountAdapter(DefaultSocialAccountAdapter):
    """Custom adapter เพื่อให้ล็อกอินด้วย Google เชื่อมกับบัญชีเดิมได้อัตโนมัติ"""

    def is_open_for_signup(self, request, sociallogin):
        """เปิดรับสมัครสมาชิกผ่าน Google เสมอ (อีเมลได้รับการยืนยันแล้ว)"""
        return True

    def pre_social_login(self, request, sociallogin):
        """ก่อนเข้า flow ของ allauth — จัดการกรณีอีเมลชนกับบัญชีเดิม

        ถ้าผู้ใช้บอกว่ายังไม่มี SocialAccount ของ Google (login ครั้งแรก) แล้ว
        อีเมล Google ตรงกับบัญชี 'username + รหัสผ่าน' ที่สมัครไว้แล้ว → ลิงก์
        บัญชีเข้าด้วยกัน แล้วเข้าสู่ระบบทันที ไม่ต้องไปหน้าขั้นตอน "เชื่อมบัญชี"
        """
        # มี SocialAccount อยู่แล้ว → ปล่อยให้ allauth ทำตามปกติ
        if sociallogin.is_existing:
            return

        email = ''
        if sociallogin.email_addresses:
            email = sociallogin.email_addresses[0].email.lower()

        if not email:
            return

        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            # ยังไม่มีบัญชีนี้ในระบบ → auto-signup ตามปกติของ allauth
            return

        # อีเมลจาก Google ยืนยันตัวตนแล้ว ถ้าบัญชีเดิมเคยถูกรออนุมัติไว้ → เปิดใช้งาน
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=['is_active'])

        # ลิงก์ SocialAccount ของ Google เข้ากับบัญชีเดิม (ไม่สร้างผู้ใช้ใหม่)
        sociallogin.connect(request, user)

        # เข้าสู่ระบบทันที (Google ยืนยันตัวตนแล้ว ไม่ต้องป้อนรหัสผ่าน)
        response = perform_login(request, user, email_verification='none')
        raise ImmediateHttpResponse(response)

    def populate_user(self, request, sociallogin, data):
        """กรอกข้อมูลผู้ใช้จากโปรไฟล์ Google — กำหนดชื่อ/นามสกุลอย่างถูกต้อง"""
        user = super().populate_user(request, sociallogin, data)
        first_name = (data.get('first_name') or '').strip()
        last_name = (data.get('last_name') or '').strip()
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        return user

    def get_connect_redirect_url(self, request, socialaccount):
        """หลังเชื่อมบัญชี Google ในหน้าจัดการ (กรณีเข้า /accounts/.../connect/)
        กลับไปหน้าโปรไฟล์ของระบบแทนหน้า default ของ allauth"""
        return reverse('user_profile')
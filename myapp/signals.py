"""Signals — รวบรวมลอจิกที่ต้องทำงานอัตโนมัติเมื่อข้อมูลเปลี่ยน

1. สร้าง Profile ให้ทุก User ใหม่ (เพื่อให้ user.profile ใช้ได้เสมอ เช่น ดูคะแนน)
2. สะสมคะแนนสมาชิกให้โดยอัตโนมัติเมื่อออเดอร์กลายเป็น "ชำระแล้ว"
   ไม่ว่าจะชำระโดยพนักงานหรืออัตโนมัติ (ครอบคลุมทุกทางเข้า)
"""

from django.contrib.auth.models import User
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .automation import notify
from .models import AutomationSettings, Coupon, Order, PointTransaction, Profile


@receiver(post_save, sender=User)
def create_profile_for_new_user(sender, instance, created, **kwargs):
    """สร้าง Profile ให้ทุก User ใหม่ — ไม่ควรมีลิงหลุดที่ไม่มีโปรไฟล์"""
    if created:
        Profile.objects.get_or_create(user=instance)


@receiver(pre_save, sender=Order)
def stash_order_previous_state(sender, instance, **kwargs):
    """เก็บสถานะเดิมก่อนบันทึกไว้ใน instance (post_save อ่านจาก DB ไม่ได้ —
    เพราะ post_save ถูกเรียกหลังบันทึกแล้วจึงเห็นแต่สถานะใหม่เสมอ)"""
    if instance.pk:
        try:
            instance._previous_order = Order.objects.only(
                'status', 'paid_at'
            ).get(pk=instance.pk)
        except Order.DoesNotExist:
            instance._previous_order = None
    else:
        instance._previous_order = None


@receiver(post_save, sender=Order)
def reward_points_on_paid(sender, instance, created, **kwargs):
    """เมื่อออเดอร์ถูกปิดเป็น 'paid' — สะสมคะแนนสมาชิก + นับคูปอง + แจ้งเตือน
    ใช้ค่า status เดิมจาก pre_save เพื่อตรวจจับการเปลี่ยนจากสถานะอื่น → paid
    เท่านั้น (save ซ้ำของออเดอร์ที่ชำระแล้ว จะไม่นับซ้ำ)
    """
    if created:
        return
    if instance.status != 'paid':
        return

    prev = getattr(instance, '_previous_order', None)
    prev_status = prev.status if prev else None
    prev_paid_at = prev.paid_at if prev else None

    # เคยเป็น paid โดยมีเวลาชำระแล้ว = เป็นแค่ save ซ้ำ → ข้ามทั้งหมด
    if prev_status == 'paid' and prev_paid_at is not None:
        return

    # นับจำนวนครั้งที่ใช้คูปอง — เฉพาะตอนที่ออเดอร์เพิ่งกลายเป็น paid (ครั้งแรก)
    if instance.coupon_code:
        coupon = Coupon.objects.filter(code=instance.coupon_code).first()
        if coupon is not None:
            coupon.mark_used()

    cfg = AutomationSettings.get_setting()
    if not cfg.auto_earn_points:
        return

    profile = getattr(instance.created_by, 'profile', None)
    if profile is None:
        return

    # กันซ้ำอีกชั้น: เช็คว่ายังไม่เคยสะสมคะแนนสำหรับออเดอร์นี้ (จาก ledger)
    already_rewarded = PointTransaction.objects.filter(
        profile=profile, order=instance, points_change__gt=0
    ).exists()
    if already_rewarded:
        return

    amount = instance.discounted_total
    earned = profile.earn_points(
        amount,
        order=instance,
        reason=f'สะสมจากออเดอร์ {instance.display_code} (สถานะ {profile.get_membership_status_display()})',
    )
    if earned > 0:
        notify(
            'report', f'คะแนนสมาชิก {profile.user.username}',
            f'สะสมคะแนน +{earned} คะแนน จากออเดอร์ {instance.display_code} '
            f'(สถานะ {profile.get_membership_status_display()}, ส่วนลด {profile.discount_percent}%)',
            '/profile/',
            recipient=profile.user,
        )

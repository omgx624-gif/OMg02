"""ระบบเดลิเวอร์รี่อัตโนมัติ (Auto Dispatch)

- จัดสรรงานให้ไรเดอร์ที่ว่างที่สุด (least-loaded) เมื่องานค้างเกินเวลาเปิดรับ (grace)
- ปล่อยงานออกจากไรเดอร์ที่รับแล้วแต่ไม่คืบหน้าเกินเวลาสำรอง (release)
เรียกผ่าน manage.py autodelivery (แนะนำรันทุก 1 นาที)
หรือผ่านหน้าเว็บ (rider_dashboard / rider_my_jobs / delivery_dashboard)
"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.utils import timezone

from .models import Delivery, StoreLocation

# จำนวนงานสูงสุดที่ไรเดอร์ 1 คนถือได้พร้อมกัน
RIDER_MAX_ACTIVE_JOBS = 2
# จำนวนครั้งสูงสุดที่ระบบจะปล่อยงานออกจากไรเดอร์เดิม (กันวนซ้ำไม่มีที่สิ้นสุด)
MAX_AUTO_RELEASE = 2


def rider_active_count(rider):
    """จำนวนงานที่ไรเดอร์ยังถืออยู่ (ยังไม่ส่งสำเร็จ / ไม่ได้ยกเลิก)"""
    return (
        Delivery.objects.filter(assigned_rider=rider)
        .exclude(status__in=['delivered', 'cancelled'])
        .count()
    )


def pick_available_rider(exclude_rider_id=None):
    """เลือกไรเดอร์ที่ว่างที่สุด (มีงานค้างน้อยที่สุด และไม่เกินเกณฑ์)

    คำนวณจำนวนงานค้างของไรเดอร์ทุกคนใน query เดียว (group by)
    แทนการวนลูปเรียก count ทีละคน
    """
    from django.db.models import Count, IntegerField, OuterRef, Subquery

    # จำนวนงานค้างของไรเดอร์แต่ละคน (ยังไม่ส่งสำเร็จ / ไม่ได้ยกเลิก)
    active_counts = (
        Delivery.objects.filter(
            assigned_rider=OuterRef('pk'),
        )
        .exclude(status__in=['delivered', 'cancelled'])
        .order_by()
        .values('assigned_rider')
        .annotate(total=Count('pk'))
        .values('total')[:1]
    )

    riders = (
        User.objects.filter(profile__is_rider=True)
        .annotate(active_jobs=Subquery(active_counts, output_field=IntegerField()))
        .order_by('active_jobs', 'username')
    )

    for rider in riders:
        if exclude_rider_id and rider.pk == exclude_rider_id:
            continue
        if (rider.active_jobs or 0) < RIDER_MAX_ACTIVE_JOBS:
            return rider
    return None


def auto_assign_delivery(delivery):
    """มอบงานให้ไรเดอร์ที่ว่างที่สุด และเปลี่ยนสถานะเป็น 'accepted'

    คืนค่าไรเดอร์ที่ได้รับงาน หรือ None ถ้าไม่มีไรเดอร์ว่าง
    """
    if delivery.status != 'pending' or delivery.assigned_rider is not None:
        return None
    rider = pick_available_rider()
    if rider is None:
        return None
    delivery.assigned_rider = rider
    delivery.rider_name = rider.get_full_name() or rider.username
    delivery.status = 'accepted'
    delivery.accepted_at = timezone.now()
    delivery.save(
        update_fields=['assigned_rider', 'rider_name', 'status', 'accepted_at']
    )
    return rider


def release_stuck_accepted(delivery):
    """ปล่อยงานที่ไรเดอร์รับแล้วไม่คืบหน้าเกินเวลาสำรอง ออกเป็น pending ใหม่

    คืน True ถ้าปล่อยงานสำเร็จ
    """
    if delivery.status != 'accepted' or delivery.accepted_at is None:
        return False
    store = StoreLocation.get_setting()
    limit = store.auto_release_minutes or 0
    if limit <= 0:
        return False
    deadline = delivery.accepted_at + timedelta(minutes=limit)
    if timezone.now() < deadline:
        return False
    if delivery.release_count >= MAX_AUTO_RELEASE:
        return False
    delivery.release_count += 1
    delivery.assigned_rider = None
    delivery.rider_name = None
    delivery.status = 'pending'
    delivery.accepted_at = None
    delivery.picked_up_at = None
    delivery.delivered_at = None
    delivery.tracking_note = (
        f'ปล่อยงานอัตโนมัติ (ครั้งที่ {delivery.release_count}) - ไรเดอร์ไม่คืบหน้า'
    )
    delivery.save(
        update_fields=[
            'release_count',
            'assigned_rider',
            'rider_name',
            'status',
            'accepted_at',
            'picked_up_at',
            'delivered_at',
            'tracking_note',
        ]
    )
    return True


def maybe_auto_dispatch():
    """รันรอบจัดสรรงานอัตโนมัติ ทั้งหมดแบบ idempotent

    1) ปล่อยงานที่ไรเดอร์รับแล้วแต่ไม่คืบหน้า (เกิน auto_release_minutes)
    2) มอบงานที่รอรับเกิน grace period ให้ไรเดอร์ที่ว่างที่สุด (ถ้าเปิด auto_assign_enabled)
    """
    store = StoreLocation.get_setting()

    # 1) ปล่อยงานค้าง
    for delivery in Delivery.objects.filter(status='accepted'):
        release_stuck_accepted(delivery)

    # 2) จัดสรรงานที่ค้างเกินเวลารอรับ
    if store.auto_assign_enabled:
        grace_minutes = store.auto_assign_grace_minutes or 0
        due_jobs = Delivery.objects.filter(
            status='pending',
            assigned_rider__isnull=True,
        )
        for delivery in due_jobs:
            if grace_minutes > 0:
                deadline = delivery.created_at + timedelta(minutes=grace_minutes)
                if timezone.now() < deadline:
                    continue
            auto_assign_delivery(delivery)
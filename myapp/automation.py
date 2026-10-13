"""ระบบอัตโนมัติแบบรวมศูนย์ (Full Autopilot)

เดินสถานะออเดอร์ / สถานะจัดส่ง / จัดสรรไรเดอร์ / คำนวณรายงาน+คะแนนสมาชิก /
สร้างการแจ้งเตือน ให้ทำงานเองตามเวลาที่ตั้งไว้ โดยอ้างอิงเวลา baseline จาก:
- ออเดอร์: order.created_at
- จัดส่ง: สถานะเดิม (accepted_at / picked_up_at) ถ้ามี ไม่งั้นใช้ created_at

เรียกผ่าน `manage.py automate_all` (แนะนำรันทุก 1 นาที)
หรือผ่านรัน loop ใน view ที่มีหน้างาน (idempotent)
"""


from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from .delivery_auto import auto_assign_delivery, maybe_auto_dispatch
from .models import AutomationSettings, Delivery, Notification, Order

# สถานะที่ถือว่า "จบออเดอร์" — ห้ามเดินสถานะต่อ
FINAL_ORDER_STATUSES = ('paid', 'cancelled', 'refunded', 'completed')
# สถานะจัดส่งที่จบแล้ว
FINAL_DELIVERY_STATUSES = ('delivered', 'cancelled')


# ----------------------------------------------------------------------
# การแจ้งเตือน
# ----------------------------------------------------------------------

def notify(kind, title, message='', link='', recipient=None):
    """สร้างการแจ้งเตือน (ถ้ามีข้อความซ้ำล่าสุดประเภทเดียวกันจะไม่ซ้ำ)"""
    last = Notification.objects.filter(
        kind=kind, title=title, link=link, recipient=recipient
    ).order_by('-created_at').first()
    if last and last.message == message:
        return last
    return Notification.objects.create(
        kind=kind, title=title, message=message, link=link, recipient=recipient
    )


# ----------------------------------------------------------------------
# เดินสถานะออเดอร์ (ทานในร้าน + เดลิเวอร์รี่)
# ----------------------------------------------------------------------

def elapsed_minutes(ts):
    if ts is None:
        return 0
    return (timezone.now() - ts).total_seconds() / 60.0


def advance_order_status():
    """เดินสถานะออเดอร์ตามเวลา (เฉพาะออเดอร์ที่ยังไม่จบ)
    ใช้ time ต่อขั้นตอน (status_changed_at) เป็นหลัก — ทุกขั้นนับจากที่สถานะเปลี่ยน
    """
    cfg = AutomationSettings.get_setting()
    changed = 0
    for order in Order.objects.select_related('created_by', 'delivery').exclude(
        status__in=FINAL_ORDER_STATUSES
    ):
        if order.order_type == 'delivery':
            delivery = getattr(order, 'delivery', None)
            if delivery is None or delivery.status in FINAL_DELIVERY_STATUSES:
                continue
            # จัดส่งยังไม่เสร็จ — ปล่อยให้ advance_delivery_status จัดการ
            continue

        # ทานในร้าน — คำนวณตามเวลาที่ผ่านไปของขั้นปัจจุบัน
        base = order.status_changed_at or order.created_at
        t = elapsed_minutes(base)
        next_status = None

        if order.status == 'open' and t >= cfg.preparing_minutes:
            next_status = 'preparing'
        elif order.status == 'preparing' and t >= cfg.ready_minutes:
            next_status = 'ready'
        elif order.status == 'ready' and t >= cfg.served_minutes:
            next_status = 'served'
            if cfg.auto_pay and order.items.exists():
                next_status = 'paid'

        if next_status is None:
            continue

        order.status = next_status
        if next_status == 'paid':
            order.paid_at = timezone.now()
            order.payment_method = order.payment_method or 'cash'
        order.save()
        changed += 1
        notify(
            'order', order.display_code,
            f'ออเดอร์ {order.display_code} ({order.table_display}) → {order.get_status_display()}',
            f'/orders/{order.pk}/',
        )
    return changed


def advance_delivery_status():
    """เดินสถานะการจัดส่งตามเวลา (+ จัดสรรไรเดอร์ถ้ามี)
    ใช้ time ต่อขั้นตอน (status_changed_at) เป็นหลัก
    """
    cfg = AutomationSettings.get_setting()
    changed = 0

    for delivery in Delivery.objects.select_related('order', 'order__created_by').exclude(
        status__in=FINAL_DELIVERY_STATUSES
    ):
        # ยังไม่มีไรเดอร์ → ให้จัดสรรอัตโนมัติ
        if delivery.assigned_rider is None and delivery.status == 'pending':
            rider = auto_assign_delivery(delivery)
            if rider:
                changed += 1
                delivery.refresh_from_db()
                notify(
                    'rider', delivery.order.display_code,
                    f'มอบงาน {delivery.order.display_code} ให้ไรเดอร์ "{rider.get_full_name() or rider.username}" อัตโนมัติ',
                    '/delivery/rider/my-jobs/',
                    recipient=rider,
                )
            continue

        # มีไรเดอร์แล้ว — คำนวณตามเวลาที่ผ่านไปของขั้นปัจจุบัน
        base = delivery.status_changed_at or delivery.accepted_at or delivery.order.created_at
        t = elapsed_minutes(base)
        next_status = None

        if delivery.status == 'accepted' and t >= cfg.picking_up_minutes:
            next_status = 'picking_up'
        elif delivery.status == 'picking_up' and t >= cfg.out_for_delivery_minutes:
            next_status = 'out_for_delivery'
        elif delivery.status == 'out_for_delivery' and t >= cfg.delivered_minutes:
            next_status = 'delivered'

        if next_status is None:
            continue

        now = timezone.now()
        delivery.status = next_status
        if next_status in ('picking_up', 'out_for_delivery'):
            if not delivery.picked_up_at:
                delivery.picked_up_at = now
        elif next_status == 'delivered':
            delivery.delivered_at = now
            if not delivery.picked_up_at:
                delivery.picked_up_at = now
            # จบออเดอร์เดลิเวอร์รี่
            order = delivery.order
            if order.status not in ('paid', 'completed'):
                order.status = 'served'
                if cfg.auto_pay:
                    order.status = 'paid'
                    order.paid_at = now
                    order.payment_method = order.payment_method or 'cash'
                order.save()
        delivery.save()
        changed += 1
        notify(
            'delivery', delivery.order.display_code,
            f'ออเดอร์ {delivery.order.display_code} → สถานะจัดส่ง: {delivery.get_status_display()}',
            f'/orders/{delivery.order_id}/',
        )
    return changed


# ----------------------------------------------------------------------
# รายงาน
# ----------------------------------------------------------------------

def generate_report():
    """ส่งรายงานสรุปยอดขายประจำวันให้ Staff (สร้างวันละครั้ง)"""
    from django.contrib.auth.models import User
    from django.db.models import F, Sum

    today = timezone.localdate()
    # สร้างสรุปวันส่งท้าย — ถ้ายังไม่เคยมีการแจ้งเตือนรายงานวันนี้
    existing = Notification.objects.filter(kind='report', title__contains='สรุปยอดขาย').order_by('-created_at').first()
    if existing and existing.created_at.date() == today:
        return

    paid = Order.objects.filter(status='paid', paid_at__date=today)
    from .models import Delivery

    items_total = paid.aggregate(
        revenue=Sum(F('items__menu__price') * F('items__quantity'), default=0)
    )['revenue'] or 0
    fee_total = Delivery.objects.filter(
        order__in=paid.values('pk')
    ).aggregate(revenue=Sum('fee'))['revenue'] or 0
    revenue = items_total + fee_total
    count = paid.count()
    staff = User.objects.filter(is_staff=True)
    if revenue or count:
        msg = f'ยอดขายวันนี้ {count} ออเดอร์ รวม {revenue:,.2f} บาท'
        for s in staff:
            notify('report', 'สรุปยอดขายประจำวัน', msg, '/dashboard/', recipient=s)


# ----------------------------------------------------------------------
# ตัวรวมเรียก (entry point)
# ----------------------------------------------------------------------

def run_all(force=False):
    """รันระบบอัตโนมัติทั้งหมดแบบ idempotent — ใช้กับ manage.py หรือ view ได้

    force=True ข้ามการจำกัดความถี่ (ใช้ตอนเรียกจาก management command/cron)
    ความถี่จำกัดด้วยค่า AUTOMATION_MIN_INTERVAL (วินาที, 0 = ไม่จำกัด) —
    ป้องกันทุก GET วิ่ง state machine ซ้ำโดยไม่จำเป็นตอนเปิดใช้จริง
    """
    interval = getattr(settings, 'AUTOMATION_MIN_INTERVAL', 0)
    if interval > 0 and not force:
        # cache.add ช่วยกันข้าม worker ได้พอประมาณ (locmem ได้เฉพาะใน process เดียว)
        if not cache.add('automation:last_run', timezone.now().isoformat(),
                         timeout=interval):
            return {'order': 0, 'delivery': 0, 'skipped': True}

    cfg = AutomationSettings.get_setting()
    if not cfg.enabled:
        # ยังไม่เปิด autopilot — ใช้ระบบเดิม: จัดสรรงานที่ค้างเกินเวลารอ + ปล่อยงานค้าง
        maybe_auto_dispatch()
        return {'order': 0, 'delivery': 0}

    # โหมด autopilot: สถานะเดินเองตามเวลา ไม่มีงานค้าง (ไรเดอร์ไม่ถูกปล่อย)
    with transaction.atomic():
        order_changed = advance_order_status()
        delivery_changed = advance_delivery_status()
    generate_report()
    return {'order': order_changed, 'delivery': delivery_changed}

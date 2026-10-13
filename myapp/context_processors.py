from django.db.models import Count, Q

from .models import Delivery, Notification, Order


def notifications(request):
    """ส่งข้อมูลสถิติออเดอร์ที่ยังค้างอยู่ให้ทุกหน้า
    ใช้แสดง notification badge ใน navbar สำหรับ Staff
    """
    if not request.user.is_authenticated:
        return {}

    # ไม่สร้าง Profile ชนิด write-ทุก-request อีกต่อไป
    # (มี signal สร้างให้ผู้ใช้ใหม่อยู่แล้ว — ใช้ getattr fallback แทน)
    profile = getattr(request.user, 'profile', None)
    is_staff = request.user.is_staff

    context = {}

    # สถิติออเดอร์ — คำนวณเฉพาะ Staff เท่านั้น
    # (ผู้ใช้ทั่วไปไม่ได้ใช้ + ลด query ทุก request ของทุกคน)
    if is_staff:
        status_counts = Order.objects.filter(
            status__in=['open', 'preparing', 'ready', 'pending', 'confirmed']
        ).aggregate(
            open=Count('pk', filter=Q(status='open')),
            preparing=Count('pk', filter=Q(status='preparing')),
            ready=Count('pk', filter=Q(status='ready')),
            pending=Count('pk', filter=Q(status='pending')),
            confirmed=Count('pk', filter=Q(status='confirmed')),
        )
        context.update({
            'staff_new_orders': status_counts.get('preparing', 0) + status_counts.get('ready', 0),
            'staff_order_counts': status_counts,
            'staff_kitchen_orders': status_counts.get('open', 0) + status_counts.get('preparing', 0),
            'staff_delivery_orders': Order.objects.filter(
                order_type='delivery',
                status__in=['pending', 'confirmed', 'preparing', 'ready', 'served'],
            ).count(),
        })

    is_rider = (
        getattr(profile, 'is_rider', False)
        and not is_staff
    )

    if is_rider:
        context['rider_available_jobs'] = Delivery.objects.filter(
            status='pending',
            assigned_rider__isnull=True,
        ).count()
        context['rider_my_active'] = Delivery.objects.filter(
            assigned_rider=request.user,
        ).exclude(status__in=['delivered', 'cancelled']).count()

    # แจ้งเตือน: Staff เห็นข้อความรวม (broadcast) + ของตัวเอง
    #          / ผู้ใช้ทั่วไป+ไรเดอร์เห็นข้อความของตัวเอง
    if is_staff:
        notif_qs = Notification.objects.filter(
            Q(recipient__isnull=True) | Q(recipient=request.user)
        )
    else:
        notif_qs = Notification.objects.filter(recipient=request.user)

    shown_notifications = notif_qs.order_by('-created_at')[:10]
    unread_count = notif_qs.filter(is_read=False).count()

    context.update({
        'nav_notifications': shown_notifications,
        'unread_count': unread_count,
        'is_rider': is_rider,
    })
    return context

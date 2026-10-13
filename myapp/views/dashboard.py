"""Dashboard ผู้ดูแล + การตั้งค่าระบบอัตโนมัติ + หน้าจอครัว (KDS)"""

from ._common import *  # noqa: F403


@staff_required
@require_POST
def welcome_banner_update(request):
    """เปลี่ยน/รีเซ็ตรูปภาพหน้าต้อนรับบนหน้าแรก (เฉพาะ Staff)"""
    setting = HomeImage.get_setting()

    # รีเซ็ตกลับไปใช้รูปเริ่มต้นของระบบ
    if request.POST.get('reset'):
        if setting.hero_image:
            setting.hero_image.delete(save=False)
        setting.hero_image = None
        setting.save()
        messages.success(request, 'กลับไปใช้รูปภาพเริ่มต้นของระบบแล้ว')
        return redirect('home')

    form = HomeImageForm(request.POST, request.FILES, instance=setting)
    if form.is_valid() and 'hero_image' in request.FILES:
        if setting.hero_image:
            setting.hero_image.delete(save=False)
        form.save()
        messages.success(request, 'เปลี่ยนรูปภาพหน้าต้อนรับเรียบร้อยแล้ว')
    else:
        messages.error(request, 'ไม่สามารถเปลี่ยนรูปภาพได้ กรุณาตรวจสอบไฟล์ (รูปภาพ ขนาดไม่เกิน 10 MB)')
    return redirect('home')


@staff_required
def dashboard(request):
    """Dashboard สำหรับ Staff — สรุปสถิติทั้งหมด"""
    from datetime import timedelta

    from django.db.models import Sum
    from django.utils import timezone

    today = timezone.localdate()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    # สถิติออเดอร์
    orders_today = Order.objects.filter(created_at__date=today)
    orders_week = Order.objects.filter(created_at__date__gte=week_ago)
    orders_month = Order.objects.filter(created_at__date__gte=month_ago)

    # ออเดอร์เดลิเวอร์รี่
    delivery_today = orders_today.filter(order_type='delivery')
    delivery_week = orders_week.filter(order_type='delivery')
    delivery_month = orders_month.filter(order_type='delivery')

    # รายได้เดลิเวอร์รี่ — คำนวณใน SQL (แยกค่าอาหารกับค่าส่ง กันค่า fee บวกซ้ำต่อรายการ)
    def _delivery_revenue(qs):
        paid_qs = qs.filter(status='paid')
        items_total = paid_qs.aggregate(
            total=Sum(F('items__menu__price') * F('items__quantity'), default=0)
        )['total'] or 0
        fee_total = Delivery.objects.filter(
            order__in=paid_qs.values('pk')
        ).aggregate(total=Sum('fee'))['total'] or 0
        return items_total + fee_total

    delivery_revenue_today = _delivery_revenue(delivery_today)
    delivery_revenue_week = _delivery_revenue(delivery_week)
    delivery_revenue_month = _delivery_revenue(delivery_month)

    # ยอดขายรายวัน 7 วันล่าสุด (เฉพาะออเดอร์ที่ชำระแล้ว)
    revenue_by_day = {}
    for day in (today - timedelta(days=i) for i in range(6, -1, -1)):
        revenue_by_day[day.strftime('%Y-%m-%d')] = (
            Order.objects.filter(status='paid', paid_at__date=day).aggregate(
                total=Sum(F('items__menu__price') * F('items__quantity'))
            )['total'] or 0
        )
    sales_dates = list(revenue_by_day.keys())
    sales_values = [int(revenue_by_day[d]) for d in sales_dates]
    sales_labels = [timezone.datetime.strptime(d, '%Y-%m-%d').strftime('%d/%m') for d in sales_dates]

    context = {
        # สถิติทั่วไป
        'total_menus': MenuItem.objects.count(),
        'total_users': User.objects.count(),
        'total_categories': Category.objects.count(),
        # ออเดอร์วันนี้
        'orders_today_count': orders_today.count(),
        'revenue_today': orders_today.filter(status='paid').aggregate(
            total=Sum(F('items__menu__price') * F('items__quantity'))
        )['total'] or 0,
        # สถิติเดลิเวอร์รี่
        'delivery_today_count': delivery_today.count(),
        'delivery_revenue_today': delivery_revenue_today,
        'delivery_week_count': delivery_week.count(),
        'delivery_revenue_week': delivery_revenue_week,
        'delivery_month_count': delivery_month.count(),
        'delivery_revenue_month': delivery_revenue_month,
        'delivery_waiting_count': Order.objects.filter(
            order_type='delivery', delivery__status='pending'
        ).count(),
        'delivery_out_count': Order.objects.filter(
            order_type='delivery', delivery__status='out_for_delivery'
        ).count(),
        'delivery_no_info_count': Order.objects.filter(
            order_type='delivery', delivery__isnull=True
        ).exclude(status__in=['paid', 'cancelled', 'refunded', 'completed']).count(),
        # ออเดอร์เปิด
        'open_orders': Order.objects.filter(status='open').count(),
        'preparing_orders': Order.objects.filter(status='preparing').count(),
        'ready_orders': Order.objects.filter(status='ready').count(),
        'served_orders': Order.objects.filter(status='served').count(),
        # สต็อก: นับของใกล้หมด/หมด
        'out_of_stock_count': Ingredient.objects.filter(
            is_active=True, stock_qty__lte=0
        ).count(),
        'low_stock_list': Ingredient.objects.filter(
            is_active=True, reorder_level__gt=0,
            stock_qty__lte=F('reorder_level'),
        )[:5],
        'low_stock_count': Ingredient.objects.filter(
            is_active=True, reorder_level__gt=0, stock_qty__lte=F('reorder_level')
        ).count(),
        'coupon_count': Coupon.objects.filter(is_active=True).count(),
        'reservation_pending_count': Reservation.objects.filter(status='requested').count(),
        'review_pending_count': Review.objects.count(),
    # สถิติสัปดาห์
    'orders_week_count': orders_week.count(),
    'revenue_week': orders_week.filter(status='paid').aggregate(
        total=Sum(F('items__menu__price') * F('items__quantity'))
    )['total'] or 0,
    'avg_week_revenue': (orders_week.filter(status='paid').aggregate(
        total=Sum(F('items__menu__price') * F('items__quantity'))
    )['total'] or 0) / 7,
        # สถิติเดือน
        'orders_month_count': orders_month.count(),
        'revenue_month': orders_month.filter(status='paid').aggregate(
            total=Sum(F('items__menu__price') * F('items__quantity'))
        )['total'] or 0,
        # เมนูยอดนิยม
        'popular_items': OrderItem.objects.filter(
            order__status='paid'
        ).values('menu__name').annotate(
            total_ordered=Sum('quantity')
        ).order_by('-total_ordered')[:5],
        # ออเดอร์ล่าสุด
        'recent_orders': Order.objects.select_related('created_by')[:5],
        # ข้อมูลแผนภูมิยอดขาย
        'sales_labels': sales_labels,
        'sales_values': sales_values,
    }
    return render(request, 'dashboard/dashboard.html', context)


@staff_required
def automation_settings(request):
    """ตั้งค่านาฬิกาเดินสถานะอัตโนมัติ (Autopilot) — เปิด/ปิด + กำหนดเวลาขั้นตอน"""
    cfg = AutomationSettings.get_setting()

    if request.method == 'POST':

        def _int(value, default):
            if value == '' or value is None:
                return default
            try:
                return max(int(value), 0)
            except (TypeError, ValueError):
                return default

        cfg.enabled = request.POST.get('enabled') == 'on'
        cfg.auto_pay = request.POST.get('auto_pay') == 'on'
        cfg.auto_earn_points = request.POST.get('auto_earn_points') == 'on'
        cfg.preparing_minutes = _int(request.POST.get('preparing_minutes'), cfg.preparing_minutes)
        cfg.ready_minutes = _int(request.POST.get('ready_minutes'), cfg.ready_minutes)
        cfg.served_minutes = _int(request.POST.get('served_minutes'), cfg.served_minutes)
        cfg.picking_up_minutes = _int(request.POST.get('picking_up_minutes'), cfg.picking_up_minutes)
        cfg.out_for_delivery_minutes = _int(request.POST.get('out_for_delivery_minutes'), cfg.out_for_delivery_minutes)
        cfg.delivered_minutes = _int(request.POST.get('delivered_minutes'), cfg.delivered_minutes)
        cfg.save()
        messages.success(request, 'บันทึกการตั้งค่าระบบอัตโนมัติเรียบร้อยแล้ว')
        return redirect('automation_settings')

    return render(request, 'automation/automation_settings.html', {'cfg': cfg})


@staff_required
def kitchen_display(request):
    """จอครัว — แสดงออเดอร์ที่ต้องทำ + พร้อมเสิร์ฟ (สั่งเป็นกระดานสด)"""
    run_all()
    cooking = (
        Order.objects.filter(status__in=['open', 'preparing'])
        .prefetch_related('items', 'items__menu', 'items__addons')
        .order_by('created_at')
    )
    ready = (
        Order.objects.filter(status='ready')
        .prefetch_related('items', 'items__menu', 'items__addons')
        .order_by('created_at')
    )
    # กันคำสั่งเดียวกันพร้อมกันโดยไม่ได้ตั้งใจด้วย ETag ง่ายๆ (refresh อัตโนมัติทุก 15 วิ)
    return render(request, 'kitchen/kitchen_display.html', {
        'cooking': cooking,
        'ready': ready,
    })


@staff_required
@require_POST
def kds_update_status(request, pk):
    """เลื่อนสถานะครัวจากหน้าจอ KDS:
    open → preparing (เข้าครัว) → ready (เสร็จ) → served (เสิร์ฟแล้ว)
    """
    order = get_object_or_404(Order, pk=pk)

    # ตัดสต็อกเมื่อเข้าครัว — Order.save() ดูแลให้ (เข้า preparing)
    if order.status == 'open':
        new_status = 'preparing'
    elif order.status == 'preparing':
        new_status = 'ready'
    elif order.status == 'ready':
        new_status = 'served'
    else:
        messages.error(request, 'ออเดอร์นี้ไม่อยู่ในสถานะที่ใช้หน้าจอครัวจัดการได้')
        return redirect('kitchen_display')

    order.status = new_status
    order.save()
    messages.success(
        request,
        f'{order.display_code} → "{order.get_status_display()}" เรียบร้อย',
    )

    # เดลิเวอร์รี่: เสิร์ฟ = จัดส่งแล้ว อัปเดตสถานะขนส่งให้ตรงกัน
    if order.order_type == 'delivery' and new_status == 'served':
        delivery = getattr(order, 'delivery', None)
        if delivery is not None:
            delivery.status = 'delivered'
            delivery.delivered_at = timezone.now()
            delivery.save()

    return redirect('kitchen_display')

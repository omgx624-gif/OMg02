"""เดลิเวอร์รี่: แดชบอร์ด, ติดตาม, ไรเดอร์, ค่าส่ง, การตั้งค่า"""

from ._common import *  # noqa: F403
from ._common import _rider_status_counts


@staff_required
def delivery_dashboard(request):
    """แดชบอร์ดจัดการออเดอร์เดลิเวอร์รี่ (Staff) — ดูสถานะ/กำหนดไรเดอร์/ติดตาม"""
    run_all()
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')
    delivery_filter = request.GET.get('delivery_status', '')
    rider_filter = request.GET.get('rider', '')

    orders = (
        Order.objects.filter(order_type='delivery')
        .select_related('delivery', 'delivery__assigned_rider', 'created_by')
        .prefetch_related('items', 'items__menu')
        .order_by('-created_at')
    )

    if query:
        orders = orders.filter(
            Q(daily_code__icontains=query)
            | Q(delivery__recipient_name__icontains=query)
            | Q(delivery__phone__icontains=query)
            | Q(delivery__address__icontains=query)
            | Q(delivery__rider_name__icontains=query)
            | Q(delivery__assigned_rider__username__icontains=query)
        )
    if status_filter:
        orders = orders.filter(status=status_filter)
    if delivery_filter:
        orders = orders.filter(delivery__status=delivery_filter)
    if rider_filter:
        rider_obj = User.objects.filter(username=rider_filter).first()
        if rider_obj:
            orders = orders.filter(delivery__assigned_rider=rider_obj)

    paginator = Paginator(orders, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    # สรุปจำนวนตามสถานะการจัดส่ง
    delivery_status_counts = {
        'pending': Order.objects.filter(order_type='delivery', delivery__status='pending').count(),
        'accepted': Order.objects.filter(order_type='delivery', delivery__status='accepted').count(),
        'picking_up': Order.objects.filter(order_type='delivery', delivery__status='picking_up').count(),
        'out_for_delivery': Order.objects.filter(order_type='delivery', delivery__status='out_for_delivery').count(),
        'delivered': Order.objects.filter(order_type='delivery', delivery__status='delivered').count(),
        'cancelled': Order.objects.filter(order_type='delivery', delivery__status='cancelled').count(),
    }
    # ออเดอร์เดลิเวอร์รี่ที่ยังไม่ได้กรอกข้อมูลจัดส่ง
    no_info_count = Order.objects.filter(
        order_type='delivery', delivery__isnull=True
    ).exclude(status__in=['paid', 'cancelled', 'refunded', 'completed']).count()
    riders = User.objects.filter(profile__is_rider=True).order_by('username')

    context = {
        'page_obj': page_obj,
        'query': query,
        'status_filter': status_filter,
        'delivery_filter': delivery_filter,
        'rider_filter': rider_filter,
        'riders': riders,
        'delivery_status_counts': delivery_status_counts,
        'no_info_count': no_info_count,
        'ORDER_STATUS_CHOICES': Order.STATUS_CHOICES,
        'DELIVERY_STATUS_CHOICES': Delivery.DELIVERY_STATUS_CHOICES,
    }
    return render(request, 'delivery/delivery_dashboard.html', context)


@require_POST
@staff_required
def delivery_update_status(request, delivery_pk):
    """เปลี่ยนสถานะการจัดส่ง (รอจัดส่ง → รับงาน → ไปรับอาหาร → กำลังจัดส่ง → จัดส่งแล้ว)"""
    delivery = get_object_or_404(Delivery, pk=delivery_pk)
    new_status = request.POST.get('delivery_status', '')
    valid_statuses = [s for s, _ in Delivery.DELIVERY_STATUS_CHOICES]

    if new_status not in valid_statuses:
        messages.error(request, 'สถานะการจัดส่งไม่ถูกต้อง')
        return redirect('delivery_dashboard')

    delivery.status = new_status
    now = timezone.now()
    if new_status == 'accepted':
        delivery.accepted_at = now
        delivery.delivered_at = None
        delivery.picked_up_at = None
    elif new_status == 'picking_up':
        if not delivery.accepted_at:
            delivery.accepted_at = now
        delivery.delivered_at = None
    elif new_status == 'out_for_delivery':
        if not delivery.picked_up_at:
            delivery.picked_up_at = now
        delivery.delivered_at = None
    elif new_status == 'delivered':
        delivery.delivered_at = now
        if not delivery.picked_up_at:
            delivery.picked_up_at = now
        if not delivery.accepted_at:
            delivery.accepted_at = now
        if delivery.order.status not in ('paid', 'completed'):
            delivery.order.status = 'served'
            delivery.order.save(update_fields=['status'])
    elif new_status == 'cancelled':
        delivery.delivered_at = None
    else:
        delivery.delivered_at = None
    delivery.save()

    messages.success(
        request,
        f'ออเดอร์ {delivery.order.display_code} → สถานะจัดส่ง: "{delivery.get_status_display()}" เรียบร้อย',
    )
    redirect_url = request.POST.get('next') or 'delivery_dashboard'
    if url_has_allowed_host_and_scheme(redirect_url, allowed_hosts={request.get_host()}):
        return redirect(redirect_url)
    return redirect('delivery_dashboard')


def delivery_home(request):
    """หน้าแรกของระบบเดลิเวอร์รี่ — แสดงข้อมูลค่าส่ง/จุดนัดรับ + ปุ่มติดตาม"""
    store = StoreLocation.get_setting()
    context = {'store': store}
    return render(request, 'delivery/delivery_home.html', context)


def delivery_tracking(request):
    """หน้าติดตามออเดอร์เดลิเวอร์รี่ — กรอกรหัสออเดอร์เพื่อดูสถานะส่งของ

    - ค้นแบบตรงเป๊ะเท่านั้น (ไม่ partial match) + จำกัด 10 ครั้ง/นาที/IP
      เพื่อกันสุ่ม enumerate รหัสสั้นอย่าง #001
    - ข้อมูลผู้รับ (ชื่อ/เบอร์/ที่อยู่/ลิงก์นำทาง) แสดงเฉพาะ Staff,
      เจ้าของออเดอร์ และไรเดอร์ที่รับงาน — Guest เห็นเฉพาะสถานะเท่านั้น
    """
    from ..security import _increment, _keys, _too_many, get_client_ip

    delivery = None
    can_view_details = False
    rate_limited = False
    code = request.GET.get('code', '').strip()
    if code:
        ip_key = _keys('delivery-track', get_client_ip(request))[0]
        if _too_many(ip_key, limit=10, window=60):
            rate_limited = True
            messages.error(request, 'ค้นหาบ่อยเกินไป กรุณารอสักครู่แล้วลองใหม่อีกครั้ง')
        else:
            _increment(ip_key, window=60)
            stripped = code.lstrip('#').strip()
            queryset = Delivery.objects.select_related('order', 'assigned_rider').order_by('-created_at')
            # รับทั้ง #001 (เลขลำดับ ต้องตรงเป๊ะ) และรหัสเต็ม เช่น 20261007-001
            if stripped.isdigit() and len(stripped) <= 10:
                delivery = (
                    queryset.filter(order__daily_number=stripped)
                    .prefetch_related('order__items', 'order__items__menu')
                    .first()
                )
            if delivery is None:
                delivery = (
                    queryset.filter(order__daily_code__iexact=code)
                    .prefetch_related('order__items', 'order__items__menu')
                    .first()
                )

    if delivery is not None:
        user = request.user
        if user.is_staff:
            can_view_details = True
        elif user.is_authenticated and (
            delivery.order.created_by_id == user.id
            or delivery.assigned_rider_id == user.id
        ):
            can_view_details = True

    context = {
        'delivery': delivery,
        'can_view_details': can_view_details,
        'rate_limited': rate_limited,
        'code': code,
        'store': StoreLocation.get_setting(),
    }
    return render(request, 'delivery/delivery_tracking.html', context)


@rider_required
def rider_dashboard(request):
    """แดชบอร์ดไรเดอร์ — ดูงานที่รอรับ, จำนวนงานต่อสถานะ"""
    run_all()
    available = (
        Delivery.objects.filter(status='pending')
        .select_related('order', 'assigned_rider')
        .prefetch_related('order__items', 'order__items__menu')
        .order_by('created_at')
    )
    counts = _rider_status_counts()
    context = {
        'available': available,
        'counts': counts,
        'store': StoreLocation.get_setting(),
        'DELIVERY_STATUS_CHOICES': Delivery.DELIVERY_STATUS_CHOICES,
    }
    return render(request, 'delivery/rider_dashboard.html', context)


@rider_required
def rider_my_jobs(request):
    """รายการงานที่ไรเดอร์คนนี้รับไว้แล้ว (ทั้งสถานะ)"""
    run_all()
    my_jobs = (
        Delivery.objects.filter(assigned_rider=request.user)
        .select_related('order')
        .prefetch_related('order__items', 'order__items__menu')
        .order_by('-created_at')
    )
    status_filter = request.GET.get('status', '')
    if status_filter:
        my_jobs = my_jobs.filter(status=status_filter)

    active = my_jobs.exclude(
        status__in=['delivered', 'cancelled']
    ).order_by('created_at')
    history = my_jobs.filter(
        status__in=['delivered', 'cancelled']
    ).order_by('-delivered_at', '-created_at')

    context = {
        'active': active,
        'history': history,
        'status_filter': status_filter,
        'counts': _rider_status_counts(),
        'store': StoreLocation.get_setting(),
        'DELIVERY_STATUS_CHOICES': Delivery.DELIVERY_STATUS_CHOICES,
    }
    return render(request, 'delivery/rider_my_jobs.html', context)


@require_POST
@rider_required
def rider_accept_job(request, delivery_pk):
    """ไรเดอร์รับงาน (self-assign) — เปลี่ยนสถานะเป็น accepted และผูกไรเดอร์"""
    delivery = get_object_or_404(Delivery, pk=delivery_pk)
    if delivery.status != 'pending':
        messages.error(request, 'งานนี้ไม่เปิดให้รับแล้ว')
        return redirect('rider_dashboard')
    delivery.assigned_rider = request.user
    delivery.rider_name = request.user.get_full_name() or request.user.username
    delivery.status = 'accepted'
    delivery.accepted_at = timezone.now()
    delivery.save()
    messages.success(request, f'รับงานออเดอร์ {delivery.order.display_code} เรียบร้อย')
    return redirect('rider_my_jobs')


@require_POST
@rider_required
def rider_update_status(request, delivery_pk):
    """ไรเดอร์อัปเดตสถานะงานของตัวเอง (ออกจากร้าน → กำลังจัดส่ง → จัดส่งแล้ว)"""
    delivery = get_object_or_404(Delivery, pk=delivery_pk)
    if delivery.assigned_rider != request.user and not request.user.is_staff:
        messages.error(request, 'คุณไม่ได้รับมอบหมายงานนี้')
        return redirect('rider_dashboard')

    new_status = request.POST.get('delivery_status', '')
    valid_statuses = [s for s, _ in Delivery.DELIVERY_STATUS_CHOICES]
    if new_status not in valid_statuses:
        messages.error(request, 'สถานะการจัดส่งไม่ถูกต้อง')
        return redirect('rider_my_jobs')

    now = timezone.now()
    delivery.status = new_status
    if new_status == 'picking_up':
        if not delivery.accepted_at:
            delivery.accepted_at = now
        delivery.delivered_at = None
    elif new_status == 'out_for_delivery':
        if not delivery.picked_up_at:
            delivery.picked_up_at = now
        delivery.delivered_at = None
    elif new_status == 'delivered':
        delivery.delivered_at = now
        if not delivery.picked_up_at:
            delivery.picked_up_at = now
        if delivery.order.status not in ('paid', 'completed'):
            delivery.order.status = 'served'
            delivery.order.save(update_fields=['status'])
    delivery.save()

    messages.success(
        request,
        f'ออเดอร์ {delivery.order.display_code} → "{delivery.get_status_display()}" เรียบร้อย',
    )
    return redirect('rider_my_jobs')


@staff_required
def delivery_assign_rider(request, delivery_pk):
    """แอดมินกำหนดไรเดอร์ให้กับงาน (admin assignment)"""
    delivery = get_object_or_404(Delivery, pk=delivery_pk)
    rider_id = request.POST.get('rider_id', '')
    rider = None
    if rider_id:
        rider = User.objects.filter(pk=rider_id, profile__is_rider=True).first()

    if not rider:
        messages.error(request, 'กรุณาเลือกไรเดอร์ให้ถูกต้อง')
        return redirect('delivery_dashboard')

    delivery.assigned_rider = rider
    delivery.rider_name = rider.get_full_name() or rider.username
    # ถ้ายังไม่เคยรับงาน ให้เปลี่ยนเป็น accepted (ไรเดอร์ออกไปส่งแล้ว)
    if delivery.status not in ('delivered', 'cancelled', 'out_for_delivery', 'picking_up'):
        delivery.status = 'accepted'
        if not delivery.accepted_at:
            delivery.accepted_at = timezone.now()
    delivery.save()
    messages.success(request, f'มอบหมายงาน {delivery.order.display_code} ให้ "{rider}" เรียบร้อย')
    redirect_url = request.POST.get('next') or 'delivery_dashboard'
    if url_has_allowed_host_and_scheme(redirect_url, allowed_hosts={request.get_host()}):
        return redirect(redirect_url)
    return redirect('delivery_dashboard')


@staff_required
def delivery_calc_fee(request, delivery_pk):
    """คำนวณระยะทางและค่าส่งอัตโนมัติจากพิกัด (บังคับใหม่แม้เคยล็อกค่าไว้)"""
    delivery = get_object_or_404(Delivery, pk=delivery_pk)
    distance = delivery.calc_distance_km()
    if distance is None:
        messages.error(request, 'ยังไม่มีพิกัดปลายทางของออเดอร์นี้ กรุณาเลือกตำแหน่งบนแผนที่ก่อน')
        return redirect('delivery_dashboard')

    delivery.fee_locked = False
    delivery.update_distance_and_fee(save=False)
    delivery.save()
    messages.success(
        request,
        f'คำนวณระยะทาง {delivery.distance_km} กม. → ค่าส่ง {delivery.fee:.2f} บาท เรียบร้อย',
    )
    redirect_url = request.POST.get('next') or 'delivery_dashboard'
    if url_has_allowed_host_and_scheme(redirect_url, allowed_hosts={request.get_host()}):
        return redirect(redirect_url)
    return redirect('delivery_dashboard')


@staff_required
@require_POST
def delivery_geocode(request, delivery_pk):
    """ค้นหาพิกัดปลายทางจากที่อยู่จัดส่ง (API ภายนอก: Nominatim/OpenStreetMap)
    แล้วบันทึกพิกัด + คำนวณระยะทาง/ค่าส่งอัตโนมัติ (ใช้เมื่อที่อยู่พร้อมแต่ยังไม่มีพิกัด)
    """
    delivery = get_object_or_404(Delivery, pk=delivery_pk)
    address = (request.POST.get('address') or delivery.address or '').strip()
    if address and address != delivery.address:
        delivery.address = address
        delivery.save(update_fields=['address'])
    if not delivery.address:
        messages.error(request, 'ยังไม่มีที่อยู่จัดส่ง — กรุณากรอกที่อยู่ก่อนค้นหาพิกัด')
        redirect_url = request.POST.get('next') or 'delivery_dashboard'
        if url_has_allowed_host_and_scheme(redirect_url, allowed_hosts={request.get_host()}):
            return redirect(redirect_url)
        return redirect('delivery_dashboard')

    coords = delivery.geocode_from_address()
    if coords is None:
        messages.error(
            request, 'ไม่พบพิกัดจากที่อยู่ที่กรอก — ตรวจสอบที่อยู่ให้ครบถ้วน หรือลากหมุดบนแผนที่แทน'
        )
    else:
        lat, lng = coords
        fee_note = (
            f'ค่าส่ง {delivery.fee:.2f} บาท' if delivery.distance_km is not None else 'ยังไม่มีค่าส่ง'
        )
        messages.success(
            request,
            f'ค้นหาพิกัดสำเร็จ ({lat:.5f}, {lng:.5f}) — ระยะทาง {delivery.distance_km} กม. → {fee_note}',
        )
    redirect_url = request.POST.get('next') or 'delivery_dashboard'
    if url_has_allowed_host_and_scheme(redirect_url, allowed_hosts={request.get_host()}):
        return redirect(redirect_url)
    return redirect('delivery_dashboard')


@staff_required
@require_POST
def line_notify_test(request):
    """ส่งข้อความทดสอบไปยัง Line ผ่าน token ที่ตั้งใน Admin (หรือ env LINE_NOTIFY_TOKEN)
    ใช้เช็คว่าการเชื่อมต่อ API ภายนอกของ Line ทำงานจริงหรือไม่
    """
    from ..services import notify_line

    sent = notify_line(
        StoreLocation.get_setting().line_notify_token,
        '✅ ทดสอบการเชื่อมต่อ Line Notify — ระบบแจ้งเตือนทำงานปกติ',
    )
    if sent:
        messages.success(request, 'ส่งข้อความทดสอบถึง Line สำเร็จ')
    else:
        messages.error(
            request,
            'ส่งข้อความทดสอบไม่สำเร็จ — ตรวจสอบ Line Notify Token ในระบบ Admin '
            '(หรือตัวแปรสภาพแวดล้อม LINE_NOTIFY_TOKEN)',
        )
    return redirect('delivery_settings')


@staff_required
def delivery_settings(request):
    """ตั้งค่าตำแหน่งร้าน อัตราค่าส่ง และระบบจัดสรรงานอัตโนมัติ"""
    store = StoreLocation.get_setting()
    if request.method == 'POST':
        lat = request.POST.get('lat')
        lng = request.POST.get('lng')
        try:
            store.lat = float(lat) if lat else store.lat
            store.lng = float(lng) if lng else store.lng
        except (TypeError, ValueError):
            messages.error(request, 'พิกัดไม่ถูกต้อง')
            return redirect('delivery_settings')

        store.name = request.POST.get('name', store.name).strip() or store.name
        store.address = request.POST.get('address', store.address).strip()
        fee_base = request.POST.get('fee_base')
        fee_per_km = request.POST.get('fee_per_km')
        free_over = request.POST.get('free_delivery_over')
        from decimal import Decimal, InvalidOperation

        def _dec(value, default):
            if value == '' or value is None:
                return default
            try:
                return Decimal(value)
            except InvalidOperation:
                return default

        def _int_or_default(value, default):
            if value == '' or value is None:
                return default
            try:
                parsed = int(value)
                return max(parsed, 0)
            except (TypeError, ValueError):
                return default

        store.fee_base = _dec(fee_base, store.fee_base)
        store.fee_per_km = _dec(fee_per_km, store.fee_per_km)
        if free_over == '':
            store.free_delivery_over = None
        else:
            store.free_delivery_over = _dec(free_over, store.free_delivery_over)

        # --- ระบบจัดสรรงานอัตโนมัติ ---
        store.auto_assign_enabled = request.POST.get('auto_assign_enabled') == 'on'
        store.auto_assign_grace_minutes = _int_or_default(
            request.POST.get('auto_assign_grace_minutes'), store.auto_assign_grace_minutes
        )
        store.auto_release_minutes = _int_or_default(
            request.POST.get('auto_release_minutes'), store.auto_release_minutes
        )
        store.save()
        messages.success(request, 'บันทึกการตั้งค่าเดลิเวอร์รี่เรียบร้อยแล้ว')
        return redirect('delivery_settings')

    from ..services import mask_token

    context = {
        'store': store,
        'line_token_masked': mask_token(store.line_notify_token),
        'has_line_token': bool(store.line_notify_token),
    }
    return render(request, 'delivery/delivery_settings.html', context)

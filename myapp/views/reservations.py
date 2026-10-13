"""การจองโต๊ะ: ฟอร์ม, รายการ, Dashboard สำหรับ Staff"""

from ._common import *  # noqa: F403


@rate_limit(
    'reservation', 5, 3600,
    key_parts=lambda r: (get_client_ip(r),),
    message='มีการส่งคำขอยืนยันบ่อยเกินไป กรุณารอสักครู่แล้วลองใหม่อีกครั้ง',
)
def reservation_create(request):
    """จองโต๊ะ (ลูกค้าทั่วไป ไม่ต้องล็อกอิน) — ระบบจะแจ้งพนักงานอัตโนมัติ
    จำกัด 5 ครั้ง/ชั่วโมง/IP ผ่าน decorator @rate_limit"""
    if request.method == 'POST':
        form = ReservationForm(request.POST)
        if form.is_valid():
            reservation = form.save(commit=False)
            if request.user.is_authenticated:
                reservation.created_by = request.user
            reservation.status = 'requested'
            reservation.save()
            from ..services import announce_new_reservation
            announce_new_reservation(reservation)
            t = reservation.reservation_time
            time_str = t.strftime('%H:%M') if hasattr(t, 'strftime') else str(t)
            messages.success(
                request,
                f'ส่งคำขอยืนยันการจอง {reservation.reservation_date:%d/%m/%Y} '
                f'{time_str} เรียบร้อยแล้ว กรุณารอพนักงานยืนยัน',
            )
            return redirect('reservation_dashboard') if getattr(request.user, 'is_staff', False) else redirect('reservation_list')
        messages.error(request, 'กรุณาตรวจสอบข้อมูลการจองให้ถูกต้อง')
    else:
        form = ReservationForm()
    return render(request, 'reservation/reservation_create.html', {'form': form})


def reservation_list(request):
    """รายการจองของลูกค้า (ดูจองของตัวเอง ถ้าล็อกอิน — ไม่ login จะแสดงจองล่าสุดจาก session ง่ายๆ)"""
    if request.user.is_authenticated and not request.user.is_staff:
        reservations = Reservation.objects.filter(created_by=request.user).order_by('-reservation_date')
    else:
        reservations = []
    return render(request, 'reservation/reservation_list.html', {'reservations': reservations})


@staff_required
def reservation_dashboard(request):
    """แดชบอร์ดจัดการการจอง (Staff) — ดูคิว/เปลี่ยนสถานะ/ค้นหา"""
    query = request.GET.get('q', '').strip()
    date_filter = request.GET.get('date', '')
    status_filter = request.GET.get('status', '')

    reservations = Reservation.objects.select_related('created_by').order_by('reservation_date', 'reservation_time')
    if query:
        reservations = reservations.filter(
            Q(customer_name__icontains=query)
            | Q(phone__icontains=query)
            | Q(table_number__icontains=query)
        )
    if date_filter:
        reservations = reservations.filter(reservation_date=date_filter)
    if status_filter:
        reservations = reservations.filter(status=status_filter)

    pending_count = Reservation.objects.filter(status='requested').count()
    today = timezone.localdate()
    today_count = Reservation.objects.filter(reservation_date=today).exclude(status__in=['cancelled', 'no_show']).count()

    context = {
        'reservations': reservations,
        'query': query,
        'date_filter': date_filter,
        'status_filter': status_filter,
        'pending_count': pending_count,
        'today_count': today_count,
        'today': today,
        'STATUS_CHOICES': Reservation.STATUS_CHOICES,
    }
    return render(request, 'reservation/reservation_dashboard.html', context)


@staff_required
@require_POST
def reservation_update_status(request, pk):
    """เปลี่ยนสถานะการจอง (ยืนยัน/นั่งแล้ว/เสร็จสิ้น/ยกเลิก/ไม่มา)"""
    reservation = get_object_or_404(Reservation, pk=pk)
    new_status = request.POST.get('status', '')
    if new_status in dict(Reservation.STATUS_CHOICES):
        reservation.status = new_status
        reservation.save(update_fields=['status'])
        messages.success(
            request,
            f'เปลี่ยนสถานะการจอง "{reservation.customer_name}" เป็น '
            f'"{reservation.get_status_display()}" เรียบร้อย',
        )
    else:
        messages.error(request, 'สถานะไม่ถูกต้อง')
    return redirect('reservation_dashboard')


@staff_required
def reservation_delete(request, pk):
    """ลบการจอง (มีหน้ายืนยัน)"""
    reservation = get_object_or_404(Reservation, pk=pk)
    if request.method == 'POST':
        name = reservation.customer_name
        reservation.delete()
        messages.warning(request, f'ลบการจองของ "{name}" เรียบร้อยแล้ว')
        return redirect('reservation_dashboard')
    return render(request, 'reservation/reservation_confirm_delete.html', {'reservation': reservation})

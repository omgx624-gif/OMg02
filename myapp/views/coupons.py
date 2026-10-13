"""คูปอง/โปรโมชั่น + ระบบคะแนนสะสม (Points Redemption)"""

from ._common import *  # noqa: F403
from ._common import _user_can_access_order


@staff_required
def coupon_list(request):
    """รายการคูปองทั้งหมด (Staff)"""
    coupons = Coupon.objects.all()
    return render(request, 'coupon/coupon_list.html', {'coupons': coupons})


@staff_required
def coupon_create(request):
    """สร้างคูปองใหม่"""
    if request.method == 'POST':
        form = CouponForm(request.POST)
        if form.is_valid():
            coupon = form.save()
            messages.success(request, f'สร้างคูปอง "{coupon.code}" เรียบร้อยแล้ว')
            return redirect('coupon_list')
        messages.error(request, 'กรุณาตรวจสอบข้อมูลคูปองให้ถูกต้อง')
    else:
        form = CouponForm()
    return render(request, 'coupon/coupon_form.html', {'form': form, 'title': 'สร้างคูปองใหม่'})


@staff_required
def coupon_update(request, pk):
    """แก้ไขคูปอง"""
    coupon = get_object_or_404(Coupon, pk=pk)
    if request.method == 'POST':
        form = CouponForm(request.POST, instance=coupon)
        if form.is_valid():
            form.save()
            messages.success(request, f'แก้ไขคูปอง "{coupon.code}" เรียบร้อยแล้ว')
            return redirect('coupon_list')
        messages.error(request, 'กรุณาตรวจสอบข้อมูลคูปองให้ถูกต้อง')
    else:
        form = CouponForm(instance=coupon)
    return render(request, 'coupon/coupon_form.html', {'form': form, 'title': f'แก้ไขคูปอง {coupon.code}'})


@staff_required
def coupon_delete(request, pk):
    """ลบคูปอง (มีหน้ายืนยัน)"""
    coupon = get_object_or_404(Coupon, pk=pk)
    if request.method == 'POST':
        code = coupon.code
        coupon.delete()
        messages.warning(request, f'ลบคูปอง "{code}" เรียบร้อยแล้ว')
        return redirect('coupon_list')
    return render(request, 'coupon/coupon_confirm_delete.html', {'coupon': coupon})


@require_POST
@login_required
def order_apply_coupon(request, pk):
    """ใช้คูปองกับออเดอร์ (คำนวณส่วนลด snapshot ลงในออเดอร์)"""
    order = get_object_or_404(Order, pk=pk)
    if not _user_can_access_order(request.user, order):
        messages.error(request, 'คุณไม่มีสิทธิ์แก้ไขออเดอร์นี้')
        return redirect('order_list')
    back_page = request.POST.get('page', '') or request.GET.get('page', '')

    can_apply, used = order_coupon_status(order)
    if not can_apply:
        if used:
            messages.info(request, f'ออเดอร์นี้ใช้คูปอง {used.code} ไปแล้ว กรุณาเอารหัสออกก่อนถ้าต้องการเปลี่ยน')
        else:
            messages.error(request, 'ไม่สามารถใช้คูปองกับออเดอร์ที่ปิดบิล/ยกเลิกแล้วได้')
        return redirect('order_detail', pk=order.pk)

    form = CouponApplyForm(request.POST)
    if form.is_valid():
        coupon, discount, error = validate_coupon(
            form.cleaned_data.get('coupon_code'), order.total_price, request.user,
        )
        if error:
            messages.error(request, error[1])
            return redirect('order_detail', pk=order.pk)

        order.coupon_code = coupon.code
        order.coupon_discount = discount
        order.save(update_fields=['coupon_code', 'coupon_discount'])
        messages.success(
            request,
            f'ใช้คูปอง {coupon.code} เรียบร้อย ได้ส่วนลด {discount:,.2f} บาท',
        )
    else:
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)

    url = reverse('order_detail', args=[order.pk])
    if back_page.isdigit():
        url += f'?page={back_page}'
    url += '#cart-list'
    return redirect(url)


@require_POST
@login_required
def order_remove_coupon(request, pk):
    """เอารหัสคูปองออกจากออเดอร์"""
    order = get_object_or_404(Order, pk=pk)
    if not _user_can_access_order(request.user, order):
        messages.error(request, 'คุณไม่มีสิทธิ์แก้ไขออเดอร์นี้')
        return redirect('order_list')
    if order.coupon_code:
        messages.info(request, f'เอารหัสคูปอง {order.coupon_code} ออกจากออเดอร์แล้ว')
    order.coupon_code = ''
    order.coupon_discount = 0
    order.save(update_fields=['coupon_code', 'coupon_discount'])
    return redirect('order_detail', pk=order.pk)


@login_required
def points_redemption(request):
    """หน้าแลกคะแนนสะสมเป็นสิทธิ์ประโยชน์ (สร้างคูปองผูกเจ้าของให้ผู้ใช้)
    ดูยอดคงเหลือ + รายการสิทธิ์ที่แลกได้ + ประวัติการได้/ใช้คะแนน
    """
    from datetime import timedelta
    from uuid import uuid4

    from django.utils import timezone

    profile, _ = Profile.objects.get_or_create(user=request.user)
    rewards = PointReward.objects.filter(is_active=True).order_by('points_cost')
    transactions = profile.point_transactions.select_related('reward', 'order')[:20]

    if request.method == 'POST':
        reward_id = request.POST.get('reward_id')
        reward = get_object_or_404(PointReward, pk=reward_id, is_active=True)

        if not profile.redeem_points(
            reward.points_cost,
            reason=f'แลกสิทธิ์ "{reward.name}"',
            reward=reward,
        ):
            messages.error(
                request,
                f'คะแนนของคุณ {profile.points} ไม่พอแลกสิทธิ์นี้ '
                f'(ต้องใช้ {reward.points_cost} คะแนน)',
            )
            return redirect('points_redemption')

        # ออกคูปองผูกเจ้าของ อายุ 30 วัน ใช้ได้เฉพาะผู้แลก
        code = f'PTS-{reward.pk}-{uuid4().hex[:6].upper()}'
        Coupon.objects.create(
            code=code,
            owner=request.user,
            is_active=True,
            discount_type=reward.discount_type,
            value=reward.value,
            min_order=reward.min_order,
            valid_until=timezone.now() + timedelta(days=30),
        )
        messages.success(
            request,
            f'แลก "{reward.name}" สำเร็จ ({reward.points_cost} คะแนน) '
            f'รับคูปอง {code} กรอกตอนสั่งอาหารได้เลย',
        )
        return redirect('points_redemption')

    context = {
        'profile': profile,
        'rewards': rewards,
        'transactions': transactions,
        'balance': profile.points,
        'point_value': float(profile.points_rate),
    }
    return render(request, 'points/points_redemption.html', context)

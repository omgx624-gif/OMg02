"""ผู้ใช้: รายชื่อ, โปรไฟล์, สร้าง/แก้ไข, การแจ้งเตือน"""

from ._common import *  # noqa: F403


@staff_required
def user_list(request):
    """รายชื่อผู้ใช้ทั้งหมด + ค้นหา + แบ่งหน้า"""
    query = request.GET.get('q', '').strip()

    users = User.objects.select_related('profile').all().order_by('-date_joined')
    if query:
        users = users.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
        )

    paginator = Paginator(users, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'query': query,
        'total_users': paginator.count,
    }
    return render(request, 'user/user_list.html', context)


@staff_required
def user_profile_detail(request, pk):
    """ดูโปรไฟล์ผู้ใช้ (เฉพาะ Staff) + อัปโหลดรูปโปรไฟล์"""
    target = get_object_or_404(User.objects.select_related('profile'), pk=pk)
    profile, _ = Profile.objects.get_or_create(user=target)

    avatar_form = UserAvatarForm(instance=profile)
    cover_form = UserCoverForm(instance=profile)

    if request.method == 'POST' and 'avatar_submit' in request.POST:
        avatar_form = UserAvatarForm(request.POST, request.FILES, instance=profile)
        if avatar_form.is_valid():
            avatar_form.save()
            messages.success(request, f'อัปโหลดรูปโปรไฟล์ของ "{target.username}" เรียบร้อยแล้ว')
            return redirect('user_profile_detail', pk=target.pk)
        else:
            messages.error(request, 'กรุณาตรวจสอบไฟล์รูปภาพ')
    elif request.method == 'POST' and 'cover_submit' in request.POST:
        cover_form = UserCoverForm(request.POST, request.FILES, instance=profile)
        if cover_form.is_valid():
            cover_form.save()
            messages.success(request, f'อัปโหลดรูปปกของ "{target.username}" เรียบร้อยแล้ว')
            return redirect('user_profile_detail', pk=target.pk)
        else:
            messages.error(request, 'กรุณาตรวจสอบไฟล์รูปภาพ')

    return render(request, 'user/user_profile_detail.html', {
        'target': target,
        'avatar_form': avatar_form,
        'cover_form': cover_form,
    })


@staff_required
def user_create(request):
    """Create: เพิ่มผู้ใช้ใหม่ (เฉพาะ superuser เท่านั้นที่ตั้ง is_staff ได้)"""
    can_set_staff = request.user.is_superuser
    if request.method == 'POST':
        form = UserCreateForm(request.POST, request.FILES, can_set_staff=can_set_staff)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'เพิ่มผู้ใช้ "{user.username}" เรียบร้อยแล้ว')
            return redirect('user_list')
        messages.error(request, 'กรุณาตรวจสอบข้อมูลที่กรอกให้ถูกต้อง')
    else:
        form = UserCreateForm(can_set_staff=can_set_staff)
    return render(request, 'user/user_form.html', {'form': form, 'title': 'เพิ่มผู้ใช้ใหม่'})


@staff_required
def user_update(request, pk):
    """Update: แก้ไขข้อมูลผู้ใช้ (เฉพาะ superuser เท่านั้นที่ตั้ง is_staff ได้)"""
    target = get_object_or_404(User.objects.select_related('profile'), pk=pk)
    can_set_staff = request.user.is_superuser
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, request.FILES, instance=target,
                              can_set_staff=can_set_staff)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'แก้ไขผู้ใช้ "{user.username}" เรียบร้อยแล้ว')
            return redirect('user_list')
        messages.error(request, 'กรุณาตรวจสอบข้อมูลที่กรอกให้ถูกต้อง')
    else:
        form = UserUpdateForm(instance=target, can_set_staff=can_set_staff)
    return render(request, 'user/user_form.html',
                  {'form': form, 'title': f'แก้ไขผู้ใช้: {target.username}', 'target': target})


@staff_required
def user_delete(request, pk):
    """Delete: ลบผู้ใช้ (มีหน้ายืนยันก่อนลบ) — ห้ามลบบัญชีตัวเอง"""
    target = get_object_or_404(User, pk=pk)
    if target.pk == request.user.pk:
        messages.error(request, 'ไม่สามารถลบบัญชีของตัวเองได้')
        return redirect('user_list')

    if request.method == 'POST':
        name = target.username
        target.delete()
        messages.warning(request, f'ลบผู้ใช้ "{name}" เรียบร้อยแล้ว')
        return redirect('user_list')
    return render(request, 'user/user_confirm_delete.html', {'target': target})


@login_required
def user_profile(request):
    """หน้าโปรไฟล์ของผู้ใช้: ดู/แก้ไขข้อมูลส่วนตัว + อัปโหลดรูป + เปลี่ยนรหัสผ่าน"""
    success_msg = None

    # สร้าง Profile ถ้ายังไม่มี
    profile, _ = Profile.objects.get_or_create(user=request.user)

    # ลบรูปปกโปรไฟล์
    if request.method == 'POST' and 'cover_clear' in request.POST:
        if profile.cover:
            profile.cover.delete(save=False)
            profile.cover = None
            profile.save()
            success_msg = 'ลบรูปปกโปรไฟล์เรียบร้อยแล้ว'
        return render(request, 'user/user_profile.html', {
            'basic_form': UserBasicForm(instance=request.user),
            'avatar_form': UserAvatarForm(instance=profile),
            'cover_form': UserCoverForm(instance=profile),
            'pw_form': UserChangePasswordForm(user=request.user),
            'profile': profile,
            'success_msg': success_msg,
        })

    # ลบรูปโปรไฟล์
    if request.method == 'POST' and 'avatar_clear' in request.POST:
        if profile.avatar:
            profile.avatar.delete(save=False)
            profile.avatar = None
            profile.save()
            success_msg = 'ลบรูปโปรไฟล์เรียบร้อยแล้ว'
        return render(request, 'user/user_profile.html', {
            'basic_form': UserBasicForm(instance=request.user),
            'avatar_form': UserAvatarForm(instance=profile),
            'cover_form': UserCoverForm(instance=profile),
            'pw_form': UserChangePasswordForm(user=request.user),
            'profile': profile,
            'success_msg': success_msg,
        })

    # ฟอร์มแก้ไขข้อมูล User (ชื่อจริง นามสกุล อีเมล)
    if request.method == 'POST' and 'basic_submit' in request.POST:
        basic_form = UserBasicForm(request.POST, instance=request.user)
        avatar_form = UserAvatarForm(instance=profile)
        cover_form = UserCoverForm(instance=profile)
        pw_form = UserChangePasswordForm(user=request.user)
        if basic_form.is_valid():
            basic_form.save()
            success_msg = 'บันทึกข้อมูลส่วนตัวเรียบร้อยแล้ว'
        else:
            messages.error(request, 'กรุณาตรวจสอบข้อมูลที่กรอกให้ถูกต้อง')
    # ฟอร์มอัปโหลดรูปโปรไฟล์
    elif request.method == 'POST' and 'avatar_submit' in request.POST:
        basic_form = UserBasicForm(instance=request.user)
        avatar_form = UserAvatarForm(request.POST, request.FILES, instance=profile)
        cover_form = UserCoverForm(instance=profile)
        pw_form = UserChangePasswordForm(user=request.user)
        if avatar_form.is_valid():
            avatar_form.save()
            success_msg = 'อัปโหลดรูปโปรไฟล์เรียบร้อยแล้ว'
        else:
            messages.error(request, 'กรุณาตรวจสอบไฟล์รูปภาพ')
    # ฟอร์มอัปโหลดรูปปกโปรไฟล์
    elif request.method == 'POST' and 'cover_submit' in request.POST:
        basic_form = UserBasicForm(instance=request.user)
        avatar_form = UserAvatarForm(instance=profile)
        cover_form = UserCoverForm(request.POST, request.FILES, instance=profile)
        pw_form = UserChangePasswordForm(user=request.user)
        if cover_form.is_valid():
            cover_form.save()
            success_msg = 'อัปโหลดรูปปกโปรไฟล์เรียบร้อยแล้ว'
        else:
            messages.error(request, 'กรุณาตรวจสอบไฟล์รูปภาพ')
    else:
        basic_form = UserBasicForm(instance=request.user)
        avatar_form = UserAvatarForm(instance=profile)
        cover_form = UserCoverForm(instance=profile)
        pw_form = UserChangePasswordForm(user=request.user)

    context = {
        'basic_form': basic_form,
        'avatar_form': avatar_form,
        'cover_form': cover_form,
        'pw_form': pw_form,
        'profile': profile,
        'success_msg': success_msg,
    }
    return render(request, 'user/user_profile.html', context)


@login_required
def user_change_password(request):
    """เปลี่ยนรหัสผ่านของผู้ใช้เอง"""
    if request.method != 'POST':
        return redirect('user_profile')

    form = UserChangePasswordForm(user=request.user, data=request.POST)
    if form.is_valid():
        form.save()
        update_session_auth_hash(request, request.user)
        messages.success(request, 'เปลี่ยนรหัสผ่านเรียบร้อยแล้ว! กรุณาเข้าสู่ระบบใหม่ถ้ายังไม่เห็นการเปลี่ยนแปลง')
    else:
        messages.error(request, 'กรุณาตรวจสอบรหัสผ่านให้ถูกต้อง')

    return redirect('user_profile')


@login_required
def user_order_history(request):
    """ประวัติสั่งอาหารของผู้ใช้ตัวเอง"""
    if request.user.is_staff:
        orders = Order.objects.prefetch_related('items', 'items__menu', 'items__addons').all()
    else:
        orders = Order.objects.prefetch_related('items', 'items__menu', 'items__addons').filter(created_by=request.user)

    status_counts = {}
    for status_val, status_label in Order.STATUS_CHOICES:
        status_counts[status_val] = orders.filter(status=status_val).count()

    total_orders = orders.count()
    active_orders = orders.exclude(status__in=['paid', 'cancelled', 'refunded', 'completed']).count()
    # ยอดใช้จ่ายรวม (ชำระแล้ว) — คำนวณใน SQL แทนการวนลูปเรียก total_price ทีละออเดอร์
    paid_qs = orders.filter(status='paid')
    items_total = paid_qs.aggregate(
        total=Sum(F('items__menu__price') * F('items__quantity'), default=0)
    )['total'] or 0
    fee_total = Delivery.objects.filter(
        order__in=paid_qs.values('pk')
    ).aggregate(total=Sum('fee'))['total'] or 0
    total_spent = items_total + fee_total

    paginator = Paginator(orders, 9)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'total_orders': total_orders,
        'active_orders': active_orders,
        'status_counts': status_counts,
        'total_spent': total_spent,
        'STATUS_CHOICES': Order.STATUS_CHOICES,
    }
    return render(request, 'user/user_orders.html', context)


@login_required
def notifications_center(request):
    """หน้าศูนย์รวมการแจ้งเตือนของผู้ใช้ + Staff"""
    if request.user.is_staff:
        notif = Notification.objects.filter(recipient__isnull=True)
    else:
        notif = Notification.objects.filter(recipient=request.user)
    notif.update(is_read=True)
    paginator = Paginator(notif, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'automation/notifications.html', {'page_obj': page_obj})


@require_POST
@login_required
def mark_notifications_read(request):
    """ทำเครื่องหมายการแจ้งเตือนทั้งหมดว่า อ่านแล้ว"""
    if request.user.is_staff:
        Notification.objects.filter(recipient__isnull=True).update(is_read=True)
    else:
        Notification.objects.filter(recipient=request.user).update(is_read=True)
    next_url = request.POST.get('next') or request.GET.get('next') or 'notifications_center'
    if url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect('notifications_center')


@login_required
def notification_redirect(request, pk):
    """กดแจ้งเตือน → ทำเครื่องหมายอ่าน แล้วไปยังลิงก์ของข้อความนั้น"""
    n = get_object_or_404(Notification, pk=pk)
    # รับรองว่าเป็นของเขาจริง
    if n.recipient is None and not request.user.is_staff:
        messages.error(request, 'ไม่สามารถเข้าถึงการแจ้งเตือนนี้ได้')
        return redirect('notifications_center')
    if n.recipient and n.recipient != request.user:
        messages.error(request, 'ไม่สามารถเข้าถึงการแจ้งเตือนนี้ได้')
        return redirect('notifications_center')
    n.is_read = True
    n.save(update_fields=['is_read'])
    if n.link and url_has_allowed_host_and_scheme(n.link, allowed_hosts={request.get_host()}):
        return redirect(n.link)
    return redirect('notifications_center')

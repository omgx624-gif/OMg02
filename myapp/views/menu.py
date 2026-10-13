"""เมนูอาหาร / หมวดหมู่ / Add-on (CRUD สำหรับ Staff)"""

from ._common import *  # noqa: F403


def menu_list(request):
    """Read: แสดงรายการเมนู พร้อมค้นหา กรองหมวดหมู่ และแบ่งหน้า"""
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '')

    menus = MenuItem.objects.all()
    if query:
        menus = menus.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
    if category:
        menus = menus.filter(category=category)

    paginator = Paginator(menus, 6)  # แบ่งหน้าละ 6 รายการ
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'query': query,
        'selected_category': category,
        'total_results': paginator.count,
        'category_choices': MenuItem.CATEGORY_CHOICES,
    }
    return render(request, 'menu/menu_list.html', context)


def menu_detail(request, pk):
    """Read: แสดงรายละเอียดเมนูเดียว พร้อมเมนูแนะนำใกล้เคียง + รีวิว/คะแนนเฉลี่ย"""
    from django.db.models import Avg

    menu = get_object_or_404(MenuItem, pk=pk)
    related_menus = MenuItem.objects.filter(
        category=menu.category
    ).exclude(pk=menu.pk).order_by('?')[:3]
    reviews = menu.reviews.select_related('user').all()
    avg_data = reviews.aggregate(avg=Avg('rating'), total=Count('pk'))
    user_review = None
    if request.user.is_authenticated:
        user_review = reviews.filter(user=request.user).first()
    context = {
        'menu': menu,
        'related_menus': related_menus,
        'reviews': reviews,
        'avg_rating': avg_data['avg'],
        'review_count': avg_data['total'] or 0,
        'user_review': user_review,
    }
    return render(request, 'menu/menu_detail.html', context)


@staff_required
def menu_create(request):
    """Create: เพิ่มเมนูใหม่"""
    if request.method == 'POST':
        form = MenuItemForm(request.POST, request.FILES)
        if form.is_valid():
            menu = form.save()
            messages.success(request, f'เพิ่มเมนู "{menu.name}" เรียบร้อยแล้ว')
            return redirect('menu_list')
        messages.error(request, 'กรุณาตรวจสอบข้อมูลที่กรอกให้ถูกต้อง')
    else:
        form = MenuItemForm()
    return render(request, 'menu/menu_form.html', {'form': form, 'title': 'เพิ่มเมนูใหม่'})


@staff_required
def menu_update(request, pk):
    """Update: แก้ไขเมนู"""
    menu = get_object_or_404(MenuItem, pk=pk)
    if request.method == 'POST':
        form = MenuItemForm(request.POST, request.FILES, instance=menu)
        if form.is_valid():
            form.save()
            messages.success(request, f'แก้ไขเมนู "{menu.name}" เรียบร้อยแล้ว')
            return redirect('menu_list')
        messages.error(request, 'กรุณาตรวจสอบข้อมูลที่กรอกให้ถูกต้อง')
    else:
        form = MenuItemForm(instance=menu)
    return render(request, 'menu/menu_form.html', {'form': form, 'title': f'แก้ไขเมนู: {menu.name}'})


@staff_required
def menu_delete(request, pk):
    """Delete: ลบเมนู (มีหน้ายืนยันก่อนลบ)"""
    menu = get_object_or_404(MenuItem, pk=pk)
    if request.method == 'POST':
        name = menu.name
        menu.delete()
        messages.warning(request, f'ลบเมนู "{name}" เรียบร้อยแล้ว')
        return redirect('menu_list')
    return render(request, 'menu/menu_confirm_delete.html', {'menu': menu})


@staff_required
def category_list(request):
    """รายชื่อหมวดหมู่ทั้งหมด"""
    categories = Category.objects.all()
    context = {'categories': categories}
    return render(request, 'category/category_list.html', context)


@staff_required
def category_create(request):
    """Create: เพิ่มหมวดหมู่ใหม่"""
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'เพิ่มหมวดหมู่ "{category.name}" เรียบร้อยแล้ว')
            return redirect('category_list')
        messages.error(request, 'กรุณาตรวจสอบข้อมูลที่กรอกให้ถูกต้อง')
    else:
        form = CategoryForm()
    return render(request, 'category/category_form.html', {'form': form, 'title': 'เพิ่มหมวดหมู่ใหม่'})


@staff_required
def category_update(request, pk):
    """Update: แก้ไขหมวดหมู่"""
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f'แก้ไขหมวดหมู่ "{category.name}" เรียบร้อยแล้ว')
            return redirect('category_list')
        messages.error(request, 'กรุณาตรวจสอบข้อมูลที่กรอกให้ถูกต้อง')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'category/category_form.html', {'form': form, 'title': f'แก้ไขหมวดหมู่: {category.name}'})


@staff_required
def category_delete(request, pk):
    """Delete: ลบหมวดหมู่ (มีหน้ายืนยันก่อนลบ)"""
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        name = category.name
        category.delete()
        messages.warning(request, f'ลบหมวดหมู่ "{name}" เรียบร้อยแล้ว')
        return redirect('category_list')
    return render(request, 'category/category_confirm_delete.html', {'category': category})


@staff_required
def addon_list(request):
    """รายการเครื่องเคียงทั้งหมด"""
    addons = AddOn.objects.all()
    context = {'addons': addons}
    return render(request, 'addon/addon_list.html', context)


@staff_required
def addon_create(request):
    """Create: เพิ่มเครื่องเคียงใหม่"""
    if request.method == 'POST':
        form = AddOnForm(request.POST)
        if form.is_valid():
            addon = form.save()
            messages.success(request, f'เพิ่มเครื่องเคียง "{addon.name}" เรียบร้อยแล้ว')
            return redirect('addon_list')
        messages.error(request, 'กรุณาตรวจสอบข้อมูลที่กรอกให้ถูกต้อง')
    else:
        form = AddOnForm()
    return render(request, 'addon/addon_form.html', {'form': form, 'title': 'เพิ่มเครื่องเคียงใหม่'})


@staff_required
def addon_update(request, pk):
    """Update: แก้ไขเครื่องเคียง"""
    addon = get_object_or_404(AddOn, pk=pk)
    if request.method == 'POST':
        form = AddOnForm(request.POST, instance=addon)
        if form.is_valid():
            form.save()
            messages.success(request, f'แก้ไขเครื่องเคียง "{addon.name}" เรียบร้อยแล้ว')
            return redirect('addon_list')
        messages.error(request, 'กรุณาตรวจสอบข้อมูลที่กรอกให้ถูกต้อง')
    else:
        form = AddOnForm(instance=addon)
    return render(request, 'addon/addon_form.html', {'form': form, 'title': f'แก้ไขเครื่องเคียง: {addon.name}'})


@staff_required
def addon_delete(request, pk):
    """Delete: ลบเครื่องเคียง (มีหน้ายืนยันก่อนลบ)"""
    addon = get_object_or_404(AddOn, pk=pk)
    if request.method == 'POST':
        name = addon.name
        addon.delete()
        messages.warning(request, f'ลบเครื่องเคียง "{name}" เรียบร้อยแล้ว')
        return redirect('addon_list')
    return render(request, 'addon/addon_confirm_delete.html', {'addon': addon})

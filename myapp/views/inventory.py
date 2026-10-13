"""วัตถุดิบ/สต็อก + สัดส่วนวัตถุดิบในเมนู (Recipe)"""

from ._common import *  # noqa: F403


@staff_required
def inventory_dashboard(request):
    """แดชบอร์ดสต็อก — สรุปคงเหลือ + เตือนของใกล้หมด/หมด"""
    ingredients = list(Ingredient.objects.all())
    low_stock = [i for i in ingredients if i.is_low_stock]
    out_stock = [i for i in ingredients if i.is_out_stock]
    ok_count = len(ingredients) - len(low_stock) - len(out_stock)
    context = {
        'ingredients': ingredients,
        'low_stock': low_stock,
        'out_stock': out_stock,
        'ok_count': ok_count,
        'total_count': len(ingredients),
    }
    return render(request, 'inventory/inventory_dashboard.html', context)


@staff_required
def ingredient_create(request):
    """เพิ่มวัตถุดิบใหม่"""
    if request.method == 'POST':
        form = IngredientForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'เพิ่มวัตถุดิบเรียบร้อยแล้ว')
            return redirect('inventory_dashboard')
        messages.error(request, 'กรุณาตรวจสอบข้อมูลให้ถูกต้อง')
    else:
        form = IngredientForm()
    return render(request, 'inventory/ingredient_form.html', {'form': form, 'title': 'เพิ่มวัตถุดิบ'})


@staff_required
def ingredient_update(request, pk):
    """แก้ไขวัตถุดิบ / รับของเข้าคลัง"""
    ingredient = get_object_or_404(Ingredient, pk=pk)
    if request.method == 'POST':
        form = IngredientForm(request.POST, instance=ingredient)
        if form.is_valid():
            form.save()
            messages.success(request, f'อัปเดต "{ingredient.name}" เรียบร้อยแล้ว')
            return redirect('inventory_dashboard')
        messages.error(request, 'กรุณาตรวจสอบข้อมูลให้ถูกต้อง')
    else:
        form = IngredientForm(instance=ingredient)
    return render(request, 'inventory/ingredient_form.html', {
        'form': form,
        'title': f'แก้ไข {ingredient.name}',
        'ingredient': ingredient,
    })


@staff_required
def ingredient_delete(request, pk):
    """ลบวัตถุดิบ (มีหน้ายืนยัน)"""
    ingredient = get_object_or_404(Ingredient, pk=pk)
    if request.method == 'POST':
        name = ingredient.name
        ingredient.delete()
        messages.warning(request, f'ลบวัตถุดิบ "{name}" เรียบร้อยแล้ว')
        return redirect('inventory_dashboard')
    return render(request, 'inventory/ingredient_confirm_delete.html', {'ingredient': ingredient})


@staff_required
def menu_ingredient_list(request):
    """ตั้งค่าสัดส่วนวัตถุดิบของแต่ละเมนู (Recipe) — ตัดสต็อกอัตโนมัติ"""
    menu = None
    menu_pk = request.GET.get('menu', '')
    if menu_pk.isdigit():
        menu = MenuItem.objects.filter(pk=int(menu_pk)).first()

    recipes = MenuIngredient.objects.select_related('menu', 'ingredient').order_by('menu__name', 'ingredient__name')
    if menu:
        recipes = recipes.filter(menu=menu)

    return render(request, 'inventory/menu_ingredient_list.html', {
        'recipes': recipes,
        'menus': MenuItem.objects.order_by('name'),
        'selected_menu': menu,
    })


@staff_required
def menu_ingredient_create(request):
    """เพิ่มสัดส่วนวัตถุดิบให้เมนู"""
    from ..forms import MenuIngredientForm

    if request.method == 'POST':
        form = MenuIngredientForm(request.POST)
        if form.is_valid():
            recipe = form.save(commit=False)
            # ป้องกันรายการซ้ำ (menu + ingredient) — update แทน insert ถ้าซ้ำ
            existing = MenuIngredient.objects.filter(
                menu=recipe.menu, ingredient=recipe.ingredient
            ).first()
            if existing:
                existing.quantity = recipe.quantity
                existing.save()
                messages.success(request, f'อัปเดตสัดส่วน "{existing}" เรียบร้อยแล้ว')
            else:
                recipe.save()
                messages.success(request, f'เพิ่มสัดส่วน "{recipe}" เรียบร้อยแล้ว')
            return redirect('menu_ingredient_list')
        messages.error(request, 'กรุณาตรวจสอบข้อมูลให้ถูกต้อง')
    else:
        form = MenuIngredientForm()
    return render(request, 'inventory/menu_ingredient_form.html', {'form': form, 'title': 'เพิ่มสัดส่วนวัตถุดิบ'})


@staff_required
def menu_ingredient_update(request, pk):
    """แก้ไขสัดส่วนวัตถุดิบของเมนู"""
    from ..forms import MenuIngredientForm

    recipe = get_object_or_404(MenuIngredient, pk=pk)
    if request.method == 'POST':
        form = MenuIngredientForm(request.POST, instance=recipe)
        if form.is_valid():
            form.save()
            messages.success(request, 'แก้ไขสัดส่วนวัตถุดิบเรียบร้อยแล้ว')
            return redirect('menu_ingredient_list')
        messages.error(request, 'กรุณาตรวจสอบข้อมูลให้ถูกต้อง')
    else:
        form = MenuIngredientForm(instance=recipe)
    return render(request, 'inventory/menu_ingredient_form.html', {'form': form, 'title': 'แก้ไขสัดส่วนวัตถุดิบ', 'recipe': recipe})


@staff_required
def menu_ingredient_delete(request, pk):
    """ลบสัดส่วนวัตถุดิบของเมนู"""
    recipe = get_object_or_404(MenuIngredient, pk=pk)
    if request.method == 'POST':
        recipe.delete()
        messages.warning(request, 'ลบสัดส่วนวัตถุดิบเรียบร้อยแล้ว')
        return redirect('menu_ingredient_list')
    return render(request, 'inventory/menu_ingredient_confirm_delete.html', {'recipe': recipe})

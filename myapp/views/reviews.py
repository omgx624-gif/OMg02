"""รีวิวเมนู: สร้าง/ลบ"""

from ._common import *  # noqa: F403


@login_required
def review_create(request, menu_pk):
    """รีวิว + ให้คะแนนเมนู (เมนูละ 1 ครั้งต่อผู้ใช้ — แก้ไขได้)"""
    from ..services import announce_new_review

    menu = get_object_or_404(MenuItem, pk=menu_pk)
    try:
        existing = Review.objects.get(menu=menu, user=request.user)
    except Review.DoesNotExist:
        existing = None

    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=existing)
        if form.is_valid():
            review = form.save(commit=False)
            review.menu = menu
            review.user = request.user
            review.save()
            if not existing:
                announce_new_review(review)
            messages.success(
                request,
                'บันทึกรีวิวเรียบร้อยแล้ว ขอบคุณสำหรับความคิดเห็น 🙏',
            )
            return redirect('menu_detail', pk=menu.pk)
        messages.error(request, 'กรุณาให้คะแนน 1-5 ดาว')
    else:
        form = ReviewForm(instance=existing)

    return render(request, 'review/review_form.html', {
        'form': form,
        'menu': menu,
        'existing': existing,
    })


@login_required
@require_POST
def review_delete(request, pk):
    """ลบรีวิวของตัวเอง (ต้อง POST เท่านั้น — กัน CSRF ข้ามไซต์ด้วย GET)"""
    review = get_object_or_404(Review, pk=pk, user=request.user)
    menu = review.menu
    review.delete()
    messages.warning(request, 'ลบรีวิวเรียบร้อยแล้ว')
    return redirect('menu_detail', pk=menu.pk)

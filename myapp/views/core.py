"""หน้าทั่วไป + ระบบล็อกอิน/สมัครสมาชิก + error handlers"""

from ._common import *  # noqa: F403
from ._common import _dev_google_user, _google_login_active, _make_captcha


@require_GET
def healthz(request):
    """Health check สำหรับ Docker/load balancer — ตรวจการเชื่อมต่อ DB จริง

    คืน 200 เมื่อใช้งานได้ / 503 เมื่อ DB ใช้การไม่ได้
    (ไม่ต้องล็อกอิน และยกเว้น HTTPS redirect — ดู SECURE_REDIRECT_EXEMPT)
    """
    from django.db import connection
    from django.http import JsonResponse

    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except Exception:
        return JsonResponse({'status': 'error', 'db': 'error'}, status=503)
    return JsonResponse({'status': 'ok', 'db': 'ok'})


@require_GET
def google_login_redirect(request):
    """ทางเข้าล็อกอินด้วย Google
    - ถ้าตั้งค่า Client ID จริง → ส่งต่อไปยัง OAuth ของ Google (allauth)
    - โหมดพัฒนา (DEBUG) ที่ยังไม่มี Client ID → เข้าใช้งานด้วยผู้ใช้ทดสอบได้ทันที
    """
    from django.conf import settings
    from django.urls import reverse

    if settings.GOOGLE_OAUTH_CLIENT_ID and settings.GOOGLE_OAUTH_CLIENT_SECRET:
        from urllib.parse import urlencode
        base = reverse('google_login')
        next_url = request.GET.get('next')
        params = {'process': 'login'}
        if next_url and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            params['next'] = next_url
        return redirect(f'{base}?{urlencode(params)}')

    if not settings.DEBUG:
        messages.error(request, 'ยังไม่ได้ตั้งค่าการล็อกอินด้วย Google กรุณาติดต่อผู้ดูแลระบบ')
        return redirect('login')

    user = _dev_google_user()
    # ระบุ backend ให้ชัดเจน (ระบบมีมากกว่า 1 backend)
    user.backend = 'django.contrib.auth.backends.ModelBackend'
    auth_login(request, user)
    messages.success(request, f'เข้าสู่ระบบด้วย Google เรียบร้อย ยินดีต้อนรับคุณ {user.first_name}')

    next_url = request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect('home')


def robots_txt(request):
    """ไฟล์ robots.txt สำหรับ SEO"""
    content = (
        'User-agent: *\n'
        'Disallow: /admin/\n'
        'Disallow: /api/\n'
        'Disallow: /cart/\n'
        'Allow: /\n'
        f'\nSitemap: {request.build_absolute_uri("/sitemap.xml")}\n'
    )
    return HttpResponse(content, content_type='text/plain')


def custom_404(request, exception):
    """หน้า 404 Not Found"""
    return render(request, 'core/404.html', status=404)


def custom_500(request):
    """หน้า 500 Server Error"""
    return render(request, 'core/500.html', status=500)


def custom_403(request, exception):
    """หน้า 403 Forbidden"""
    return render(request, 'core/403.html', status=403)


def login_view(request):
    """หน้าเข้าสู่ระบบของร้าน"""
    if request.user.is_authenticated:
        return redirect('home')

    # กันการพยายามรหัสผ่านซ้ำ ๆ (brute-force)
    attempted_username = (request.POST.get('username') or '').strip()
    if request.method == 'POST' and too_many_login_attempts(request, attempted_username):
        messages.error(
            request,
            'พยายามเข้าสู่ระบบผิดพลาดหลายครั้งเกินไป ระบบได้ล็อกชั่วคราว '
            'กรุณารอ 15 นาทีแล้วลองใหม่อีกครั้ง',
        )
        return render(request, 'core/auth/login.html', {
            'form': AuthenticationForm(request, data=request.POST),
            'google_configured': _google_login_active(),
        })

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            clear_login_attempts(request, user.username)
            messages.success(request, f'ยินดีต้อนรับคุณ {user.username} เข้าสู่ระบบ')
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect('home')
        record_failed_login(request, attempted_username)
        messages.error(request, 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง')
    else:
        form = AuthenticationForm()

    return render(request, 'core/auth/login.html', {
        'form': form,
        'google_configured': _google_login_active(),
    })


def logout_view(request):
    """ออกจากระบบ"""
    auth_logout(request)
    messages.info(request, 'ออกจากระบบเรียบร้อยแล้ว แล้วพบกันใหม่!')
    return redirect('login')


@rate_limit('register', 5, 3600, key_parts=lambda r: (get_client_ip(r),),
            message='คุณลงทะเบียนบ่อยเกินไป กรุณารอ 1 ชั่วโมงแล้วลองใหม่อีกครั้ง')
def register_view(request):
    """สมัครสมาชิกสำหรับผู้ใช้ทั่วไป — ไม่สามารถเลือกเป็นผู้ดูแล (Staff) ได้
    ต้องตอบแคปต์ชา และบัญชีใหม่ต้องรอผู้ดูแลอนุมัติก่อนใช้งาน
    """
    if request.user.is_authenticated:
        return redirect('home')
    if not request.session.get('register_captcha'):
        request.session['register_captcha'] = _make_captcha()

    if request.method == 'POST':
        form = UserRegisterForm(request.POST, request.FILES)
        form.captcha_data = request.session.get('register_captcha')
        if form.is_valid():
            user = form.save()
            request.session.pop('register_captcha', None)
            messages.success(
                request,
                f'ลงทะเบียนสำเร็จ คุณ {user.username} '
                f'บัญชีของคุณต้องรอให้ผู้ดูแลระบบอนุมัติก่อน จึงจะเข้าสู่ระบบได้',
            )
            return redirect('login')
        messages.error(request, 'กรุณาตรวจสอบข้อมูลที่กรอกให้ถูกต้อง (รวมถึงคำตอบแคปต์ชา)')
        request.session['register_captcha'] = _make_captcha()
    else:
        form = UserRegisterForm()

    captcha = request.session.get('register_captcha', {})
    return render(request, 'core/auth/register.html', {
        'form': form,
        'captcha_question': captcha.get('question', ''),
        'google_configured': _google_login_active(),
    })


def home(request):
    featured = MenuItem.objects.filter(available=True).order_by('-date_added')[:3]
    context = {
        'total_menus': MenuItem.objects.filter(available=True).count(),
        'new_menus': featured,
        'home_image': HomeImage.get_setting(),
    }
    return render(request, 'core/home.html', context)


def contact(request):
    store = StoreLocation.get_setting()
    return render(request, 'core/contact.html', {'store': store})


def education(request):
    return render(request, 'core/education.html')

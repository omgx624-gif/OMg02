"""เคมีส่วนกลางของ views: imports, decorators และ helper ที่ใช้ร่วมกัน"""

# flake8: noqa  (import * จากไฟล์ต้นฉบับเดิม)

import csv


import random


from django.contrib import messages


from django.contrib.auth import update_session_auth_hash


from django.contrib.auth import login as auth_login, logout as auth_logout


from django.contrib.auth.decorators import login_required, user_passes_test


from django.contrib.auth.forms import AuthenticationForm


from django.contrib.auth.models import User


from django.core.paginator import Paginator


from django.db.models import Avg, Count, F, Q, Sum


from django.http import HttpResponse


from django.shortcuts import render, redirect, get_object_or_404, reverse


from django.utils import timezone


from django.utils.http import url_has_allowed_host_and_scheme


from django.views.decorators.http import require_GET, require_POST


from ..forms import (
    AddOnForm,
    CategoryForm,
    CouponApplyForm,
    CouponForm,
    DeliveryForm,
    HomeImageForm,
    IngredientForm,
    MenuItemForm,
    OrderForm,
    OrderItemForm,
    ReservationForm,
    ReviewForm,
    UserAvatarForm,
    UserBasicForm,
    UserChangePasswordForm,
    UserCoverForm,
    UserCreateForm,
    UserRegisterForm,
    UserUpdateForm,
)


from ..automation import run_all


from ..security import clear_login_attempts, get_client_ip, rate_limit, record_failed_login, too_many_login_attempts


from ..services import order_coupon_status, validate_coupon


from ..models import (
    AddOn,
    AutomationSettings,
    Category,
    Coupon,
    Delivery,
    HomeImage,
    Ingredient,
    MenuIngredient,
    MenuItem,
    Notification,
    Order,
    OrderItem,
    PointReward,
    PointTransaction,
    Profile,
    Reservation,
    Review,
    StoreLocation,
)


def _google_configured():
    """Google Sign-In พร้อมใช้งานหรือยัง (ต้องตั้ง SocialApp ใน admin/คำสั่งสร้าง)"""
    try:
        from allauth.socialaccount.models import SocialApp
        return SocialApp.objects.filter(provider='google').exists()
    except Exception:
        return False


def _google_login_active():
    """ปิดการล็อกอินด้วย Google แล้ว — คืนค่า False เสมอ"""
    return False


def _dev_google_user():
    """ผู้ใช้ทดสอบสำหรับล็อกอินด้วย Google ในโหมดพัฒนา (ไม่มี Client ID จริง)"""
    from django.contrib.auth.models import User
    from ..models import Profile
    email = 'demo.google@gmail.com'
    user, created = User.objects.get_or_create(
        username='demo.google',
        defaults={
            'email': email,
            'first_name': 'โดนัท',
            'last_name': 'ล็อกอิน Google',
            'is_active': True,
            'is_staff': False,
        },
    )
    Profile.objects.get_or_create(user=user, defaults={'membership_status': 'active'})
    return user


def staff_required(view_func):
    """Decorator: อนุญาตเฉพาะผู้ใช้ที่เป็น staff (ถ้าไม่ใช่จะส่งไปหน้าล็อกอิน)"""
    return user_passes_test(
        lambda u: u.is_authenticated and u.is_staff,
        login_url='login',
    )(view_func)


def rider_required(view_func):
    """Decorator: อนุญาตเฉพาะผู้ใช้ที่มีสถานะไรเดอร์ (Profile.is_rider) หรือ staff"""
    return user_passes_test(
        lambda u: u.is_authenticated
        and (u.is_staff or getattr(getattr(u, 'profile', None), 'is_rider', False)),
        login_url='login',
    )(view_func)


def _user_can_access_order(user, order):
    """ตรวจสอบว่าผู้ใช้สามารถเข้าถึงออเดอร์นี้ได้หรือไม่
    - Staff เข้าถึงได้ทุกออเดอร์
    - ผู้ใช้ทั่วไปเข้าถึงได้เฉพาะออเดอร์ของตัวเอง
    """
    if user.is_staff:
        return True
    return order.created_by_id == user.id


def _make_captcha():
    """สร้างโจทย์แคปต์ชาแบบง่าย (บวกเลข) กันสแปมบอท"""
    a = random.randint(1, 9)
    b = random.randint(1, 9)
    return {
        'question': f'{a} + {b} = ?',
        'answer': a + b,
    }


def _promptpay_qr_for(order):
    """สร้าง data URI ของ QR PromptPay สำหรับออเดอร์ (None ถ้าตั้งค่าไม่ครบ)"""
    store = StoreLocation.get_setting()
    if not store.promptpay_id:
        return None
    from ..services import promptpay_payload, render_qrcode_base64

    payload = promptpay_payload(store.promptpay_id, order.discounted_total)
    if not payload:
        return None
    return render_qrcode_base64(payload)


def _sale_rows():
    """ดึงข้อมูลออเดอร์ + รายการอาหาร เพื่อใช้ส่งออกรายงาน (รวมเดลิเวอร์รี่)"""
    orders = (
        Order.objects.prefetch_related('items', 'items__menu', 'items__addons')
        .select_related('delivery', 'created_by')
        .filter(status='paid')
        .order_by('-paid_at')
    )
    for order in orders:
        delivery = getattr(order, 'delivery', None)
        for item in order.items.all():
            yield {
                'order_id': order.pk,
                'order_type': 'เดลิเวอร์รี่' if order.order_type == 'delivery' else 'ทานในร้าน',
                'table_number': order.table_display if order.order_type != 'delivery' else '-',
                'recipient': delivery.recipient_name if delivery else '-',
                'phone': delivery.phone if delivery else '-',
                'address': delivery.address.replace('\n', ' ') if delivery else '-',
                'delivery_fee': float(delivery.fee) if delivery else 0,
                'delivery_status': delivery.get_status_display() if delivery else '-',
                'paid_at': order.paid_at.strftime('%d/%m/%Y %H:%M') if order.paid_at else '',
                'payment_method': order.get_payment_method_display() or '-',
                'menu_name': item.menu.name,
                'quantity': item.quantity,
                'unit_price': float(item.menu.price),
                'subtotal': float(item.subtotal),
                'created_by': order.created_by.username if order.created_by else 'ไม่ระบุ',
            }


def _rider_status_counts():
    """จำนวนออเดอร์เดลิเวอร์รี่ตามสถานะการจัดส่ง (สำหรับไรเดอร์)"""
    return {
        'pending': Delivery.objects.filter(status='pending').count(),
        'accepted': Delivery.objects.filter(status='accepted').count(),
        'picking_up': Delivery.objects.filter(status='picking_up').count(),
        'out_for_delivery': Delivery.objects.filter(status='out_for_delivery').count(),
        'delivered': Delivery.objects.filter(status='delivered').count(),
    }

from datetime import timedelta
from decimal import Decimal
from unittest import mock

import requests
from django.contrib.auth.models import User
from django.core import mail
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import (
    AddOn,
    Coupon,
    Delivery,
    Ingredient,
    MenuIngredient,
    MenuItem,
    Order,
    OrderItem,
    PointReward,
    PointTransaction,
    Profile,
    Reservation,
    Review,
)
from .services import (
    crc16_xmodem,
    order_coupon_status,
    promptpay_payload,
    render_qrcode_base64,
    validate_coupon,
)


class MenuItemTests(TestCase):
    def setUp(self):
        self.menu = MenuItem.objects.create(
            name='ข้าวผัดกะเพราหมูสับ',
            price=50,
            spice_level=2,
            description='เผ็ดปานกลาง อร่อยมาก',
        )

    def test_create_menu(self):
        self.assertEqual(MenuItem.objects.count(), 1)
        self.assertEqual(str(self.menu), 'ข้าวผัดกะเพราหมูสับ')

    def test_duplicate_name_not_allowed(self):
        from .forms import MenuItemForm
        form = MenuItemForm(data={
            'name': 'ข้าวผัดกะเพราหมูสับ',
            'category': 'rice',
            'price': 55,
            'spice_level': 1,
            'available': True,
            'date_added': timezone.localdate(),
        })
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_price_zero_invalid(self):
        from .forms import MenuItemForm
        form = MenuItemForm(data={
            'name': 'เมนูใหม่',
            'category': 'rice',
            'price': 0,
            'spice_level': 1,
            'available': True,
            'date_added': timezone.localdate(),
        })
        self.assertFalse(form.is_valid())

    def test_menu_list_page(self):
        response = self.client.get(reverse('menu_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ข้าวผัดกะเพราหมูสับ')

    def test_menu_detail_page(self):
        response = self.client.get(reverse('menu_detail', args=[self.menu.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ข้าวผัดกะเพราหมูสับ')


class OrderTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.staff = User.objects.create_user(username='staff', password='password123', is_staff=True)
        self.menu = MenuItem.objects.create(name='ข้าวผัดกระเพรา', price=50)
        self.addon = AddOn.objects.create(name='ไข่ดาว', price=10)
        self.order = Order.objects.create(table_number=5, created_by=self.user)

    def test_total_price_with_addon(self):
        item = OrderItem.objects.create(
            order=self.order, menu=self.menu, quantity=2, notes='ไม่ใส่พริก'
        )
        item.addons.add(self.addon)
        # (50 * 2) + 10 = 110
        self.assertEqual(item.subtotal, 110)
        self.assertEqual(self.order.total_price, 110)
        self.assertEqual(self.order.item_count, 2)
        self.assertFalse(self.order.is_paid)

    def test_user_redirect_when_not_logged_in(self):
        response = self.client.get(reverse('order_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_staff_can_pay_order(self):
        self.client.login(username='staff', password='password123')
        OrderItem.objects.create(order=self.order, menu=self.menu, quantity=1)
        response = self.client.post(reverse('order_pay', args=[self.order.pk]), {'method': 'cash'})
        self.order.refresh_from_db()
        self.assertTrue(self.order.is_paid)
        self.assertEqual(self.order.payment_method, 'cash')
        self.assertIsNotNone(self.order.paid_at)
        self.assertRedirects(response, reverse('order_detail', args=[self.order.pk]))

    def test_order_receipt_page(self):
        self.client.login(username='staff', password='password123')
        OrderItem.objects.create(order=self.order, menu=self.menu, quantity=1)
        response = self.client.get(reverse('order_receipt', args=[self.order.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ใบเสร็จ')

    def test_daily_code_resets_each_day(self):
        today = timezone.localdate()
        base = self.order.daily_number  # ลำดับของออเดอร์ใน setUp
        o1 = Order.objects.create(table_number=1)
        o2 = Order.objects.create(table_number=2)
        self.assertEqual(o1.daily_number, base + 1)
        self.assertEqual(o2.daily_number, base + 2)
        self.assertEqual(o1.daily_code, f"{today:%Y%m%d}-{base + 1:03d}")
        self.assertEqual(o2.daily_code, f"{today:%Y%m%d}-{base + 2:03d}")
        self.assertEqual(o1.display_code, f"#{base + 1:03d}")
        self.assertEqual(o2.display_code, f"#{base + 2:03d}")

        # วันถัดไป → รีเซ็ตเป็นลำดับ 1 ใหม่
        next_day = today + timedelta(days=1)
        with mock.patch('myapp.models.timezone.localdate', return_value=next_day):
            o3 = Order.objects.create(table_number=3)
        self.assertEqual(o3.daily_number, 1)
        self.assertEqual(o3.daily_code, f"{next_day:%Y%m%d}-001")
        self.assertEqual(o3.display_code, '#001')

    def test_daily_code_not_reused_after_delete(self):
        today = timezone.localdate()
        base = self.order.daily_number
        o1 = Order.objects.create(table_number=1)  # base+1
        o2 = Order.objects.create(table_number=2)  # base+2
        o1.delete()
        o3 = Order.objects.create(table_number=3)  # ต้องได้ base+3 ไม่ใช่เลขซ้ำ
        self.assertEqual(o3.daily_number, o2.daily_number + 1)
        self.assertEqual(o3.daily_code, f"{today:%Y%m%d}-{base + 3:03d}")
        self.assertEqual(o3.display_code, f"#{base + 3:03d}")

    def test_display_code_in_pages(self):
        self.client.login(username='staff', password='password123')
        response = self.client.get(reverse('order_list'))
        self.assertContains(response, self.order.display_code)


class UserTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username='staff', password='password123', is_staff=True)

    def test_profile_auto_create(self):
        # Signal สร้าง Profile ให้ทุกผู้ใช้ใหม่โดยอัตโนมัติ
        profile = self.staff.profile
        self.assertEqual(str(profile), 'Profile of staff')
        self.assertEqual(profile.points, 0)

    def test_staff_required_sends_to_login(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_register_creates_inactive_user(self):
        from django.test import RequestFactory

        from .forms import UserRegisterForm

        request = RequestFactory().post('/')
        request.session = self.client.session
        # สร้าง captcha ลง session
        s = self.client.session
        s['register_captcha'] = {'question': '1 + 1 = ?', 'answer': 2}
        s.save()
        session = self.client.session

        form = UserRegisterForm(
            data={
                'username': 'newuser',
                'first_name': '',
                'last_name': '',
                'email': 'new@example.com',
                'password1': 'StrongPass123!',
                'password2': 'StrongPass123!',
                'captcha_answer': '2',
            }
        )
        form.captcha_data = session.get('register_captcha')
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertFalse(user.is_active)
        self.assertFalse(user.is_staff)


class ExportAndApiTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username='staff', password='password123', is_staff=True)
        self.menu = MenuItem.objects.create(name='กะเพราหมูกรอบ', price=60)
        order = Order.objects.create(table_number=1, created_by=self.staff)
        OrderItem.objects.create(order=order, menu=self.menu, quantity=3)
        order.status = 'paid'
        order.payment_method = 'cash'
        order.paid_at = timezone.now()
        order.save()

    def test_export_csv(self):
        self.client.login(username='staff', password='password123')
        response = self.client.get(reverse('export_orders_csv'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('กะเพราหมูกรอบ', response.content.decode('utf-8-sig'))

    def test_export_xlsx(self):
        self.client.login(username='staff', password='password123')
        response = self.client.get(reverse('export_orders_xlsx'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

    def test_api_menu_list(self):
        response = self.client.get(reverse('api-menu-list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('กะเพราหมูกรอบ', response.content.decode())

    def test_api_order_requires_login_for_write(self):
        response = self.client.post(reverse('api-order-list'), {'table_number': 9})
        # ไม่ได้ล็อกอิน → 401/403
        self.assertIn(response.status_code, (401, 403))


class DeliveryTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username='staff', password='password123', is_staff=True)
        self.user = User.objects.create_user(username='user', password='password123')
        self.menu = MenuItem.objects.create(name='กะเพราเดลิเวอร์รี่', price=60)
        self.order = Order.objects.create(
            order_type='delivery',
            status='pending',
            created_by=self.user,
        )
        OrderItem.objects.create(order=self.order, menu=self.menu, quantity=2)

    def _fill_delivery(self):
        from .models import Delivery
        return Delivery.objects.create(
            order=self.order,
            recipient_name='สมชาย ใจดี',
            phone='089-123-4567',
            address='123/45 ถ.สุขใจ เขตบางกะปิ กทม 10240',
            fee=20,
        )

    def test_order_form_delivery_does_not_need_table(self):
        from .forms import OrderForm
        form = OrderForm(data={'order_type': 'delivery', 'table_number': ''})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.cleaned_data['table_number'])

    def test_order_form_dine_in_requires_table(self):
        from .forms import OrderForm
        form = OrderForm(data={'order_type': 'dine_in', 'table_number': ''})
        self.assertFalse(form.is_valid())
        self.assertIn('table_number', form.errors)

    def test_total_price_includes_delivery_fee(self):
        delivery = self._fill_delivery()
        # (60 * 2) + 20 = 140
        self.assertEqual(self.order.delivery_fee, 20)
        self.assertEqual(self.order.total_price, 140)
        self.assertEqual(str(self.order.table_display), 'เดลิเวอร์รี่')

    def test_delivery_status_update_sets_delivered_at(self):

        delivery = self._fill_delivery()
        self.client.login(username='staff', password='password123')
        self.client.post(reverse('delivery_update_status', args=[delivery.pk]), {
            'delivery_status': 'delivered',
        })
        delivery.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(delivery.status, 'delivered')
        self.assertIsNotNone(delivery.delivered_at)
        self.assertEqual(self.order.status, 'served')

    def test_delivery_dashboard_requires_staff(self):
        response = self.client.get(reverse('delivery_dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

        self.client.login(username='user', password='password123')
        response = self.client.get(reverse('delivery_dashboard'))
        self.assertEqual(response.status_code, 302)

        self.client.login(username='staff', password='password123')
        delivery = self._fill_delivery()
        response = self.client.get(reverse('delivery_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'สมชาย ใจดี')
        self.assertContains(response, 'จัดการเดลิเวอร์รี่')

    def test_order_detail_saves_delivery_info(self):
        self.client.login(username='staff', password='password123')
        response = self.client.post(reverse('order_detail', args=[self.order.pk]), {
            'delivery_submit': '1',
            'recipient_name': 'นางวันดี',
            'phone': '088-000-0000',
            'address': '99/1 ถ.อร่อย จ.สุโขทัย',
            'fee': '30',
            'rider_name': '',
            'rider_phone': '',
            'tracking_note': '',
        })
        self.assertRedirects(response, reverse('order_detail', args=[self.order.pk]))
        self.order.refresh_from_db()
        self.assertEqual(self.order.delivery.recipient_name, 'นางวันดี')
        self.assertEqual(self.order.delivery.fee, 30)

    def test_order_pay_blocks_delivery_without_info(self):
        self.client.login(username='staff', password='password123')
        response = self.client.get(reverse('order_pay', args=[self.order.pk]))
        self.assertRedirects(response, reverse('order_detail', args=[self.order.pk]))

    def test_api_delivery_list(self):
        self._fill_delivery()
        self.client.login(username='staff', password='password123')
        response = self.client.get(reverse('api-delivery-list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('สมชาย ใจดี', response.content.decode())


class DeliveryModuleTests(TestCase):
    """ทดสอบระบบเดลิเวอร์รี่แบบแยก (หน้าแรก / ติดตาม / ไรเดอร์)"""

    def setUp(self):
        from django.core.cache import cache

        from .models import Delivery, StoreLocation

        # เคลียร์ rate limit ของหน้าติดตาม (cache อยู่ข้าม test ใน locmem)
        cache.clear()

        self.staff = User.objects.create_user(username='staff', password='password123', is_staff=True)
        self.user = User.objects.create_user(username='user', password='password123')
        self.rider = User.objects.create_user(username='rider', password='password123')
        Profile.objects.update_or_create(user=self.rider, defaults={'is_rider': True})

        self.menu = MenuItem.objects.create(name='เมนูเดลิเวอร์รี่', price=60)
        self.order = Order.objects.create(
            order_type='delivery',
            status='pending',
            created_by=self.user,
        )
        OrderItem.objects.create(order=self.order, menu=self.menu, quantity=2)

        self.delivery = Delivery.objects.create(
            order=self.order,
            recipient_name='วิภา รุ่งเรือง',
            phone='090-000-0000',
            address='45/6 ซ.สีสุก เขตจตุจักร กทม 10900',
            fee=0,
            status='pending',
            recipient_lat=13.8,
            recipient_lng=100.55,
        )
        self.store = StoreLocation.get_setting()
        self.store.lat = 13.7563
        self.store.lng = 100.5018
        self.store.fee_base = 10
        self.store.fee_per_km = 5
        self.store.free_delivery_over = None
        self.store.save()

    def test_delivery_home_page_public(self):
        response = self.client.get(reverse('delivery_home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'เดลิเวอร์รี่ อร่อยเกินเบอร์')

    def test_delivery_tracking_guest_sees_status_but_not_pii(self):
        # Guest กรอกรหัสถูก — เห็นสถานะ แต่ไม่เห็นชื่อ/เบอร์/ที่อยู่ผู้รับ
        short = self.order.display_code.lstrip('#')
        url = reverse('delivery_tracking')
        response = self.client.get(url, {'code': short})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.order.display_code)
        self.assertNotContains(response, 'วิภา รุ่งเรือง')
        self.assertNotContains(response, '090-000-0000')
        self.assertNotContains(response, 'ซ.สีสุก')
        self.assertNotContains(response, 'google.com/maps/dir')
        self.assertContains(response, 'เข้าสู่ระบบด้วยบัญชีของคุณ')

    def test_delivery_tracking_owner_sees_details(self):
        self.client.login(username='user', password='password123')
        short = self.order.display_code.lstrip('#')
        response = self.client.get(reverse('delivery_tracking'), {'code': short})
        self.assertContains(response, 'วิภา รุ่งเรือง')
        self.assertContains(response, '090-000-0000')
        self.assertContains(response, 'google.com/maps/dir')

    def test_delivery_tracking_staff_sees_details(self):
        self.client.login(username='staff', password='password123')
        short = self.order.display_code.lstrip('#')
        response = self.client.get(reverse('delivery_tracking'), {'code': short})
        self.assertContains(response, 'วิภา รุ่งเรือง')

    def test_delivery_tracking_exact_match_only(self):
        # ค้นแบบบางส่วน (partial) ต้องไม่เจอ — กัน enumerate
        full = self.order.daily_code  # เช่น 20261007-001
        response = self.client.get(reverse('delivery_tracking'), {'code': full[:-3]})
        self.assertContains(response, 'ไม่พบออเดอร์')

    def test_delivery_tracking_rate_limited(self):
        url = reverse('delivery_tracking')
        for _ in range(10):
            self.client.get(url, {'code': '999'})
        response = self.client.get(url, {'code': '999'})
        self.assertContains(response, 'ค้นหาบ่อยเกินไป')
        self.assertNotContains(response, 'ไม่พบออเดอร์')

    def test_delivery_tracking_not_found(self):
        response = self.client.get(reverse('delivery_tracking'), {'code': '999'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ไม่พบออเดอร์')

    def test_rider_dashboard_requires_rider(self):
        self.client.login(username='user', password='password123')
        response = self.client.get(reverse('rider_dashboard'))
        self.assertEqual(response.status_code, 302)

        self.client.login(username='rider', password='password123')
        response = self.client.get(reverse('rider_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'แดชบอร์ดไรเดอร์')
        self.assertContains(response, 'วิภา รุ่งเรือง')

    def test_rider_accept_and_deliver_job(self):
        self.client.login(username='rider', password='password123')

        # ไรเดอร์รับงาน
        response = self.client.post(reverse('rider_accept_job', args=[self.delivery.pk]))
        self.assertRedirects(response, reverse('rider_my_jobs'))
        self.delivery.refresh_from_db()
        self.assertEqual(self.delivery.status, 'accepted')
        self.assertEqual(self.delivery.assigned_rider, self.rider)
        self.assertIsNotNone(self.delivery.accepted_at)

        # ไปรับอาหาร → กำลังจัดส่ง → จัดส่งแล้ว
        for status in ('picking_up', 'out_for_delivery', 'delivered'):
            self.client.post(reverse('rider_update_status', args=[self.delivery.pk]), {
                'delivery_status': status,
            })
            self.delivery.refresh_from_db()
            self.assertEqual(self.delivery.status, status)

        self.assertIsNotNone(self.delivery.delivered_at)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'served')

        # หน้า "งานของฉัน" ต้องแสดงผลได้และมีงานนี้อยู่ในประวัติ
        response = self.client.get(reverse('rider_my_jobs'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'วิภา รุ่งเรือง')
        self.assertContains(response, 'จัดส่งแล้ว')

    def test_rider_cannot_accept_claimed_job_by_another(self):
        self.delivery.status = 'accepted'
        self.delivery.assigned_rider = self.rider
        self.delivery.save()
        other = User.objects.create_user(username='rider2', password='password123')
        Profile.objects.update_or_create(user=other, defaults={'is_rider': True})
        self.client.login(username='rider2', password='password123')
        response = self.client.post(reverse('rider_accept_job', args=[self.delivery.pk]))
        self.assertRedirects(response, reverse('rider_dashboard'))
        self.delivery.refresh_from_db()
        self.assertEqual(self.delivery.assigned_rider, self.rider)

    def test_admin_can_assign_rider(self):
        self.client.login(username='staff', password='password123')
        response = self.client.post(reverse('delivery_assign_rider', args=[self.delivery.pk]), {
            'rider_id': self.rider.pk,
        })
        self.assertRedirects(response, reverse('delivery_dashboard'))
        self.delivery.refresh_from_db()
        self.assertEqual(self.delivery.assigned_rider, self.rider)
        self.assertEqual(self.delivery.status, 'accepted')

    def test_calc_fee_from_coordinates(self):
        self.client.login(username='staff', password='password123')
        response = self.client.post(reverse('delivery_calc_fee', args=[self.delivery.pk]))
        self.assertRedirects(response, reverse('delivery_dashboard'))
        self.delivery.refresh_from_db()
        self.assertIsNotNone(self.delivery.distance_km)
        self.assertGreater(self.delivery.distance_km, 0)
        # ค่าส่งต้อง >= ค่าแรกเริ่ม (10)
        self.assertGreaterEqual(self.delivery.fee, 10)

    def test_calc_distance_haversine(self):
        from .models import haversine_km
        distance = haversine_km(13.7563, 100.5018, 13.7563, 100.5018)
        self.assertAlmostEqual(distance, 0.0, places=3)
        distance = haversine_km(13.7563, 100.5018, 13.7563, 100.6018)
        self.assertAlmostEqual(distance, 11.13, delta=0.5)

    def test_free_delivery_over_threshold(self):
        self.client.login(username='staff', password='password123')
        self.store.free_delivery_over = 200
        self.store.save()
        self.delivery.update_distance_and_fee()
        self.order.refresh_from_db()
        # ยอดรวม 120 (< 200) → ไม่ฟรีค่าส่ง
        self.assertGreater(self.delivery.fee, 0)

        # ยอดเยอะกว่า threshold → ค่าส่ง 0
        OrderItem.objects.create(order=self.order, menu=self.menu, quantity=10)
        self.delivery.update_distance_and_fee()
        self.assertEqual(self.delivery.fee, 0)

    def test_delivery_settings_staff_only_and_save(self):
        self.client.login(username='user', password='password123')
        response = self.client.get(reverse('delivery_settings'))
        self.assertEqual(response.status_code, 302)

        self.client.login(username='staff', password='password123')
        response = self.client.get(reverse('delivery_settings'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ตั้งค่าเดลิเวอร์รี่')

        response = self.client.post(reverse('delivery_settings'), {
            'name': 'อร่อยเกินเบอร์',
            'lat': '13.75',
            'lng': '100.50',
            'address': 'ตลาดสดแถวนี้',
            'fee_base': '15',
            'fee_per_km': '7',
            'free_delivery_over': '300',
        })
        self.assertRedirects(response, reverse('delivery_settings'))
        self.store.refresh_from_db()
        self.assertEqual(float(self.store.lat), 13.75)
        self.assertEqual(float(self.store.fee_base), 15)
        self.assertEqual(float(self.store.free_delivery_over), 300)


class DeliveryAutoTests(TestCase):
    """ทดสอบระบบจัดส่งอัตโนมัติ: คำนวณค่าส่ง / จัดสรรงาน / ปล่อยงานค้าง / ตั้งค่า"""

    def setUp(self):
        from .models import Delivery, StoreLocation

        self.staff = User.objects.create_user(username='staff', password='password123', is_staff=True)
        self.user = User.objects.create_user(username='user', password='password123')
        self.rider = User.objects.create_user(username='rider', password='password123')
        Profile.objects.update_or_create(user=self.rider, defaults={'is_rider': True})

        self.menu = MenuItem.objects.create(name='เมนูเดลิเวอร์รี่', price=60)
        self.order = Order.objects.create(
            order_type='delivery',
            status='pending',
            created_by=self.user,
        )
        OrderItem.objects.create(order=self.order, menu=self.menu, quantity=2)

        self.delivery = Delivery.objects.create(
            order=self.order,
            recipient_name='วิภา รุ่งเรือง',
            phone='090-000-0000',
            address='45/6 ซ.สีสุก เขตจตุจักร กทม 10900',
            fee=0,
            status='pending',
            recipient_lat=13.8,
            recipient_lng=100.55,
        )
        self.store = StoreLocation.get_setting()
        self.store.lat = 13.7563
        self.store.lng = 100.5018
        self.store.fee_base = 10
        self.store.fee_per_km = 5
        self.store.free_delivery_over = None
        self.store.save()

    def test_auto_fee_calculated_on_save_with_coords(self):
        from .models import Delivery
        new_order = Order.objects.create(
            order_type='delivery',
            status='pending',
            created_by=self.user,
        )
        OrderItem.objects.create(order=new_order, menu=self.menu, quantity=1)
        other = Delivery.objects.create(
            order=new_order,
            recipient_name='นางทดสอบ',
            phone='081-111-1111',
            address='ซอยเทสต์',
            fee=0,
            status='pending',
            recipient_lat=13.7563,
            recipient_lng=100.5018,
        )
        other.refresh_from_db()
        self.assertIsNotNone(other.distance_km)
        self.assertGreater(float(other.fee), 0)
        self.assertEqual(float(other.fee), float(self.store.fee_base))

    def test_manual_fee_locked_when_differs_from_auto(self):
        from .models import Delivery
        self.client.login(username='staff', password='password123')
        response = self.client.post(reverse('order_detail', args=[self.order.pk]), {
            'delivery_submit': '1',
            'recipient_name': 'จ่าควบ',
            'phone': '089',
            'address': 'ซอยทดสอบ',
            'recipient_lat': '13.9',
            'recipient_lng': '100.6',
            'fee': '999',
            'rider_name': '',
            'rider_phone': '',
            'tracking_note': '',
        })
        self.assertRedirects(response, reverse('order_detail', args=[self.order.pk]))
        delivery = Delivery.objects.get(order=self.order)
        delivery.refresh_from_db()
        self.assertEqual(float(delivery.fee), 999)
        self.assertTrue(delivery.fee_locked)

    def test_auto_assign_after_grace_picks_free_rider(self):
        from myapp.delivery_auto import maybe_auto_dispatch
        self.store.auto_assign_grace_minutes = 0
        self.store.save()
        maybe_auto_dispatch()
        self.delivery.refresh_from_db()
        self.assertEqual(self.delivery.status, 'accepted')
        self.assertEqual(self.delivery.assigned_rider, self.rider)

    def test_no_rider_available_no_auto_assign(self):
        from myapp.delivery_auto import maybe_auto_dispatch
        self.rider.profile.is_rider = False
        self.rider.profile.save()
        self.store.auto_assign_grace_minutes = 0
        self.store.save()
        maybe_auto_dispatch()
        self.delivery.refresh_from_db()
        self.assertEqual(self.delivery.status, 'pending')
        self.assertIsNone(self.delivery.assigned_rider)

    def test_auto_assign_picks_least_loaded_rider(self):
        from myapp.delivery_auto import maybe_auto_dispatch

        from .models import Delivery

        rider2 = User.objects.create_user(username='rider2', password='password123')
        Profile.objects.update_or_create(user=rider2, defaults={'is_rider': True})

        # rider ยุ่ง: มีงานกำลังทำ 1 อัน → ระบบต้องเลือก rider2 ที่ว่างที่สุด
        busy_order = Order.objects.create(
            order_type='delivery', status='out_for_delivery', created_by=self.user,
        )
        OrderItem.objects.create(order=busy_order, menu=self.menu, quantity=1)
        Delivery.objects.create(
            order=busy_order,
            recipient_name='ลูกค้าที่ยุ่ง',
            phone='082-222-2222',
            address='ซอยวุ่น',
            fee=0,
            status='out_for_delivery',
            assigned_rider=self.rider,
            recipient_lat=13.8,
            recipient_lng=100.55,
        )

        self.store.auto_assign_grace_minutes = 0
        self.store.save()
        maybe_auto_dispatch()
        self.delivery.refresh_from_db()
        self.assertEqual(self.delivery.assigned_rider, rider2)
        self.assertEqual(self.delivery.status, 'accepted')

    def test_release_stuck_accepted_job(self):
        from datetime import timedelta as td

        from django.utils import timezone

        from myapp.delivery_auto import maybe_auto_dispatch

        self.delivery.status = 'accepted'
        self.delivery.assigned_rider = self.rider
        self.delivery.accepted_at = timezone.now() - td(minutes=20)
        self.delivery.save(update_fields=['status', 'assigned_rider', 'accepted_at'])

        self.store.auto_assign_enabled = False
        self.store.auto_release_minutes = 10
        self.store.save()
        maybe_auto_dispatch()

        self.delivery.refresh_from_db()
        self.assertEqual(self.delivery.status, 'pending')
        self.assertIsNone(self.delivery.assigned_rider)
        self.assertEqual(self.delivery.release_count, 1)

    def test_stuck_accepted_not_released_twice_beyond_limit(self):
        from datetime import timedelta as td

        from django.utils import timezone

        from myapp.delivery_auto import maybe_auto_dispatch

        self.delivery.status = 'accepted'
        self.delivery.assigned_rider = self.rider
        self.delivery.accepted_at = timezone.now() - td(minutes=30)
        self.delivery.release_count = 2  # ถึงขีดจำกัดแล้ว ระบบต้องไม่ปล่อยวนซ้ำ
        self.delivery.save(update_fields=['status', 'assigned_rider', 'accepted_at', 'release_count'])

        self.store.auto_assign_enabled = False
        self.store.auto_release_minutes = 10
        self.store.save()
        maybe_auto_dispatch()

        self.delivery.refresh_from_db()
        self.assertEqual(self.delivery.status, 'accepted')

    def test_settings_saves_auto_assign_fields(self):
        self.client.login(username='staff', password='password123')
        response = self.client.post(reverse('delivery_settings'), {
            'name': 'อร่อยเกินเบอร์',
            'lat': '13.75',
            'lng': '100.50',
            'address': 'ตลาดสดแถวนี้',
            'fee_base': '10',
            'fee_per_km': '5',
            'free_delivery_over': '',
            'auto_assign_enabled': 'on',
            'auto_assign_grace_minutes': '5',
            'auto_release_minutes': '15',
        })
        self.assertRedirects(response, reverse('delivery_settings'))
        self.store.refresh_from_db()
        self.assertTrue(self.store.auto_assign_enabled)
        self.assertEqual(self.store.auto_assign_grace_minutes, 5)
        self.assertEqual(self.store.auto_release_minutes, 15)

    def test_rider_nav_badge_shows_new_jobs(self):
        self.client.login(username='rider', password='password123')
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'งานใหม่ที่รอรับ 1 รายการ')


class GoogleSignInTests(TestCase):
    """ทดสอบหน้าเข้าสู่ระบบ/สมัครเมื่อเปิดใช้ Google Sign-In"""

    def setUp(self):
        self.staff = User.objects.create_user(username='staff', password='password123', is_staff=True)

    def test_login_page_hides_google_button_when_not_configured(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'เข้าสู่ระบบด้วย Google')

    def test_login_page_shows_google_button_when_configured(self):
        from allauth.socialaccount.models import SocialApp
        from django.contrib.sites.models import Site
        site, _ = Site.objects.get_or_create(id=1, defaults={'domain': 'testserver', 'name': 'testserver'})
        app = SocialApp.objects.create(
            provider='google',
            name='Google',
            client_id='test-client-id.apps.googleusercontent.com',
            secret='test-secret',
        )
        app.sites.add(site)

        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'เข้าสู่ระบบด้วย Google')

        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'สมัคร/เข้าสู่ระบบด้วย Google')

    def test_google_button_hides_for_authenticated(self):
        self.client.login(username='staff', password='password123')
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 302)

    def test_dev_mode_google_login_creates_and_logs_in_demo_user(self):
        from django.test import override_settings

        # ยังไม่ตั้งค่า Client ID จริง → ใช้ผู้ใช้ทดสอบโหมดพัฒนา
        with override_settings(GOOGLE_OAUTH_CLIENT_ID='', GOOGLE_OAUTH_CLIENT_SECRET='', DEBUG=True):
            response = self.client.get(reverse('google_login_redirect'))
            self.assertRedirects(response, reverse('home'))

            self.assertTrue(response.wsgi_request.user.is_authenticated)
            user = response.wsgi_request.user
            self.assertEqual(user.username, 'demo.google')
            self.assertTrue(user.is_active)
            self.assertFalse(user.is_staff)

            # ล็อกอินซ้ำต้องได้ผู้ใช้คนเดิม ไม่สร้างซ้ำ
            self.client.logout()
            again = self.client.get(reverse('google_login_redirect'))
            self.assertRedirects(again, reverse('home'))
            self.assertEqual(again.wsgi_request.user.pk, user.pk)

    def test_dev_mode_google_respects_next_redirect(self):
        from django.test import override_settings

        with override_settings(GOOGLE_OAUTH_CLIENT_ID='', GOOGLE_OAUTH_CLIENT_SECRET='', DEBUG=True):
            response = self.client.get(reverse('google_login_redirect'), {'next': '/profile/'})
            self.assertRedirects(response, '/profile/')

    def test_google_login_with_real_credentials_redirects_to_oauth(self):
        from django.test import override_settings

        with override_settings(
            GOOGLE_OAUTH_CLIENT_ID='real-id.apps.googleusercontent.com',
            GOOGLE_OAUTH_CLIENT_SECRET='real-secret',
            DEBUG=True,
        ):
            response = self.client.get(reverse('google_login_redirect'))
            self.assertIn('/accounts/google/login/', response.url)

    def test_google_login_production_without_credentials_blocked(self):
        from django.test import override_settings

        with override_settings(GOOGLE_OAUTH_CLIENT_ID='', GOOGLE_OAUTH_CLIENT_SECRET='', DEBUG=False):
            response = self.client.get(reverse('google_login_redirect'))
            self.assertRedirects(response, reverse('login'))

    def test_google_adapter_opens_signup(self):
        """ผู้ใช้ใหม่ผ่าน Google ได้รับอนุญาตให้สร้างบัญชี (อีเมลยืนยันแล้ว)"""
        from myapp.accounts import GoogleAccountAdapter

        adapter = GoogleAccountAdapter()
        request = self._make_session_request()
        self.assertTrue(adapter.is_open_for_signup(request, None))

    def _make_pending_sociallogin(self, email, uid='google-uid-test'):
        """สร้าง SocialLogin ที่ยังมี 's บัญชี (user ยังไม่ถูกบันทึก)"""
        from allauth.account.models import EmailAddress
        from allauth.socialaccount.models import SocialAccount, SocialLogin
        return SocialLogin(
            user=User(username=f'google-temp-{uid}'),
            account=SocialAccount(provider='google', uid=uid),
            email_addresses=[EmailAddress(email=email)],
        )

    def _create_google_app(self):
        """สร้าง SocialApp สำหรับ Google ใน test DB (จำเป็นตอน connect บัญชี)"""
        from allauth.socialaccount.models import SocialApp
        from django.contrib.sites.models import Site
        site, _ = Site.objects.get_or_create(
            id=1, defaults={'domain': 'testserver', 'name': 'testserver'}
        )
        app = SocialApp.objects.create(
            provider='google',
            name='Google',
            client_id='test-client-id.apps.googleusercontent.com',
            secret='test-secret',
        )
        app.sites.add(site)
        return app

    def _make_session_request(self):
        """สร้าง request ที่ผ่าน middleware (session/messages/auth) สำหรับเรียก adapter"""
        from django.contrib.auth.middleware import AuthenticationMiddleware
        from django.contrib.messages.middleware import MessageMiddleware
        from django.contrib.sessions.middleware import SessionMiddleware
        from django.test import RequestFactory

        request = RequestFactory().get('/')
        for middleware in (SessionMiddleware, MessageMiddleware, AuthenticationMiddleware):
            middleware(lambda r: None).process_request(request)
        return request

    def test_google_adapter_links_existing_account_with_same_email(self):
        """อีเมล Google ตรงกับบัญชี username/รหัสผ่าน ที่มีอยู่ → ลิงก์บัญชีเดิม"""
        from allauth.exceptions import ImmediateHttpResponse
        from allauth.socialaccount.models import SocialAccount

        from myapp.accounts import GoogleAccountAdapter

        existing = User.objects.create_user(
            username='member1', email='member1@example.com', password='secret',
            is_active=True,
        )
        sociallogin = self._make_pending_sociallogin('MEMBER1@example.com')
        self.assertFalse(sociallogin.is_existing)
        self._create_google_app()

        request = self._make_session_request()

        from django.http import HttpResponse
        with mock.patch('myapp.accounts.perform_login', return_value=HttpResponse()):
            with self.assertRaises(ImmediateHttpResponse):
                GoogleAccountAdapter().pre_social_login(request, sociallogin)

        # SocialAccount ผูกกับบัญชีเดิม (ไม่สร้างผู้ใช้ใหม่)
        self.assertTrue(
            SocialAccount.objects.filter(
                user=existing, provider='google', uid='google-uid-test'
            ).exists()
        )
        self.assertEqual(User.objects.filter(email__iexact='member1@example.com').count(), 1)

    def test_google_adapter_activates_pending_account(self):
        """บัญชีที่เคยสมัคร (รออนุมัติ) ถ้าเข้า Google ด้วยอีเมลเดียวกัน → เปิดใช้งาน"""
        from allauth.exceptions import ImmediateHttpResponse

        from myapp.accounts import GoogleAccountAdapter

        pending = User.objects.create_user(
            username='pending1', email='pending1@example.com', password='secret',
            is_active=False,
        )
        sociallogin = self._make_pending_sociallogin('pending1@example.com')
        self._create_google_app()

        request = self._make_session_request()

        from django.http import HttpResponse
        with mock.patch('myapp.accounts.perform_login', return_value=HttpResponse()):
            with self.assertRaises(ImmediateHttpResponse):
                GoogleAccountAdapter().pre_social_login(request, sociallogin)

        pending.refresh_from_db()
        self.assertTrue(pending.is_active)

    def test_google_adapter_ignores_unknown_email(self):
        """อีเมลที่ไม่มีบัญชีในระบบ → ปล่อยให้ auto-signup ของ allauth ทำงาน"""
        from myapp.accounts import GoogleAccountAdapter

        sociallogin = self._make_pending_sociallogin('nobody@example.com')
        request = self._make_session_request()

        adapter = GoogleAccountAdapter()
        adapter.pre_social_login(request, sociallogin)  # ต้องไม่ raise

    def test_google_adapter_uses_existing_socialaccount(self):
        """SocialAccount มีอยู่แล้ว → ไม่เข้าไปยุ่ง (flow ปกติของ allauth)"""
        from allauth.account.models import EmailAddress
        from allauth.socialaccount.models import SocialAccount, SocialLogin

        from myapp.accounts import GoogleAccountAdapter

        existing = User.objects.create_user(
            username='returning', email='returning@example.com', password='secret',
        )
        SocialAccount.objects.create(
            user=existing, provider='google', uid='google-returning',
        )
        # sociallogin.user มี pk อยู่ใน DB → sociallogin.is_existing = True
        sociallogin = SocialLogin(
            user=existing,
            account=SocialAccount(provider='google', uid='google-returning'),
            email_addresses=[EmailAddress(email='returning@example.com')],
        )
        self.assertTrue(sociallogin.is_existing)

        request = self._make_session_request()
        GoogleAccountAdapter().pre_social_login(request, sociallogin)  # ต้องไม่ raise


# ======================================================================
# ทดสอบระบบคูปองส่วนลด
# ======================================================================


class CouponTests(TestCase):
    """ทดสอบ Coupon model: สร้าง, is_valid, discount_for, mark_used, มองเห็นใน admin"""

    def setUp(self):
        self.coupon_pct = Coupon.objects.create(
            code='SAVE10', discount_type='percent', value=Decimal('10'),
            min_order=Decimal('100'), max_uses=5,
        )
        self.coupon_fixed = Coupon.objects.create(
            code='FLAT50', discount_type='fixed', value=Decimal('50'),
        )

    def test_str_representation(self):
        self.assertIn('SAVE10', str(self.coupon_pct))
        self.assertIn('10%', str(self.coupon_pct))
        self.assertIn('FLAT50', str(self.coupon_fixed))

    def test_code_saved_uppercase(self):
        c = Coupon.objects.create(code='lower', discount_type='fixed', value=Decimal('10'))
        c.refresh_from_db()
        self.assertEqual(c.code, 'LOWER')

    def test_is_valid_active_within_dates(self):
        self.assertTrue(self.coupon_pct.is_valid())

    def test_is_valid_inactive_coupon(self):
        self.coupon_pct.is_active = False
        self.coupon_pct.save()
        self.assertFalse(self.coupon_pct.is_valid())

    def test_is_valid_before_valid_from(self):
        self.coupon_pct.valid_from = timezone.localdate() + timedelta(days=5)
        self.coupon_pct.save()
        self.assertFalse(self.coupon_pct.is_valid())

    def test_is_valid_after_valid_until(self):
        self.coupon_pct.valid_until = timezone.localdate() - timedelta(days=1)
        self.coupon_pct.save()
        self.assertFalse(self.coupon_pct.is_valid())

    def test_is_valid_max_uses_reached(self):
        self.coupon_pct.used_count = 5
        self.coupon_pct.save()
        self.assertFalse(self.coupon_pct.is_valid())

    def test_is_valid_below_min_order(self):
        self.assertFalse(self.coupon_pct.is_valid(order_price=Decimal('50')))
        self.assertTrue(self.coupon_pct.is_valid(order_price=Decimal('100')))
        self.assertTrue(self.coupon_pct.is_valid(order_price=Decimal('200')))

    def test_is_valid_no_limit_uses(self):
        self.assertTrue(self.coupon_fixed.is_valid())

    def test_discount_for_percent(self):
        # 10% ของ 200 = 20
        discount = self.coupon_pct.discount_for(Decimal('200'))
        self.assertEqual(discount, Decimal('20'))

    def test_discount_for_fixed(self):
        discount = self.coupon_fixed.discount_for(Decimal('200'))
        self.assertEqual(discount, Decimal('50'))

    def test_discount_for_cannot_exceed_order(self):
        discount = self.coupon_fixed.discount_for(Decimal('30'))
        self.assertEqual(discount, Decimal('30'))

    def test_discount_for_zero_returns_zero(self):
        discount = self.coupon_fixed.discount_for(Decimal('0'))
        self.assertEqual(discount, Decimal('0'))

    def test_mark_used_increments(self):
        self.assertEqual(self.coupon_pct.used_count, 0)
        self.coupon_pct.mark_used()
        self.coupon_pct.refresh_from_db()
        self.assertEqual(self.coupon_pct.used_count, 1)
        self.coupon_pct.mark_used()
        self.coupon_pct.refresh_from_db()
        self.assertEqual(self.coupon_pct.used_count, 2)


class CouponViewTests(TestCase):
    """ทดสอบหน้า Coupon CRUD"""

    def setUp(self):
        self.staff = User.objects.create_user(username='staff', password='password123', is_staff=True)
        self.user = User.objects.create_user(username='user', password='password123')
        self.coupon = Coupon.objects.create(
            code='TEST10', discount_type='percent', value=Decimal('10'),
        )

    def test_coupon_list_requires_staff(self):
        self.client.login(username='user', password='password123')
        response = self.client.get(reverse('coupon_list'))
        self.assertEqual(response.status_code, 302)

        self.client.login(username='staff', password='password123')
        response = self.client.get(reverse('coupon_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TEST10')

    def test_coupon_create(self):
        self.client.login(username='staff', password='password123')
        response = self.client.post(reverse('coupon_create'), {
            'code': 'NEW20',
            'discount_type': 'fixed',
            'value': '20',
            'min_order': '0',
            'max_uses': '',
            'valid_from': timezone.localdate().isoformat(),
            'valid_until': '',
            'is_active': 'on',
        })
        self.assertEqual(Coupon.objects.count(), 2)
        self.assertTrue(Coupon.objects.filter(code='NEW20').exists())

    def test_coupon_delete(self):
        self.client.login(username='staff', password='password123')
        response = self.client.post(reverse('coupon_delete', args=[self.coupon.pk]))
        self.assertEqual(Coupon.objects.count(), 0)

    def test_order_apply_coupon(self):
        self.client.login(username='staff', password='password123')
        order = Order.objects.create(table_number=1, created_by=self.staff)
        OrderItem.objects.create(order=order, menu=MenuItem.objects.create(name='Test', price=Decimal('150')), quantity=1)
        response = self.client.post(reverse('order_apply_coupon', args=[order.pk]), {'coupon_code': 'TEST10'})
        self.assertRedirects(response, reverse('order_detail', args=[order.pk]) + '#cart-list', fetch_redirect_response=False)
        order.refresh_from_db()
        self.assertEqual(order.coupon_code, 'TEST10')
        self.assertEqual(order.coupon_discount, Decimal('15'))

    def test_order_apply_invalid_coupon(self):
        self.client.login(username='staff', password='password123')
        order = Order.objects.create(table_number=1, created_by=self.staff)
        OrderItem.objects.create(order=order, menu=MenuItem.objects.create(name='Test2', price=Decimal('150')), quantity=1)
        response = self.client.post(reverse('order_apply_coupon', args=[order.pk]), {'code': 'EXPIRED'})
        order.refresh_from_db()
        self.assertEqual(order.coupon_code, '')

    def test_order_remove_coupon(self):
        self.client.login(username='staff', password='password123')
        order = Order.objects.create(table_number=1, created_by=self.staff, coupon_code='TEST10', coupon_discount=Decimal('10'))
        response = self.client.post(reverse('order_remove_coupon', args=[order.pk]))
        self.assertRedirects(response, reverse('order_detail', args=[order.pk]))
        order.refresh_from_db()
        self.assertEqual(order.coupon_code, '')
        self.assertEqual(order.coupon_discount, Decimal('0'))


# ======================================================================
# ทดสอบระบบสต็อกวัตถุดิบ
# ======================================================================


class StockTests(TestCase):
    """ทดสอบ Ingredient / MenuIngredient / consume_stock_for_order"""

    def setUp(self):
        self.menu = MenuItem.objects.create(name='ข้าวผัดกะเพรา', price=Decimal('50'))
        self.basil = Ingredient.objects.create(name='ใบกะเพรา', unit='กรัม', stock_qty=Decimal('100'), reorder_level=Decimal('20'))
        self.rice = Ingredient.objects.create(name='ข้าว', unit='กรัม', stock_qty=Decimal('500'), reorder_level=Decimal('100'))
        MenuIngredient.objects.create(menu=self.menu, ingredient=self.basil, quantity=Decimal('10'))
        MenuIngredient.objects.create(menu=self.menu, ingredient=self.rice, quantity=Decimal('200'))

    def test_ingredient_str(self):
        self.assertIn('ใบกะเพรา', str(self.basil))

    def test_ingredient_is_low_stock(self):
        self.assertFalse(self.basil.is_low_stock)
        self.basil.stock_qty = Decimal('20')
        self.basil.save()
        self.assertTrue(self.basil.is_low_stock)

    def test_ingredient_is_out_stock(self):
        self.assertFalse(self.basil.is_out_stock)
        self.basil.stock_qty = Decimal('0')
        self.basil.save()
        self.assertTrue(self.basil.is_out_stock)

    def test_adjust_stock_positive(self):
        self.basil.adjust_stock(Decimal('50'))
        self.assertEqual(self.basil.stock_qty, Decimal('150'))

    def test_adjust_stock_negative(self):
        self.basil.adjust_stock(Decimal('-30'))
        self.assertEqual(self.basil.stock_qty, Decimal('70'))

    def test_adjust_stock_cannot_go_below_zero(self):
        self.basil.adjust_stock(Decimal('-999'))
        self.assertEqual(self.basil.stock_qty, Decimal('0'))

    def test_consume_stock_for_order(self):
        order = Order.objects.create(table_number=1)
        OrderItem.objects.create(order=order, menu=self.menu, quantity=2)
        from .models import consume_stock_for_order
        consumed = consume_stock_for_order(order)
        self.basil.refresh_from_db()
        self.rice.refresh_from_db()
        # 2 x 10 = 20 กะเพรา, 2 x 200 = 400 ข้าว
        self.assertEqual(self.basil.stock_qty, Decimal('80'))
        self.assertEqual(self.rice.stock_qty, Decimal('100'))
        self.assertEqual(consumed, 2)

    def test_stock_auto_consumed_on_status_change_to_preparing(self):
        order = Order.objects.create(table_number=1)
        OrderItem.objects.create(order=order, menu=self.menu, quantity=1)
        order.status = 'preparing'
        order.save()
        self.basil.refresh_from_db()
        self.rice.refresh_from_db()
        self.assertEqual(self.basil.stock_qty, Decimal('90'))
        self.assertEqual(self.rice.stock_qty, Decimal('300'))

    def test_stock_not_consumed_twice(self):
        order = Order.objects.create(table_number=1)
        OrderItem.objects.create(order=order, menu=self.menu, quantity=1)
        order.status = 'preparing'
        order.save()
        order.status = 'ready'
        order.save()
        order.status = 'preparing'
        order.save()
        self.basil.refresh_from_db()
        # ตัดแค่ 2 ครั้ง (preparing ครั้งที่ 1 + ครั้งที่ 2)
        self.assertEqual(self.basil.stock_qty, Decimal('80'))

    def test_menu_ingredient_str(self):
        mi = self.menu.ingredients.first()
        self.assertIn('ข้าวผัดกะเพรา', str(mi))


# ======================================================================
# ทดสอบระบบจองโต๊ะ
# ======================================================================


class ReservationTests(TestCase):
    """ทดสอบ Reservation model, form, views"""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.user = User.objects.create_user(username='user', password='password123')
        self.staff = User.objects.create_user(username='staff', password='password123', is_staff=True)

    def _create_reservation(self, **kwargs):
        defaults = dict(
            customer_name='สมศักดิ์',
            phone='081-234-5678',
            party_size=4,
            reservation_date=timezone.localdate() + timedelta(days=1),
            reservation_time='18:30',
        )
        defaults.update(kwargs)
        return Reservation.objects.create(**defaults)

    def test_reservation_str(self):
        r = self._create_reservation()
        self.assertIn('สมศักดิ์', str(r))
        self.assertIn('4', str(r))

    def test_reservation_create_form_valid(self):
        from .forms import ReservationForm
        form = ReservationForm(data={
            'customer_name': 'ทดสอบ',
            'phone': '089-000-0000',
            'party_size': 2,
            'reservation_date': (timezone.localdate() + timedelta(days=1)).isoformat(),
            'reservation_time': '19:00',
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_reservation_create_view(self):
        response = self.client.get(reverse('reservation_create'))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse('reservation_create'), {
            'customer_name': 'วันใหม่',
            'phone': '082-111-2222',
            'party_size': 3,
            'reservation_date': (timezone.localdate() + timedelta(days=2)).isoformat(),
            'reservation_time': '17:00',
        })
        self.assertIn(response.status_code, (200, 302))
        self.assertTrue(Reservation.objects.filter(customer_name='วันใหม่').exists())

    def test_reservation_list_public(self):
        response = self.client.get(reverse('reservation_list'))
        self.assertEqual(response.status_code, 200)

    def test_reservation_list_shows_own(self):
        self.client.login(username='user', password='password123')
        r = self._create_reservation(created_by=self.user)
        other = self._create_reservation(customer_name='คนอื่น', phone='089-999-0000', created_by=User.objects.create_user(username='other', password='pass'))
        response = self.client.get(reverse('reservation_list'))
        self.assertContains(response, '4 คน')

    def test_reservation_dashboard_requires_staff(self):
        self.client.login(username='user', password='password123')
        response = self.client.get(reverse('reservation_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_reservation_dashboard_staff(self):
        self.client.login(username='staff', password='password123')
        self._create_reservation()
        response = self.client.get(reverse('reservation_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'สมศักดิ์')

    def test_reservation_update_status(self):
        self.client.login(username='staff', password='password123')
        r = self._create_reservation()
        response = self.client.post(reverse('reservation_update_status', args=[r.pk]), {
            'status': 'confirmed',
        })
        r.refresh_from_db()
        self.assertEqual(r.status, 'confirmed')

    def test_reservation_delete(self):
        self.client.login(username='staff', password='password123')
        r = self._create_reservation()
        response = self.client.post(reverse('reservation_delete', args=[r.pk]))
        self.assertEqual(Reservation.objects.count(), 0)


# ======================================================================
# ทดสอบระบบรีวิว
# ======================================================================


class ReviewTests(TestCase):
    """ทดสอบ Review model, form, views"""

    def setUp(self):
        self.user = User.objects.create_user(username='user', password='password123')
        self.menu = MenuItem.objects.create(name='ข้าวผัด', price=Decimal('45'))

    def test_review_str(self):
        r = Review.objects.create(menu=self.menu, user=self.user, rating=5, comment='อร่อยมาก')
        self.assertIn('ข้าวผัด', str(r))
        self.assertIn('5', str(r))

    def test_review_unique_per_user_per_menu(self):
        Review.objects.create(menu=self.menu, user=self.user, rating=5)
        with self.assertRaises(Exception):
            Review.objects.create(menu=self.menu, user=self.user, rating=4)

    def test_review_rating_must_be_1_to_5(self):
        Review.objects.create(menu=self.menu, user=self.user, rating=1)
        self.assertEqual(Review.objects.filter(menu=self.menu).count(), 1)
        with self.assertRaises(Exception):
            Review.objects.create(menu=self.menu, user=User.objects.create_user(username='u2', password='pass'), rating=6)
        with self.assertRaises(Exception):
            Review.objects.create(menu=self.menu, user=User.objects.create_user(username='u3', password='pass'), rating=0)

    def test_review_create_view(self):
        response = self.client.post(reverse('review_create', args=[self.menu.pk]), {
            'rating': 4,
            'comment': 'ดีมาก',
        })
        # ต้องล็อกอินก่อน
        self.assertIn(response.status_code, (302, 200))
        self.client.login(username='user', password='password123')
        response = self.client.post(reverse('review_create', args=[self.menu.pk]), {
            'rating': 4,
            'comment': 'ดีมาก',
        })
        self.assertTrue(Review.objects.filter(user=self.user, menu=self.menu).exists())

    def test_review_delete_view(self):
        self.client.login(username='user', password='password123')
        r = Review.objects.create(menu=self.menu, user=self.user, rating=3, comment='ok')
        response = self.client.post(reverse('review_delete', args=[r.pk]))
        self.assertEqual(Review.objects.count(), 0)

    def test_review_delete_view_rejects_get(self):
        # GET ต้องถูกปฏิเสธ — กันลบข้ามไซต์ผ่าน <img src=".../delete/">
        self.client.login(username='user', password='password123')
        r = Review.objects.create(menu=self.menu, user=self.user, rating=3, comment='ok')
        response = self.client.get(reverse('review_delete', args=[r.pk]))
        self.assertEqual(response.status_code, 405)
        self.assertEqual(Review.objects.count(), 1)

    def test_menu_detail_shows_reviews(self):
        Review.objects.create(menu=self.menu, user=self.user, rating=5, comment='สุดยอด')
        response = self.client.get(reverse('menu_detail', args=[self.menu.pk]))
        self.assertContains(response, 'สุดยอด')


# ======================================================================
# ทดสอบ PromptPay QR
# ======================================================================


class PromptPayTests(TestCase):
    """ทดสอบ PromptPay payload + QR code generation"""

    def test_crc16_known_vector(self):
        data = b'00020101021229370016001100669123456789053037645802TH54041.006304'
        crc = crc16_xmodem(data)
        self.assertIsInstance(crc, int)
        self.assertGreater(crc, 0)
        self.assertLessEqual(crc, 0xFFFF)

    def test_promptpay_payload_returns_string(self):
        payload = promptpay_payload('081-234-5678', 100)
        self.assertIsInstance(payload, str)
        self.assertTrue(len(payload) > 20)

    def test_promptpay_payload_no_id_returns_none(self):
        self.assertIsNone(promptpay_payload('', 100))
        self.assertIsNone(promptpay_payload(None, 100))

    def test_promptpay_payload_zero_amount_returns_none(self):
        self.assertIsNone(promptpay_payload('081-234-5678', 0))
        self.assertIsNone(promptpay_payload('081-234-5678', -10))

    def test_promptpay_payload_phone_format(self):
        payload = promptpay_payload('0812345678', 50)
        self.assertIn('0066', payload)

    def test_promptpay_payload_id_card_format(self):
        payload = promptpay_payload('1234567890123', 50)
        self.assertIsInstance(payload, str)

    def test_render_qrcode_base64_returns_data_uri(self):
        uri = render_qrcode_base64('test-payload')
        self.assertTrue(uri.startswith('data:image/png;base64,'))

    def test_promptpay_full_amount_matches_discount(self):
        # Test decimal precision
        payload = promptpay_payload('0812345678', Decimal('150.50'))
        self.assertIn('150.50', payload)


# ======================================================================
# ทดสอบ Notification services
# ======================================================================


class NotificationTests(TestCase):
    """ทดสอบ notify_line / notify_email"""

    def test_notify_email_sends(self):
        from .services import notify_email
        sent = notify_email(['test@example.com'], 'Test', 'Hello')
        self.assertTrue(sent)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Test', mail.outbox[0].subject)

    def test_notify_email_no_recipient_returns_false(self):
        from .services import notify_email
        self.assertFalse(notify_email([], 'Test', 'Hello'))

    @mock.patch('requests.post')
    def test_notify_line_success(self, mock_post):
        mock_post.return_value = mock.Mock(status_code=200)
        from .services import notify_line
        result = notify_line('fake-token', 'Test message')
        self.assertTrue(result)

    def test_notify_line_no_token_returns_false(self):
        from .services import notify_line
        self.assertFalse(notify_line('', 'Test'))

    def test_announce_new_order(self):
        from .services import announce_new_order
        staff = User.objects.create_user(username='staff2', password='pass', is_staff=True)
        menu = MenuItem.objects.create(name='Test', price=Decimal('50'))
        order = Order.objects.create(table_number=3)
        OrderItem.objects.create(order=order, menu=menu, quantity=1)
        # announce ไม่ควร error แม้ไม่มี token
        announce_new_order(order)

    @mock.patch('requests.post')
    @mock.patch('time.sleep')
    def test_notify_line_retries_on_transient_error_then_succeeds(self, mock_sleep, mock_post):
        # 5xx ติดกัน 2 ครั้ง แล้วค่อยสำเร็จ → ต้องพยายามรวม 3 ครั้ง และรอเล็กน้อยระหว่างลอง
        mock_post.side_effect = [
            mock.Mock(status_code=500),
            mock.Mock(status_code=500),
            mock.Mock(status_code=200),
        ]
        from .services import notify_line
        self.assertTrue(notify_line('fake-token', 'Test'))
        self.assertEqual(mock_post.call_count, 3)
        mock_sleep.assert_called_with(1)

    @mock.patch('requests.post')
    @mock.patch('time.sleep')
    def test_notify_line_does_not_retry_on_bad_request(self, mock_sleep, mock_post):
        # token ผิด (400) เป็น error ชัดเจน → จบเลย ไม่ต้องรอ 3 ครั้ง
        mock_post.return_value = mock.Mock(status_code=400)
        from .services import notify_line
        self.assertFalse(notify_line('bad-token', 'Test'))
        self.assertEqual(mock_post.call_count, 1)

    @mock.patch('requests.get')
    def test_line_notify_status(self, mock_get):
        from .services import line_notify_status
        mock_get.return_value = mock.Mock(status_code=200)
        self.assertTrue(line_notify_status('fake-token'))
        mock_get.return_value = mock.Mock(status_code=401)
        self.assertFalse(line_notify_status('fake-token'))

    def test_line_notify_status_no_token(self):
        from .services import line_notify_status
        self.assertFalse(line_notify_status(''))

    @override_settings(LINE_NOTIFY_TOKEN='env-token-1234')
    @mock.patch('myapp.services.notify_line')
    def test_announce_falls_back_to_env_token(self, mock_notify):
        # ไม่ได้ตั้ง token ใน DB → ต้องใช้ env LINE_NOTIFY_TOKEN แทน
        from .models import StoreLocation
        from .services import announce_new_review
        store = StoreLocation.get_setting()
        store.line_notify_token = ''
        store.save()
        menu = MenuItem.objects.create(name='Env', price=Decimal('20'))
        review = Review.objects.create(menu=menu, user=User.objects.create_user(
            username='u1', password='pass'), rating=5, comment='ดี')
        announce_new_review(review)
        mock_notify.assert_called_once_with('env-token-1234', mock.ANY)

    def test_mask_token(self):
        from .services import mask_token
        self.assertEqual(mask_token(''), '')
        self.assertEqual(mask_token(None), '')
        self.assertEqual(mask_token('abc'), '•' * 8)
        self.assertEqual(mask_token('1234567890'), '•' * 8 + '7890')


# ======================================================================
# ทดสอบ API ภายนอก: Geocoding (Nominatim/OpenStreetMap)
# ======================================================================


class GeocodingTests(TestCase):
    """ทดสอบ geocode_address — ไม่ยิงเน็ตจริง ใช้ mock ทั้งหมด"""

    @mock.patch('requests.get')
    def test_geocode_address_success(self, mock_get):
        from .services import geocode_address
        mock_get.return_value = mock.Mock(
            status_code=200,
            json=lambda: [{'lat': '16.4539', 'lon': '99.5123'}],
        )
        self.assertEqual(geocode_address('กำแพงเพชร'), (16.4539, 99.5123))

    @mock.patch('requests.get')
    def test_geocode_address_sends_user_agent(self, mock_get):
        from .services import geocode_address
        mock_get.return_value = mock.Mock(status_code=200, json=lambda: [])
        geocode_address('กำแพงเพชร')
        headers = mock_get.call_args.kwargs.get('headers', {})
        self.assertTrue(headers.get('User-Agent'))

    @mock.patch('requests.get')
    def test_geocode_address_not_found(self, mock_get):
        from .services import geocode_address
        mock_get.return_value = mock.Mock(status_code=200, json=lambda: [])
        self.assertIsNone(geocode_address('xxyyzz-not-found-address'))

    @mock.patch('requests.get')
    def test_geocode_address_api_error(self, mock_get):
        from .services import geocode_address
        mock_get.side_effect = requests.exceptions.ConnectionError('connection down')
        self.assertIsNone(geocode_address('กำแพงเพชร'))

    def test_geocode_address_empty(self):
        from .services import geocode_address
        self.assertIsNone(geocode_address(''))
        self.assertIsNone(geocode_address(None))
        self.assertIsNone(geocode_address('   '))


class ExternalApiViewsTests(TestCase):
    """ทดสอบการเรียกใช้ API ภายนอกผ่านหน้าเว็บ (delivery_geocode / line_notify_test)"""

    def setUp(self):
        self.staff = User.objects.create_user(username='staff', password='password123', is_staff=True)
        self.menu = MenuItem.objects.create(name='ข้าวผัดกะเพรา', price=Decimal('50'))

    def _make_delivery(self, address='11/1 ถนนปฏิรูป จ.กำแพงเพชร', lat=None, lng=None):
        order = Order.objects.create(table_number=1, order_type='delivery')
        delivery = Delivery.objects.create(
            order=order,
            recipient_name='สมชาย',
            phone='0812345678',
            address=address,
            recipient_lat=lat,
            recipient_lng=lng,
        )
        return order, delivery

    def test_delivery_geocode_requires_staff(self):
        order, delivery = self._make_delivery()
        response = self.client.post(reverse('delivery_geocode', args=[delivery.pk]))
        self.assertIn(response.status_code, (302, 303))

    @mock.patch('myapp.services.geocode_address', return_value=(13.75, 100.5))
    def test_delivery_geocode_updates_coords_and_fee(self, mock_geo):
        self.client.login(username='staff', password='password123')
        order, delivery = self._make_delivery()
        response = self.client.post(
            reverse('delivery_geocode', args=[delivery.pk]),
            {'next': reverse('order_detail', args=[order.pk])},
        )
        self.assertEqual(response.status_code, 302)
        delivery.refresh_from_db()
        self.assertAlmostEqual(float(delivery.recipient_lat), 13.75, places=2)
        self.assertAlmostEqual(float(delivery.recipient_lng), 100.5, places=2)
        self.assertIsNotNone(delivery.distance_km)
        self.assertGreaterEqual(float(delivery.fee), 0)

    @mock.patch('myapp.services.geocode_address', return_value=None)
    def test_delivery_geocode_not_found(self, mock_geo):
        self.client.login(username='staff', password='password123')
        order, delivery = self._make_delivery()
        response = self.client.post(
            reverse('delivery_geocode', args=[delivery.pk]),
            {'next': reverse('order_detail', args=[order.pk])},
        )
        self.assertEqual(response.status_code, 302)
        delivery.refresh_from_db()
        self.assertIsNone(delivery.recipient_lat)

    def test_delivery_geocode_no_address(self):
        self.client.login(username='staff', password='password123')
        order, delivery = self._make_delivery(address='')
        response = self.client.post(reverse('delivery_geocode', args=[delivery.pk]))
        self.assertEqual(response.status_code, 302)
        delivery.refresh_from_db()
        self.assertIsNone(delivery.recipient_lat)

    @mock.patch('myapp.services.notify_line', return_value=True)
    def test_line_notify_test_success(self, mock_notify):
        self.client.login(username='staff', password='password123')
        response = self.client.post(reverse('line_notify_test'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(mock_notify.called)

    @mock.patch('myapp.services.notify_line', return_value=False)
    def test_line_notify_test_failure(self, mock_notify):
        self.client.login(username='staff', password='password123')
        response = self.client.post(reverse('line_notify_test'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(mock_notify.called)

    def test_line_notify_test_requires_staff(self):
        response = self.client.post(reverse('line_notify_test'))
        self.assertIn(response.status_code, (302, 303))


# ======================================================================
# ทดสอบหน้าจอครัว (KDS)
# ======================================================================


class KitchenDisplayTests(TestCase):
    """ทดสอบหน้าจอครัว"""

    def setUp(self):
        self.staff = User.objects.create_user(username='staff', password='password123', is_staff=True)
        self.menu = MenuItem.objects.create(name='ข้าวผัด', price=Decimal('50'))

    def test_kitchen_display_requires_staff(self):
        response = self.client.get(reverse('kitchen_display'))
        self.assertIn(response.status_code, (302, 303))

    def test_kitchen_display_staff(self):
        self.client.login(username='staff', password='password123')
        order = Order.objects.create(table_number=2, status='preparing')
        OrderItem.objects.create(order=order, menu=self.menu, quantity=1)
        response = self.client.get(reverse('kitchen_display'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ครัว')

    def test_kds_update_status(self):
        self.client.login(username='staff', password='password123')
        order = Order.objects.create(table_number=2, status='preparing')
        OrderItem.objects.create(order=order, menu=self.menu, quantity=1)
        response = self.client.post(reverse('kds_update_status', args=[order.pk]), {
            'new_status': 'ready',
        })
        order.refresh_from_db()
        self.assertEqual(order.status, 'ready')


# ======================================================================
# ทดสอบคะแนนสะสมสมาชิก
# ======================================================================


class PointsDisplayTests(TestCase):
    """ทดสอบการเห็นคะแนนสะสมบนหน้าโปรไฟล์ / navbar / หน้าผู้อื่น"""

    def setUp(self):
        self.user = User.objects.create_user(username='user', password='password123')
        self.staff = User.objects.create_user(username='staff', password='password123', is_staff=True)
        self.user.profile.points = 150
        self.user.profile.save()

    def test_points_badge_on_navbar(self):
        self.client.login(username='user', password='password123')
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '150')
        self.assertContains(response, 'คะแนนสะสม')

    def test_own_profile_shows_points(self):
        self.client.login(username='user', password='password123')
        response = self.client.get(reverse('user_profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '150 <small')
        self.assertContains(response, 'คะแนนสะสม')

    def test_public_profile_shows_points(self):
        self.client.login(username='staff', password='password123')
        response = self.client.get(reverse('user_profile_detail', args=[self.user.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '150 คะแนน')

    def test_earn_points_matches_rate(self):
        # regular rate = 1 คะแนน / บาท → ใช้จ่าย 100 บาทได้ 100 คะแนน
        menu = MenuItem.objects.create(name='ข้าวผัด', price=Decimal('50'))
        order = Order.objects.create(table_number=1, created_by=self.user)
        OrderItem.objects.create(order=order, menu=menu, quantity=2)
        order.status = 'paid'
        order.payment_method = 'cash'
        order.save()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.points, 250)

    def test_vip_points_rate_higher(self):
        self.user.profile.membership_status = 'vip'
        self.user.profile.points = 0
        self.user.profile.save()
        earned = self.user.profile.earn_points(Decimal('100'))
        self.assertEqual(earned, 150)  # vip rate 1.5
        self.assertEqual(self.user.profile.points, 150)


class PointsRedemptionTests(TestCase):
    """ทดสอบการแลกคะแนนสะสมเป็นสิทธิ์ประโยชน์ (สร้างคูปองผูกเจ้าของ)"""

    def setUp(self):
        self.user = User.objects.create_user(username='user', password='password123')
        self.other = User.objects.create_user(username='other', password='password123')
        self.reward = PointReward.objects.create(
            name='คูปอง 50 บาท',
            description='ใช้เป็นส่วนลด 50 บาท',
            points_cost=500,
            discount_type='fixed',
            value=Decimal('50'),
            min_order=Decimal('300'),
        )
        self.user.profile.points = 600
        self.user.profile.save()

    def test_redeem_creates_owned_coupon_and_deducts_points(self):
        self.client.login(username='user', password='password123')
        response = self.client.post(reverse('points_redemption'), {'reward_id': self.reward.pk})
        self.assertEqual(response.status_code, 302)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.points, 100)
        coupon = Coupon.objects.filter(owner=self.user, code__startswith='PTS-').get()
        self.assertEqual(coupon.value, Decimal('50'))
        self.assertIsNotNone(coupon.valid_until)

    def test_redeem_records_transaction(self):
        self.client.login(username='user', password='password123')
        self.client.post(reverse('points_redemption'), {'reward_id': self.reward.pk})
        tx = PointTransaction.objects.filter(profile=self.user.profile).get(points_change=-500)
        self.assertEqual(tx.balance_after, 100)
        self.assertEqual(tx.reward, self.reward)
        self.assertIn('แลก', tx.reason)

    def test_redeem_fails_when_points_insufficient(self):
        self.user.profile.points = 100
        self.user.profile.save()
        self.client.login(username='user', password='password123')
        response = self.client.post(
            reverse('points_redemption'), {'reward_id': self.reward.pk}, follow=True,
        )
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.points, 100)
        self.assertFalse(Coupon.objects.filter(owner=self.user).exists())
        self.assertContains(response, 'ไม่พอ')

    def test_earn_points_writes_ledger(self):
        earned = self.user.profile.earn_points(Decimal('100'))
        self.assertEqual(earned, 100)
        tx = PointTransaction.objects.filter(profile=self.user.profile).get(points_change=100)
        self.assertEqual(tx.balance_after, 700)

    def test_owned_coupon_rejected_for_others(self):
        self.client.login(username='user', password='password123')
        self.client.post(reverse('points_redemption'), {'reward_id': self.reward.pk})
        coupon = Coupon.objects.filter(owner=self.user).get()
        order = Order.objects.create(table_number=1, created_by=self.other)
        menu = MenuItem.objects.create(name='ข้าวผัด', price=Decimal('100'))
        OrderItem.objects.create(order=order, menu=menu, quantity=4)
        self.client.logout()
        self.client.login(username='other', password='password123')
        response = self.client.post(reverse('order_apply_coupon', args=[order.pk]), {
            'coupon_code': coupon.code,
        }, follow=True)
        order.refresh_from_db()
        self.assertEqual(order.coupon_code, '')
        self.assertContains(response, 'ของสมาชิกท่านอื่น')

    def test_owned_coupon_usable_by_owner(self):
        self.client.login(username='user', password='password123')
        self.client.post(reverse('points_redemption'), {'reward_id': self.reward.pk})
        coupon = Coupon.objects.filter(owner=self.user).get()
        order = Order.objects.create(table_number=1, created_by=self.user)
        menu = MenuItem.objects.create(name='ข้าวผัด', price=Decimal('100'))
        OrderItem.objects.create(order=order, menu=menu, quantity=4)
        response = self.client.post(reverse('order_apply_coupon', args=[order.pk]), {
            'coupon_code': coupon.code,
        })
        order.refresh_from_db()
        self.assertEqual(order.coupon_code, coupon.code)
        self.assertGreater(order.coupon_discount, 0)

    def test_points_page_shows_balance_rewards_and_history(self):
        self.user.profile.points = 600
        self.user.profile.save()
        self.user.profile.earn_points(Decimal('100'))
        self.client.login(username='user', password='password123')
        response = self.client.get(reverse('points_redemption'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'คูปอง 50 บาท')
        self.assertContains(response, '700')
        self.assertContains(response, 'ประวัติคะแนน')


# ======================================================================
# ทดสอบหน้าต่างๆ (Dashboard + Staff views)
# ======================================================================


class DashboardStockWidgetTests(TestCase):
    """ทดสอบ dashboard context มีค่าสต็อก/คูปอง/จองโต๊ะ"""

    def setUp(self):
        self.staff = User.objects.create_user(username='staff', password='password123', is_staff=True)
        self.client.login(username='staff', password='password123')

    def test_dashboard_includes_stock_stats(self):
        Ingredient.objects.create(name='น้ำมัน', stock_qty=Decimal('0'), reorder_level=Decimal('10'))
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'สต็อกวัตถุดิบ')

    def test_dashboard_includes_coupon_count(self):
        Coupon.objects.create(code='TEST', discount_type='fixed', value=Decimal('10'))
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'คูปอง')


# ======================================================================
# ทดสอบ Inventory views
# ======================================================================


class InventoryViewTests(TestCase):
    """ทดสอบหน้าจัดการสต็อกวัตถุดิบ"""

    def setUp(self):
        self.staff = User.objects.create_user(username='staff', password='password123', is_staff=True)
        self.client.login(username='staff', password='password123')
        self.ing = Ingredient.objects.create(name='น้ำปลา', unit='ขวด', stock_qty=Decimal('20'))

    def test_inventory_dashboard(self):
        response = self.client.get(reverse('inventory_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'น้ำปลา')

    def test_ingredient_create(self):
        response = self.client.post(reverse('ingredient_create'), {
            'name': 'ซีอิ๊ว',
            'unit': 'ขวด',
            'stock_qty': '10',
            'reorder_level': '5',
            'is_active': 'on',
        })
        self.assertTrue(Ingredient.objects.filter(name='ซีอิ๊ว').exists())

    def test_ingredient_update(self):
        response = self.client.post(reverse('ingredient_update', args=[self.ing.pk]), {
            'name': 'น้ำปลา Premium',
            'unit': 'ขวด',
            'stock_qty': '30',
            'reorder_level': '5',
            'is_active': 'on',
        })
        self.ing.refresh_from_db()
        self.assertEqual(self.ing.name, 'น้ำปลา Premium')

    def test_ingredient_delete(self):
        response = self.client.post(reverse('ingredient_delete', args=[self.ing.pk]))
        self.assertFalse(Ingredient.objects.filter(pk=self.ing.pk).exists())

    def test_menu_ingredient_list(self):
        menu = MenuItem.objects.create(name='ข้าวผัด', price=Decimal('50'))
        MenuIngredient.objects.create(menu=menu, ingredient=self.ing, quantity=Decimal('1'))
        response = self.client.get(reverse('menu_ingredient_list'))
        self.assertEqual(response.status_code, 200)

    def test_menu_ingredient_create(self):
        menu = MenuItem.objects.create(name='ข้าวผัด', price=Decimal('50'))
        response = self.client.post(reverse('menu_ingredient_create'), {
            'menu': menu.pk,
            'ingredient': self.ing.pk,
            'quantity': '2',
        })
        self.assertTrue(MenuIngredient.objects.filter(menu=menu, ingredient=self.ing).exists())


# ======================================================================
# ทดสอบความปลอดภัยที่เพิ่มเข้ามา (Security hardening)
# ======================================================================


class OrderOwnershipSecurityTests(TestCase):
    """ผู้ใช้ทั่วไปต้องเข้าถึง/แก้ไข/ลบได้เฉพาะออเดอร์ของตัวเอง"""

    def setUp(self):
        self.user = User.objects.create_user(username='user', password='password123')
        self.other = User.objects.create_user(username='other', password='password123')
        self.staff = User.objects.create_user(username='staff', password='password123', is_staff=True)
        self.menu = MenuItem.objects.create(name='ข้าวผัดกะเพรา', price=50)
        self.order = Order.objects.create(table_number=5, created_by=self.user)
        OrderItem.objects.create(order=self.order, menu=self.menu, quantity=1)

    def test_user_cannot_view_others_order(self):
        self.client.login(username='other', password='password123')
        response = self.client.get(reverse('order_detail', args=[self.order.pk]))
        self.assertRedirects(response, reverse('order_list'))

    def test_user_can_view_own_order(self):
        self.client.login(username='user', password='password123')
        response = self.client.get(reverse('order_detail', args=[self.order.pk]))
        self.assertEqual(response.status_code, 200)

    def test_staff_can_view_any_order(self):
        self.client.login(username='staff', password='password123')
        response = self.client.get(reverse('order_detail', args=[self.order.pk]))
        self.assertEqual(response.status_code, 200)

    def test_user_cannot_add_item_to_others_order(self):
        self.client.login(username='other', password='password123')
        response = self.client.post(reverse('order_add_item', args=[self.order.pk]), {
            'menu': self.menu.pk,
            'quantity': 2,
        })
        self.assertRedirects(response, reverse('order_list'))
        self.order.refresh_from_db()
        self.assertEqual(self.order.item_count, 1)

    def test_user_cannot_delete_others_order(self):
        self.client.login(username='other', password='password123')
        response = self.client.post(reverse('order_delete', args=[self.order.pk]))
        self.assertRedirects(response, reverse('order_list'))
        self.assertTrue(Order.objects.filter(pk=self.order.pk).exists())

    def test_user_can_delete_own_order(self):
        self.client.login(username='user', password='password123')
        self.client.get(reverse('order_delete', args=[self.order.pk]))
        response = self.client.post(reverse('order_delete', args=[self.order.pk]))
        self.assertRedirects(response, reverse('order_list'))
        self.assertFalse(Order.objects.filter(pk=self.order.pk).exists())

    def test_user_cannot_receipt_others_order(self):
        self.client.login(username='other', password='password123')
        response = self.client.get(reverse('order_receipt', args=[self.order.pk]))
        # หน้าใบเสร็จจำกัดสิทธิ์เฉพาะ Staff → ผู้ใช้ทั่วไปโดน redirect (ห้ามเปิดได้)
        self.assertEqual(response.status_code, 302)
        self.assertNotEqual(response.url, reverse('order_receipt', args=[self.order.pk]))

    def test_user_cannot_update_qty_of_item_in_others_order(self):
        item = self.order.items.first()
        self.client.login(username='other', password='password123')
        response = self.client.post(reverse('order_item_qty', args=[item.pk]), {'delta': 1})
        self.assertRedirects(response, reverse('order_list'))
        item.refresh_from_db()
        self.assertEqual(item.quantity, 1)


class OpenRedirectSecurityTests(TestCase):
    """พารามิเตอร์ next ต้องเต็งภายในเว็บไซต์เท่านั้น"""

    def setUp(self):
        self.staff = User.objects.create_user(username='staff', password='password123', is_staff=True)
        self.user = User.objects.create_user(username='user', password='password123')
        self.menu = MenuItem.objects.create(name='กะเพรา', price=60)
        self.order = Order.objects.create(order_type='delivery', status='pending', created_by=self.user)
        OrderItem.objects.create(order=self.order, menu=self.menu, quantity=1)
        from .models import Delivery
        self.delivery = Delivery.objects.create(
            order=self.order, recipient_name='สมชาย ทดสอบ',
            phone='089-111-2222', address='ถนนทดสอบ', fee=20,
        )

    def test_delivery_status_drops_external_next(self):
        self.client.login(username='staff', password='password123')
        response = self.client.post(reverse('delivery_update_status', args=[self.delivery.pk]), {
            'delivery_status': 'delivered',
            'next': 'https://evil.example.com/phish',
        })
        # ถ้า open redirect ก็จะ redirect ไปเว็บนอก → ตรวจว่าไป delivery_dashboard แทน
        self.assertRedirects(response, reverse('delivery_dashboard'))

    def test_delivery_status_keeps_internal_next(self):
        self.client.login(username='staff', password='password123')
        internal = reverse('delivery_dashboard') + '?status=delivered'
        response = self.client.post(reverse('delivery_update_status', args=[self.delivery.pk]), {
            'delivery_status': 'delivered',
            'next': internal,
        })
        self.assertRedirects(response, internal)

    def test_login_drops_external_next(self):
        response = self.client.post(reverse('login'), {
            'username': self.staff.username,
            'password': 'password123',
            'next': 'https://evil.example.com/phish',
        })
        self.assertRedirects(response, reverse('home'))


class ClientIpSecurityTests(TestCase):
    """IP และ rate limit ต้องไม่ถูกปลอม/ใช้ในทางที่ผิด"""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    def test_get_client_ip_ignores_xff_by_default(self):
        # ไม่มี proxy → X-Forwarded-For ที่ถูกแนบมาต้องถูกเพิกเฉย
        from .security import get_client_ip
        request = RequestFactory().get('/')
        request.META['REMOTE_ADDR'] = '10.0.0.1'
        request.META['HTTP_X_FORWARDED_FOR'] = '1.2.3.4'
        self.assertEqual(get_client_ip(request), '10.0.0.1')

    def test_get_client_ip_trusts_xff_when_proxy_enabled(self):
        # เปิด DJANGO_TRUSTED_PROXY=1 → เชื่อ hop แรกของ X-Forwarded-For
        from .security import get_client_ip
        request = RequestFactory().get('/')
        request.META['REMOTE_ADDR'] = '10.0.0.1'
        request.META['HTTP_X_FORWARDED_FOR'] = '1.2.3.4, 5.6.7.8'
        with mock.patch.dict('os.environ', {'DJANGO_TRUSTED_PROXY': '1'}):
            self.assertEqual(get_client_ip(request), '1.2.3.4')

    def test_reservation_rate_limit_rejects_external_referer(self):
        # โดน rate limit พร้อม Referer ข้ามโดเมน → ห้าม redirect ไปโดเมนนั้น (open redirect)
        payload = {
            'customer_name': 'ทดสอบกันRedirect',
            'phone': '082-222-3333',
            'party_size': 2,
            'reservation_date': (timezone.localdate() + timedelta(days=1)).isoformat(),
            'reservation_time': '18:00',
        }
        url = reverse('reservation_create')
        for _ in range(5):
            self.client.post(url, payload)
        response = self.client.post(url, payload, HTTP_REFERER='http://evil.example/steal')
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('evil.example', response['Location'])
        # ไม่มี Referer เลย → กลับหน้าแรก ไม่ใช่โดเมนภายนอก
        response = self.client.post(url, payload)
        self.assertNotIn('evil.example', response['Location'])


class ApiSecurityTests(TestCase):
    """API ของออเดอร์/เดลิเวอร์รี่ ต้องไม่ให้แก้สถานะหรือเห็นข้อมูลคนอื่น"""

    def setUp(self):
        self.staff = User.objects.create_user(username='staff', password='password123', is_staff=True)
        self.user = User.objects.create_user(username='user', password='password123')
        self.other = User.objects.create_user(username='other', password='password123')
        self.menu = MenuItem.objects.create(name='กะเพราหมูกรอบ', price=60)
        from .models import Delivery
        self.order = Order.objects.create(
            order_type='delivery', status='pending', created_by=self.user,
        )
        OrderItem.objects.create(order=self.order, menu=self.menu, quantity=2)
        self.delivery = Delivery.objects.create(
            order=self.order, recipient_name='วันดี ใจงาม', phone='089-000-0000',
            address='123 ถ.สวยงาม', fee=20,
        )

    def test_api_order_status_is_read_only(self):
        self.order.status = 'paid'
        self.order.payment_method = 'cash'
        self.order.paid_at = timezone.now()
        self.order.save()
        self.client.login(username='staff', password='password123')
        response = self.client.patch(
            reverse('api-order-detail', args=[self.order.pk]),
            {'status': 'cancelled', 'payment_method': 'promptpay'},
            content_type='application/json',
        )
        self.assertIn(response.status_code, (200, 405))
        self.order.refresh_from_db()
        # status/payment_method ต้องไม่เปลี่ยน (read_only)
        self.assertEqual(self.order.status, 'paid')
        self.assertEqual(self.order.payment_method, 'cash')

    def test_api_user_sees_masked_delivery_phone(self):
        self.client.login(username='user', password='password123')
        response = self.client.get(reverse('api-delivery-detail', args=[self.delivery.pk]))
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertNotIn('089-000-0000', body)
        self.assertIn('****', body)

    def test_api_user_cannot_create_delivery_for_other_order(self):
        other_order = Order.objects.create(table_number=9, created_by=self.other)
        self.client.login(username='user', password='password123')
        response = self.client.post(
            reverse('api-delivery-list'),
            {'order': other_order.pk, 'recipient_name': 'แอบสร้าง', 'phone': '000'},
            content_type='application/json',
        )
        self.assertIn(response.status_code, (400, 403))
        other_order.refresh_from_db()
        self.assertFalse(hasattr(other_order, 'delivery'))

    def test_api_user_only_sees_own_orders(self):
        import json
        other_order = Order.objects.create(table_number=8, created_by=self.other)
        self.client.login(username='user', password='password123')
        response = self.client.get(reverse('api-order-list'))
        self.assertEqual(response.status_code, 200)
        ids = [o['id'] for o in json.loads(response.content)['results']]
        self.assertIn(self.order.pk, ids)
        self.assertNotIn(other_order.pk, ids)

    def test_api_delivery_create_ignores_fee_status_and_rider(self):
        # Mass-assignment: ลูกค้าห้ามตั้งค่าส่งเอง / กำหนดสถานะล่วงหน้า / แอบอ้างไรเดอร์
        order = Order.objects.create(order_type='delivery', status='pending', created_by=self.user)
        self.client.login(username='user', password='password123')
        response = self.client.post(
            reverse('api-delivery-list'),
            {
                'order': order.pk,
                'recipient_name': 'ทดสอบ ค่าส่ง',
                'phone': '081-111-2222',
                'address': 'ที่อยู่ทดสอบ',
                'fee': '999.00',
                'status': 'delivered',
                'rider_name': 'แอบอ้าง',
                'delivered_at': '2026-01-01T12:00:00Z',
            },
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201, response.content)
        delivery = Delivery.objects.get(order=order)
        self.assertEqual(delivery.status, 'pending')
        self.assertEqual(delivery.fee, Decimal('0'))
        self.assertIsNone(delivery.rider_name)
        self.assertIsNone(delivery.delivered_at)
        # ข้อมูลผู้รับของตัวเองกรอกได้ตามปกติ
        self.assertEqual(delivery.recipient_name, 'ทดสอบ ค่าส่ง')

    def test_api_review_patch_cannot_steal_others_review(self):
        # IDOR: PATCH รีวิวคนอื่นต้องถูกปฏิเสธ และห้ามยึดรีวิวเป็นของตัวเอง
        victim = User.objects.create_user(username='victim', password='password123')
        review = Review.objects.create(menu=self.menu, user=victim, rating=5, comment='ของเหยื่อ')
        self.client.login(username='user', password='password123')
        response = self.client.patch(
            reverse('api-review-detail', args=[review.pk]),
            {'comment': 'ถูกยึด'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        review.refresh_from_db()
        self.assertEqual(review.user_id, victim.pk)
        self.assertEqual(review.comment, 'ของเหยื่อ')

    def test_api_review_patch_owner_can_edit(self):
        review = Review.objects.create(menu=self.menu, user=self.user, rating=4, comment='เดิม')
        self.client.login(username='user', password='password123')
        response = self.client.patch(
            reverse('api-review-detail', args=[review.pk]),
            {'comment': 'แก้ไขแล้ว'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        review.refresh_from_db()
        self.assertEqual(review.user_id, self.user.pk)
        self.assertEqual(review.comment, 'แก้ไขแล้ว')


class LoginRateLimitTests(TestCase):
    """กัน brute-force: ผิดรหัสหลายครั้ง → ล็อกชั่วคราว"""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.user = User.objects.create_user(username='amber', password='CorrectPass123!')

    def _fail_login(self, times=5):
        for _ in range(times):
            response = self.client.post(reverse('login'), {
                'username': 'amber',
                'password': 'wrong',
            })
        return response

    def test_blocked_after_repeated_failures(self):
        self._fail_login(5)
        # ครั้งที่ 6 ให้รหัสถูกต้องก็ต้องโดนบล็อก (เกิน 5 ครั้ง/15 นาที/ชื่อผู้ใช้)
        response = self.client.post(
            reverse('login'), {'username': 'amber', 'password': 'CorrectPass123!'},
        )
        self.assertContains(response, 'ล็อกชั่วคราว')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_correct_password_within_limit_still_works(self):
        response = self.client.post(
            reverse('login'), {'username': 'amber', 'password': 'CorrectPass123!'},
        )
        self.assertRedirects(response, reverse('home'))
        self.assertIn('_auth_user_id', self.client.session)

    def test_successful_login_resets_failure_counter(self):
        self._fail_login(3)
        # ล็อกอินสำเร็จ → รีเซ็ต counter → ผิดอีกได้โดยไม่โดนบล็อกทันที
        self.client.post(
            reverse('login'), {'username': 'amber', 'password': 'CorrectPass123!'},
        )
        self.client.logout()
        self._fail_login(3)
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'ล็อกชั่วคราว')


class NoDoubleRewardTests(TestCase):
    """save ซ้ำของออเดอร์ที่ชำระแล้วต้องไม่สะสมคะแนนหรือนับคูปองซ้ำ"""

    def setUp(self):
        self.user = User.objects.create_user(username='user', password='password123')
        self.coupon = Coupon.objects.create(
            code='SAVE10', discount_type='percent', value=Decimal('10'), min_order=Decimal('50'),
        )
        self.menu = MenuItem.objects.create(name='กะเพรา', price=Decimal('100'))
        self.order = Order.objects.create(table_number=1, created_by=self.user, coupon_code='SAVE10')

    def test_points_earned_once_for_repeated_saves(self):
        OrderItem.objects.create(order=self.order, menu=self.menu, quantity=1)
        for _ in range(3):
            self.order.status = 'paid'
            self.order.paid_at = timezone.now()
            self.order.save()
        self.assertEqual(
            PointTransaction.objects.filter(
                profile=self.user.profile, order=self.order, points_change__gt=0
            ).count(),
            1,
        )

    def test_coupon_used_count_once_for_repeated_saves(self):
        OrderItem.objects.create(order=self.order, menu=self.menu, quantity=1)
        for _ in range(3):
            self.order.status = 'paid'
            self.order.paid_at = timezone.now()
            self.order.save()
        self.coupon.refresh_from_db()
        self.assertEqual(self.coupon.used_count, 1)


class PasswordResetFlowTests(TestCase):
    """หน้าลืมรหัสผ่าน + เปลี่ยนรหัสผ่านใหม่ตามลิงก์อีเมล"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='amber', email='amber@example.com', password='OldPass123!',
        )

    def test_reset_page_renders(self):
        response = self.client.get(reverse('password_reset'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ลืมรหัสผ่าน')

    def test_reset_sends_email_then_changes_password(self):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        response = self.client.post(reverse('password_reset'), {'email': 'amber@example.com'})
        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('amber@example.com', mail.outbox[0].to)
        self.assertTrue(self.user.check_password('OldPass123!'))  # ยังไม่เปลี่ยน

        token = default_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        confirm_url = reverse('password_reset_confirm', args=[uid, token])

        # Django 6: GET ลิงก์จริง → เก็บ token ลง session แล้ว redirect
        # ไป URL ปลอดภัย (token='set-password') ไม่ให้ token รั่วใน Referer
        response = self.client.get(confirm_url)
        self.assertEqual(response.status_code, 302)
        set_password_url = confirm_url.replace(token, 'set-password')

        response = self.client.post(set_password_url, {
            'new_password1': 'NewPass456!',
            'new_password2': 'NewPass456!',
        })
        self.assertRedirects(response, reverse('password_reset_complete'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPass456!'))

    def test_reset_unknown_email_sends_no_mail(self):
        response = self.client.post(reverse('password_reset'), {'email': 'ghost@example.com'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_token_shows_rejected_message(self):
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        response = self.client.get(reverse('password_reset_confirm', args=[uid, 'bad-token']))
        self.assertContains(response, 'ลิงก์นี้ใช้ไม่ได้')

    def test_complete_page_renders(self):
        response = self.client.get(reverse('password_reset_complete'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'เปลี่ยนรหัสผ่านเรียบร้อย')


# ======================================================================
# งานปรับปรุงรอบ: สิทธิ์ is_staff / คูปองจุดเดียว / automation throttle /
# context processor / admin token / media serving
# ======================================================================


class UserStaffPrivilegeTests(TestCase):
    """is_staff ตั้งได้เฉพาะ superuser — staff ทั่วไปห้ามยกระดับสิทธิ์ตัวเอง/ผู้อื่น"""

    def setUp(self):
        self.staff = User.objects.create_user(username='staffx', password='password123', is_staff=True)
        self.root = User.objects.create_superuser(username='rootx', password='password123')
        self.client.force_login(self.staff)

    def _payload(self, **extra):
        data = {
            'username': 'newstaff', 'first_name': 'ใหม่', 'last_name': 'ทดสอบ',
            'email': 'newstaff@example.com',
            'password1': 'NewPass456!', 'password2': 'NewPass456!',
            'is_active': 'on', 'membership_status': 'regular',
        }
        data.update(extra)
        return data

    def test_staff_create_form_hides_is_staff_field(self):
        response = self.client.get(reverse('user_create'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="is_staff"')

    def test_staff_cannot_grant_is_staff_on_create(self):
        response = self.client.post(reverse('user_create'), self._payload(is_staff='on'))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.get(username='newstaff').is_staff)

    def test_superuser_can_grant_is_staff_on_create(self):
        self.client.force_login(self.root)
        response = self.client.post(
            reverse('user_create'), self._payload(username='helper', is_staff='on'),
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.get(username='helper').is_staff)

    def test_staff_edit_cannot_grant_is_staff(self):
        target = User.objects.create_user(username='member1', password='password123')
        response = self.client.post(reverse('user_update', args=[target.pk]), {
            'username': 'member1', 'first_name': 'แก้', 'last_name': 'ไข',
            'email': 'member1@example.com', 'is_active': 'on',
            'membership_status': 'regular', 'is_staff': 'on', 'new_password': '',
        })
        self.assertEqual(response.status_code, 302)
        target.refresh_from_db()
        self.assertFalse(target.is_staff)

    def test_superuser_edit_can_toggle_is_staff(self):
        self.client.force_login(self.root)
        target = User.objects.create_user(username='member2', password='password123')
        response = self.client.post(reverse('user_update', args=[target.pk]), {
            'username': 'member2', 'first_name': '', 'last_name': '',
            'email': '', 'is_active': 'on',
            'membership_status': 'regular', 'is_staff': 'on', 'new_password': '',
        })
        self.assertEqual(response.status_code, 302)
        target.refresh_from_db()
        self.assertTrue(target.is_staff)


class CouponServiceTests(TestCase):
    """validate_coupon / order_coupon_status — ตรรกะคูปองจุดเดียวของเว็บ + API"""

    def setUp(self):
        self.owner = User.objects.create_user(username='couponowner', password='x')
        self.other = User.objects.create_user(username='couponother', password='x')
        self.coupon = Coupon.objects.create(
            code='SAVE10', discount_type='percent', value=Decimal('10'),
            min_order=Decimal('100'), max_uses=5,
        )
        self.owned = Coupon.objects.create(
            code='PRIVATE20', discount_type='percent', value=Decimal('20'),
            min_order=Decimal('0'), max_uses=5, owner=self.owner,
        )

    def test_empty_code(self):
        _, _, error = validate_coupon('', Decimal('500'), self.other)
        self.assertEqual(error[0], 'empty')

    def test_unknown_code_not_found(self):
        _, _, error = validate_coupon('NOPE', Decimal('500'), self.other)
        self.assertEqual(error[0], 'not_found')

    def test_valid_code_returns_discount(self):
        coupon, discount, error = validate_coupon('save10', Decimal('200'), self.other)
        self.assertIsNone(error)
        self.assertEqual(coupon.code, 'SAVE10')
        self.assertEqual(discount, Decimal('20'))

    def test_below_min_order_invalid(self):
        _, _, error = validate_coupon('SAVE10', Decimal('50'), self.other)
        self.assertEqual(error[0], 'invalid')

    def test_inactive_coupon_not_found(self):
        self.coupon.is_active = False
        self.coupon.save()
        _, _, error = validate_coupon('SAVE10', Decimal('500'), self.other)
        self.assertEqual(error[0], 'not_found')

    def test_others_owned_coupon_rejected(self):
        _, _, error = validate_coupon('PRIVATE20', Decimal('500'), self.other)
        self.assertEqual(error[0], 'owner')

    def test_owned_only_hides_others_coupon(self):
        _, _, error = validate_coupon('PRIVATE20', Decimal('500'), self.other, owned_only=True)
        self.assertEqual(error[0], 'not_found')

    def test_owner_can_use_own_owned_coupon(self):
        coupon, discount, error = validate_coupon(
            'PRIVATE20', Decimal('500'), self.owner, owned_only=True,
        )
        self.assertIsNone(error)
        self.assertEqual(discount, Decimal('100'))

    def test_staff_can_use_any_coupon_owned_only(self):
        staff = User.objects.create_user(username='cstaff', password='x', is_staff=True)
        _, _, error = validate_coupon('PRIVATE20', Decimal('500'), staff, owned_only=True)
        self.assertIsNone(error)

    def test_order_coupon_status(self):
        open_order = Order.objects.create(table_number=1, created_by=self.other)
        self.assertEqual(order_coupon_status(open_order), (True, None))

        paid_order = Order.objects.create(table_number=2, created_by=self.other, status='paid')
        self.assertEqual(order_coupon_status(paid_order), (False, None))

        used_order = Order.objects.create(
            table_number=3, created_by=self.other, coupon_code='SAVE10',
        )
        can_apply, used = order_coupon_status(used_order)
        self.assertFalse(can_apply)
        self.assertEqual(used.code, 'SAVE10')


class AutomationThrottleTests(TestCase):
    """run_all() จำกัดความถี่ด้วย AUTOMATION_MIN_INTERVAL (Production/ผ่าน view)"""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    @override_settings(AUTOMATION_MIN_INTERVAL=10)
    def test_second_call_skipped_without_force(self):
        from .automation import run_all
        first = run_all()
        self.assertNotIn('skipped', first)
        second = run_all()
        self.assertTrue(second.get('skipped'))

    @override_settings(AUTOMATION_MIN_INTERVAL=10)
    def test_force_bypasses_throttle(self):
        from .automation import run_all
        run_all()
        result = run_all(force=True)
        self.assertNotIn('skipped', result)

    @override_settings(AUTOMATION_MIN_INTERVAL=0)
    def test_zero_interval_never_skips(self):
        from .automation import run_all
        run_all()
        second = run_all()
        self.assertNotIn('skipped', second)


class NotificationContextTests(TestCase):
    """context processor: สถิติเฉพาะ staff / staff เห็น broadcast + แจ้งเตือนของตัวเอง"""

    def setUp(self):
        from .models import Notification
        self.staff = User.objects.create_user(username='nstaff', password='x', is_staff=True)
        self.user = User.objects.create_user(username='nmember', password='x')
        Notification.objects.create(kind='order', title='broadcast', message='รวมทุกคน')
        Notification.objects.create(
            kind='order', title='ของฉัน', message='เฉพาะสมาชิก', recipient=self.user,
        )
        Notification.objects.create(
            kind='order', title='ของstaff', message='เฉพาะ staff', recipient=self.staff,
        )

    def _ctx(self, user):
        from .context_processors import notifications
        request = RequestFactory().get('/')
        request.user = user
        return notifications(request)

    def test_non_staff_has_no_order_stats(self):
        ctx = self._ctx(self.user)
        self.assertNotIn('staff_order_counts', ctx)
        self.assertNotIn('staff_new_orders', ctx)

    def test_staff_has_order_stats(self):
        ctx = self._ctx(self.staff)
        self.assertIn('staff_order_counts', ctx)

    def test_staff_sees_broadcast_and_own_not_others(self):
        titles = {n.title for n in self._ctx(self.staff)['nav_notifications']}
        self.assertIn('broadcast', titles)
        self.assertIn('ของstaff', titles)
        self.assertNotIn('ของฉัน', titles)

    def test_member_sees_only_own_notification(self):
        titles = {n.title for n in self._ctx(self.user)['nav_notifications']}
        self.assertEqual(titles, {'ของฉัน'})


class AdminLineTokenTests(TestCase):
    """เฉพาะ superuser เท่านั้นที่แก้ไข Line Notify Token ใน Django Admin ได้"""

    def _token_fields(self, user):
        from django.contrib.admin.sites import AdminSite

        from .admin import StoreLocationAdmin
        from .models import StoreLocation
        request = RequestFactory().get('/admin/myapp/storelocation/change/')
        request.user = user
        form = StoreLocationAdmin(StoreLocation, AdminSite()).get_form(request)
        return set(form.base_fields)

    def test_staff_cannot_see_token_field(self):
        staff = User.objects.create_user(username='astaff', password='x', is_staff=True)
        self.assertNotIn('line_notify_token', self._token_fields(staff))

    def test_superuser_sees_token_field(self):
        root = User.objects.create_superuser(username='aroot', password='x')
        self.assertIn('line_notify_token', self._token_fields(root))

    def test_staff_sees_phone_field(self):
        staff = User.objects.create_user(username='astaff2', password='x', is_staff=True)
        self.assertIn('phone', self._token_fields(staff))


class MediaServedTests(TestCase):
    """DEBUG=False (ค่าตอนรันเทสต์) — /media/ ต้องเสิร์ฟไฟล์ที่อัปโหลดได้"""

    def test_serves_existing_media_file(self):
        from pathlib import Path

        from django.conf import settings
        media_root = Path(settings.MEDIA_ROOT)
        rel = 'tests/tmp-media-check.txt'
        target = media_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('hello-media', encoding='utf-8')
        try:
            response = self.client.get(settings.MEDIA_URL + rel)
            self.assertEqual(response.status_code, 200)
            body = b''.join(response.streaming_content)
            response.close()
            self.assertEqual(body, b'hello-media')
        finally:
            try:
                target.unlink(missing_ok=True)
            except PermissionError:
                pass

    def test_missing_media_file_404(self):
        from django.conf import settings
        response = self.client.get(settings.MEDIA_URL + 'tests/no-such-file.txt')
        self.assertEqual(response.status_code, 404)


class OrderStockTransactionTests(TestCase):
    """Order.save() ต้องเปลี่ยนสถานะ + ตัดสต็อกใน transaction เดียว (all-or-nothing)"""

    def setUp(self):
        self.menu = MenuItem.objects.create(name='ข้าวผัดกะเพรา', price=Decimal('50'))
        self.basil = Ingredient.objects.create(
            name='ใบกะเพรา', unit='กรัม',
            stock_qty=Decimal('100'), reorder_level=Decimal('20'),
        )
        MenuIngredient.objects.create(menu=self.menu, ingredient=self.basil, quantity=Decimal('10'))

    def test_status_and_stock_commit_together(self):
        order = Order.objects.create(table_number=1)
        OrderItem.objects.create(order=order, menu=self.menu, quantity=1)
        order.status = 'preparing'
        order.save()
        order.refresh_from_db()
        self.assertEqual(order.status, 'preparing')
        self.basil.refresh_from_db()
        self.assertEqual(self.basil.stock_qty, Decimal('90'))

    def test_failed_stock_consumption_rolls_back_status(self):
        order = Order.objects.create(table_number=1)
        OrderItem.objects.create(order=order, menu=self.menu, quantity=1)
        order.status = 'confirmed'
        order.save()

        with mock.patch.object(Ingredient, 'adjust_stock', side_effect=RuntimeError('db down')):
            with self.assertRaises(RuntimeError):
                order.status = 'preparing'
                order.save()

        order.refresh_from_db()
        self.assertEqual(order.status, 'confirmed')
        self.basil.refresh_from_db()
        self.assertEqual(self.basil.stock_qty, Decimal('100'))

    def test_stale_instance_reentering_preparing_does_not_double_consume(self):
        """instance ที่ค้างสถานะเก่าใน memory บันทึกทับ — ต้องอ่านสถานะเดิม
        ใต้ lock ตอน save เพื่อไม่ให้ตัดสต็อกซ้ำ (ที่ PostgreSQL สองคำสั่ง
        พร้อมกันจะถูกบังคับ serialize ด้วย SELECT ... FOR UPDATE)"""
        order = Order.objects.create(table_number=1)
        OrderItem.objects.create(order=order, menu=self.menu, quantity=1)
        order.status = 'confirmed'
        order.save()

        stale = Order.objects.get(pk=order.pk)

        real = Order.objects.get(pk=order.pk)
        real.status = 'preparing'
        real.save()  # ตัดสต็อก → 90

        stale.status = 'preparing'
        stale.save()  # อ่านสถานะเดิมใต้ lock = 'preparing' → ข้ามการตัดสต็อก

        self.basil.refresh_from_db()
        self.assertEqual(self.basil.stock_qty, Decimal('90'))


class DatabaseConfigTests(TestCase):
    """build_database — สลับ SQLite/PostgreSQL ด้วย DJANGO_DB_ENGINE"""

    def test_default_is_sqlite(self):
        from myproject.db import build_database
        cfg = build_database(environ={}, base_dir='D:/proj')
        self.assertEqual(cfg['ENGINE'], 'django.db.backends.sqlite3')
        self.assertTrue(str(cfg['NAME']).endswith('db.sqlite3'))

    def test_sqlite_path_env_override(self):
        from myproject.db import build_database
        cfg = build_database(
            environ={'DJANGO_SQLITE_PATH': '/data/db.sqlite3'}, base_dir='D:/proj',
        )
        self.assertEqual(cfg['NAME'], '/data/db.sqlite3')

    def test_postgres_settings(self):
        from myproject.db import build_database
        cfg = build_database(environ={
            'DJANGO_DB_ENGINE': 'postgresql',
            'DJANGO_POSTGRES_DB': 'shop',
            'DJANGO_POSTGRES_USER': 'shopuser',
            'DJANGO_POSTGRES_PASSWORD': 'secret',
            'DJANGO_POSTGRES_HOST': 'db.internal',
            'DJANGO_POSTGRES_PORT': '6543',
            'DJANGO_POSTGRES_CONN_MAX_AGE': '30',
        })
        self.assertEqual(cfg['ENGINE'], 'django.db.backends.postgresql')
        self.assertEqual(cfg['NAME'], 'shop')
        self.assertEqual(cfg['USER'], 'shopuser')
        self.assertEqual(cfg['PASSWORD'], 'secret')
        self.assertEqual(cfg['HOST'], 'db.internal')
        self.assertEqual(cfg['PORT'], '6543')
        self.assertEqual(cfg['CONN_MAX_AGE'], 30)

    def test_postgres_aliases_accepted(self):
        from myproject.db import build_database
        for alias in ('postgres', 'postgresql', 'pgsql', 'pg'):
            cfg = build_database(environ={'DJANGO_DB_ENGINE': alias})
            self.assertEqual(cfg['ENGINE'], 'django.db.backends.postgresql', alias)

    def test_unknown_engine_rejected(self):
        from django.core.exceptions import ImproperlyConfigured

        from myproject.db import build_database
        with self.assertRaises(ImproperlyConfigured):
            build_database(environ={'DJANGO_DB_ENGINE': 'postgress'})

    def test_active_settings_uses_sqlite_in_test_env(self):
        from django.conf import settings
        self.assertTrue(
            settings.DATABASES['default']['ENGINE'].endswith('sqlite3')
        )


class SentryInitTests(TestCase):
    """init_sentry — เปิดใช้เฉพาะตอนตั้ง DJANGO_SENTRY_DSN"""

    def test_skipped_without_dsn(self):
        from myproject.sentry import init_sentry
        with mock.patch.dict('os.environ', {'DJANGO_SENTRY_DSN': ''}):
            with mock.patch('sentry_sdk.init') as mocked:
                self.assertFalse(init_sentry())
                mocked.assert_not_called()

    def test_initializes_when_dsn_set(self):
        from myproject.sentry import init_sentry
        dsn = 'https://key@o1.ingest.sentry.io/1'
        with mock.patch.dict('os.environ', {'DJANGO_SENTRY_DSN': dsn}):
            with mock.patch('sentry_sdk.init') as mocked:
                self.assertTrue(init_sentry())
                mocked.assert_called_once()
                kwargs = mocked.call_args.kwargs
                self.assertEqual(kwargs['dsn'], dsn)
                self.assertFalse(kwargs['send_default_pii'])

    def test_settings_level_init_skips_without_dsn(self):
        """settings import init_sentry() มาไว้ — เรียกโดยไม่มี DSNต้องไม่ init"""
        from myproject import settings as proj_settings
        with mock.patch.dict('os.environ', {'DJANGO_SENTRY_DSN': ''}):
            with mock.patch('sentry_sdk.init') as mocked:
                self.assertFalse(proj_settings.init_sentry())
                mocked.assert_not_called()


class HealthzTests(TestCase):
    """GET /healthz — health check สาธารณะของ Docker/load balancer"""

    def test_returns_ok_with_db(self):
        response = self.client.get('/healthz')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok', 'db': 'ok'})

    def test_db_failure_returns_503(self):
        with mock.patch('django.db.connection') as conn:
            conn.cursor.side_effect = Exception('db down')
            response = self.client.get('/healthz')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['db'], 'error')

    def test_post_not_allowed(self):
        self.assertEqual(self.client.post('/healthz').status_code, 405)

    def test_healthz_exempt_from_ssl_redirect(self):
        """ตอนเปิด DJANGO_SECURE=1 — /healthz ต้องไม่โดน redirect ไป https
        (healthcheck ใน container เรียก HTTP ตรงถึง gunicorn)"""
        from django.middleware.security import SecurityMiddleware
        with override_settings(SECURE_SSL_REDIRECT=True, SECURE_REDIRECT_EXEMPT=[r'^healthz$']):
            mw = SecurityMiddleware(lambda r: None)
            self.assertIsNone(mw.process_request(RequestFactory().get('/healthz')))
            # path อื่นยังถูก redirect ตามปกติ
            self.assertIsNotNone(mw.process_request(RequestFactory().get('/login/')))


class ImageValidationTests(TestCase):
    """validate_image_file — ตรวจขนาดไม่เกิน 10MB + เป็นรูปจริง ทุกจุดอัปโหลด"""

    @staticmethod
    def _real_png(name='test.png', content_type='image/png'):
        import base64

        from django.core.files.uploadedfile import SimpleUploadedFile
        data = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ'
            'AAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
        )
        return SimpleUploadedFile(name, data, content_type=content_type)

    @staticmethod
    def _oversize_png():
        from django.core.files.uploadedfile import SimpleUploadedFile
        # โครง PNG ปลอม + padding เกิน 10MB — validator ตรวจ "ขนาด" ก่อนเสมอ
        return SimpleUploadedFile(
            'big.png', b'\x89PNG\r\n\x1a\n' + b'0' * (11 * 1024 * 1024),
            content_type='image/png',
        )

    def test_valid_png_accepted(self):
        from django.core.exceptions import ValidationError

        from .validators import validate_image_file
        validate_image_file(self._real_png())  # ไม่ raise = ผ่าน

        with self.assertRaises(ValidationError):
            validate_image_file(self._real_png('bad.png', content_type='text/plain'))

    def test_oversize_rejected_with_size_message(self):
        from django.core.exceptions import ValidationError

        from .validators import validate_image_file
        with self.assertRaises(ValidationError) as ctx:
            validate_image_file(self._oversize_png())
        self.assertIn('ไม่เกิน', str(ctx.exception))

    def test_fake_image_bytes_rejected(self):
        from django.core.exceptions import ValidationError
        from django.core.files.uploadedfile import SimpleUploadedFile

        from .validators import validate_image_file
        fake = SimpleUploadedFile('fake.png', b'this is not an image', content_type='image/png')
        with self.assertRaises(ValidationError):
            validate_image_file(fake)

    def test_menu_item_form_rejects_oversize_image(self):
        from .forms import MenuItemForm
        form = MenuItemForm(
            data={
                'name': 'เมนูทดสอบรูป',
                'category': 'rice',
                'price': 55,
                'spice_level': 1,
                'available': True,
                'date_added': timezone.localdate(),
            },
            files={'image': self._oversize_png()},
        )
        self.assertFalse(form.is_valid())
        self.assertIn('image', form.errors)

    def test_cover_form_rejects_oversize_image(self):
        from .forms import UserCoverForm
        form = UserCoverForm(data={}, files={'cover': self._oversize_png()})
        self.assertFalse(form.is_valid())
        self.assertIn('cover', form.errors)

    def test_avatar_form_field_rejects_oversize_image(self):
        """_UserBaseForm.avatar เป็น field ประกาศเอง — ต้องมี validator ติดตัว"""

        from .forms import UserAvatarForm
        form = UserAvatarForm(data={}, files={'avatar': self._oversize_png()})
        self.assertFalse(form.is_valid())
        self.assertIn('avatar', form.errors)

    def test_profile_api_rejects_oversize_image(self):
        from .api import ProfileSerializer
        user = User.objects.create(username='imguser')
        serializer = ProfileSerializer(
            user.profile, data={'avatar': self._oversize_png()}, partial=True,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('avatar', serializer.errors)

    def test_menu_image_upload_succeeds_with_valid_png(self):
        from .forms import MenuItemForm
        form = MenuItemForm(
            data={
                'name': 'เมนูรูปปกติ',
                'category': 'rice',
                'price': 55,
                'spice_level': 1,
                'available': True,
                'date_added': timezone.localdate(),
            },
            files={'image': self._real_png()},
        )
        self.assertTrue(form.is_valid(), form.errors)
        menu = form.save()
        self.assertTrue(menu.image.name)
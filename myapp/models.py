from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from .validators import validate_image_file

# ======================================================================
# ส่วนข้อมูลเมนู (Menu)
# ======================================================================


class Category(models.Model):
    """หมวดหมู่เมนูอาหาร"""

    name = models.CharField(max_length=100, unique=True, verbose_name='ชื่อหมวดหมู่')
    slug = models.SlugField(max_length=100, unique=True, verbose_name='Slug')
    sort_order = models.PositiveIntegerField(default=0, verbose_name='ลำดับการแสดง')
    is_active = models.BooleanField(default=True, verbose_name='เปิดใช้งาน')

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = 'หมวดหมู่'
        verbose_name_plural = 'หมวดหมู่'

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    """โมเดลเมนูอาหารสำหรับกรณีศึกษาระบบจัดการเมนูร้านอาหาร"""

    CATEGORY_CHOICES = [
        ('rice', 'ผัด/ข้าวราดแกง'),
        ('soup', 'แกง/ต้มยำ'),
        ('fried', 'อาหารทอด'),
        ('drink', 'เครื่องดื่ม'),
        ('dessert', 'ของหวาน'),
    ]

    SPICE_CHOICES = [
        (0, 'ไม่เผ็ด'),
        (1, 'เผ็ดนิดหน่อย 🌶️'),
        (2, 'เผ็ดกลาง 🌶️🌶️'),
        (3, 'เผ็ดมาก 🌶️🌶️🌶️'),
    ]

    name = models.CharField(max_length=100, verbose_name='ชื่อเมนู')
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='rice',
        db_index=True,
        verbose_name='หมวดหมู่',
    )
    category_fk = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='menu_items',
        verbose_name='หมวดหมู่ (ใหม่)',
    )
    price = models.DecimalField(max_digits=8, decimal_places=2, verbose_name='ราคา (บาท)')
    spice_level = models.IntegerField(
        choices=SPICE_CHOICES,
        default=0,
        verbose_name='ระดับความเผ็ด',
    )
    description = models.TextField(blank=True, null=True, verbose_name='รายละเอียดเมนู')
    available = models.BooleanField(default=True, db_index=True, verbose_name='พร้อมขาย')
    date_added = models.DateField(default=timezone.localdate, verbose_name='วันที่เพิ่มเมนู')
    image = models.ImageField(
        upload_to='menu_images/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='รูปภาพเมนู',
        validators=[validate_image_file],
    )

    class Meta:
        ordering = ['-date_added', 'name']
        verbose_name = 'เมนูอาหาร'
        verbose_name_plural = 'เมนูอาหาร'

    def __str__(self):
        return self.name


class AddOn(models.Model):
    """เครื่องเคียงในเมนู เช่น ข้าวเพิ่ม ไข่ดาว (คิดครั้งละ 1 ราคา ต่อรายการ)"""

    name = models.CharField(max_length=100, verbose_name='ชื่อเครื่องเคียง')
    price = models.DecimalField(max_digits=8, decimal_places=2, verbose_name='ราคา (บาท)')
    is_active = models.BooleanField(default=True, verbose_name='เปิดใช้งาน')

    class Meta:
        ordering = ['name']
        verbose_name = 'เครื่องเคียง'
        verbose_name_plural = 'เครื่องเคียง'

    def __str__(self):
        return f'{self.name} (+{self.price:,.0f}฿)'


# ======================================================================
# ส่วนออเดอร์และการสั่ง (Order)
# ======================================================================


class DailySequence(models.Model):
    """ลำดับรหัสออเดอร์ประจำวัน — นับเลขใหม่ทุกวัน (รีเซ็ตอัตโนมัติ)"""

    date = models.DateField(unique=True, verbose_name='วันที่')
    last_number = models.PositiveIntegerField(default=0, verbose_name='ลำดับล่าสุด')

    class Meta:
        verbose_name = 'ลำดับออเดอร์ประจำวัน'
        verbose_name_plural = 'ลำดับออเดอร์ประจำวัน'

    def __str__(self):
        return f'{self.date} #{self.last_number}'


class Order(models.Model):
    """ออเดอร์อาหารของแต่ละโต๊ะ"""

    STATUS_CHOICES = [
        ('open', 'กำลังทาน'),
        ('preparing', 'กำลังเตรียม'),
        ('ready', 'พร้อมเสิร์ฟ'),
        ('served', 'เสิร์ฟแล้ว'),
        ('paid', 'ชำระแล้ว'),
        ('cancelled', 'ยกเลิก'),
        ('pending', 'รอดำเนินการ'),
        ('confirmed', 'ยืนยันแล้ว'),
        ('completed', 'เสร็จสิ้น'),
        ('refunded', 'คืนเงิน'),
    ]

    PAYMENT_METHODS = [
        ('cash', 'เงินสด'),
        ('transfer', 'โอนเงิน'),
        ('qr', 'QR PromptPay'),
    ]

    ORDER_TYPE_CHOICES = [
        ('dine_in', 'ทานในร้าน'),
        ('delivery', 'เดลิเวอร์รี่'),
    ]

    order_type = models.CharField(
        max_length=10,
        choices=ORDER_TYPE_CHOICES,
        default='dine_in',
        db_index=True,
        verbose_name='ประเภทออเดอร์',
    )
    table_number = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name='เลขโต๊ะ',
        help_text='เฉพาะออเดอร์ทานในร้าน (เดลิเวอร์รี่ไม่ต้องกรอก)',
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='open',
        db_index=True,
        verbose_name='สถานะ',
    )
    status_changed_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
        verbose_name='เวลาที่สถานะเปลี่ยนล่าสุด',
    )
    payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_METHODS,
        null=True,
        blank=True,
        verbose_name='วิธีชำระเงิน',
    )
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='เวลาที่ชำระ',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='เวลาที่สั่ง')
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name='สั่งโดย',
    )
    daily_number = models.PositiveIntegerField(
        default=0,
        editable=False,
        verbose_name='เลขที่ประจำวัน',
    )
    daily_code = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        editable=False,
        verbose_name='รหัสออเดอร์ (รีเซ็ตทุกวัน)',
    )
    # --- คูปองส่วนลด (snapshot เมื่อใช้ กันคูปองปิดแล้วยอดออเดอร์เก่าซึม) ---
    coupon_code = models.CharField(
        max_length=50,
        blank=True,
        default='',
        editable=False,
        verbose_name='รหัสคูปองที่ใช้',
    )
    coupon_discount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        editable=False,
        verbose_name='ส่วนลดคูปอง (บาท)',
    )

    # --- การชำระเงินด้วย QR (ฝั่งลูกค้า) ---
    qr_payment_requested_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='เวลาที่ลูกค้าแจ้งชำระด้วย QR',
    )
    qr_payment_reference = models.CharField(
        max_length=80,
        blank=True,
        default='',
        verbose_name='เลขอ้างอิง/หมายเหตุการชำระ QR',
    )
    qr_payment_slip = models.ImageField(
        upload_to='payment_slips/%Y/%m/',
        blank=True,
        null=True,
        validators=[validate_image_file],
        verbose_name='สลิป/หลักฐานการชำระ QR',
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'ออเดอร์'
        verbose_name_plural = 'ออเดอร์'

    def __str__(self):
        return f'ออเดอร์ {self.display_code} ({self.table_display})'

    def save(self, *args, **kwargs):
        """สร้างรหัสออเดอร์อัตโนมัติ รูปแบบ YYYYMMDD-ลำดับ (รีเซ็ตทุกวัน)
        + อัปเดตเวลาที่สถานะเปลี่ยนล่าสุด (status_changed_at)

        ทั้งการอ่านสถานะเดิม การบันทึก และการตัดสต็อก อยู่ใน transaction
        เดียวกันพร้อมล็อกแถว (SELECT ... FOR UPDATE บน PostgreSQL) กันไม่ให้
        คำสั่งที่รันพร้อมกัน 2 ตัวอ่านสถานะเดิมซ้ำกันจนตัดสต็อก/นับคูปองซ้ำ
        (SQLite ไม่มี FOR UPDATE — เป็น best effort แต่ก็เขียนทีละไฟล์อยู่แล้ว)
        """
        from django.db import transaction

        if not self.daily_code:
            today = timezone.localdate()
            with transaction.atomic():
                counter, _ = DailySequence.objects.select_for_update().get_or_create(date=today)
                counter.last_number = models.F('last_number') + 1
                counter.save()
                counter.refresh_from_db()
                self.daily_number = counter.last_number
                self.daily_code = f"{today:%Y%m%d}-{self.daily_number:03d}"

        with transaction.atomic():
            if self.pk:
                old = (
                    Order.objects.select_for_update()
                    .filter(pk=self.pk)
                    .values_list('status', flat=True)
                    .first()
                )
            else:
                old = None

            # บันทึกเวลาสถานะเปลี่ยนล่าสุด (เฉพาะตอนสร้างหรือเมื่อสถานะเปลี่ยน)
            if old is None or old != self.status:
                self.status_changed_at = timezone.now()
            elif self.status_changed_at is None:
                self.status_changed_at = timezone.now()

            super().save(*args, **kwargs)

            # ตัดสต็อกวัตถุดิบเมื่อออเดอร์เริ่มเข้าครัว (ครั้งแรกที่เปลี่ยนเป็น preparing)
            # ถ้าตัดสต็อกล้มเหลว → rollback ทั้งสถานะและสต็อก (all-or-nothing)
            if self.status == 'preparing' and old != 'preparing':
                consume_stock_for_order(self)

    @property
    def display_code(self):
        """รหัสที่แสดงในระบบ (แบบสั้น) — ใช้ลำดับประจำวัน ถ้ายังไม่มีใช้เลข PK แทน (ข้อมูลเก่า)"""
        if self.daily_code:
            return f'#{self.daily_number:03d}'
        return f'#{self.pk}'

    @property
    def table_display(self):
        """ข้อความแสดงโต๊ะหรือเดลิเวอร์รี่"""
        if self.order_type == 'delivery' or not self.table_number:
            return 'เดลิเวอร์รี่'
        return f'โต๊ะ {self.table_number}'

    @property
    def delivery_fee(self):
        """ค่าบริการจัดส่ง (ถ้าเป็นออเดอร์เดลิเวอร์รี่)"""
        try:
            return self.delivery.fee or Decimal('0')
        except Delivery.DoesNotExist:
            return Decimal('0')

    @property
    def total_price(self):
        """ราคารวมก่อนหักส่วนลดสมาชิก"""
        subtotal = sum(item.subtotal for item in self.items.all())
        return subtotal + self.delivery_fee

    @property
    def membership_discount_percent(self):
        """ส่วนลดสมาชิก (%) ตามสถานะของคนสั่ง (ถ้ามีโปรไฟล์)"""
        profile = getattr(self.created_by, 'profile', None)
        return profile.discount_percent if profile else 0

    @property
    def membership_discount_amount(self):
        """ส่วนลดเฉพาะสมาชิก (ก่อนรวมคูปอง)"""
        return self.total_price * (Decimal(str(self.membership_discount_percent)) / 100)

    @property
    def discount_amount(self):
        """จำนวนเงินส่วนลดรวม = คูปอง + ส่วนลดสมาชิก"""
        return self.membership_discount_amount + (self.coupon_discount or Decimal('0'))

    @property
    def discounted_total(self):
        """ราคารวมสุทธิ หลังหักส่วนลดทั้งหมด (คูปอง + สมาชิก)"""
        total = self.total_price - self.discount_amount
        return max(total, Decimal('0'))

    @property
    def item_count(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def is_paid(self):
        return self.status == 'paid'


class OrderItem(models.Model):
    """รายการเมนูที่สั่งภายในออเดอร์"""

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='ออเดอร์',
    )
    menu = models.ForeignKey(MenuItem, on_delete=models.CASCADE, verbose_name='เมนู')
    quantity = models.PositiveSmallIntegerField(default=1, verbose_name='จำนวน')
    notes = models.TextField(blank=True, null=True, verbose_name='หมายเหตุ')
    addons = models.ManyToManyField(
        'AddOn',
        blank=True,
        related_name='order_items',
        verbose_name='เครื่องเคียง',
    )

    class Meta:
        ordering = ['pk']
        verbose_name = 'รายการสั่ง'
        verbose_name_plural = 'รายการสั่ง'

    def __str__(self):
        return f'{self.menu.name} x{self.quantity}'

    @property
    def addons_price(self):
        return sum(addon.price for addon in self.addons.all())

    @property
    def subtotal(self):
        return self.menu.price * self.quantity + self.addons_price


class Delivery(models.Model):
    """ข้อมูลการจัดส่ง (เดลิเวอร์รี่) สำหรับออเดอร์ — 1 ออเดอร์มี 1 ชุดข้อมูลจัดส่ง"""

    DELIVERY_STATUS_CHOICES = [
        ('pending', 'รอจัดส่ง'),
        ('accepted', 'ไรเดอร์รับงาน'),
        ('picking_up', 'กำลังไปรับอาหาร'),
        ('out_for_delivery', 'กำลังจัดส่ง'),
        ('delivered', 'จัดส่งแล้ว'),
        ('cancelled', 'ยกเลิก'),
    ]

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name='delivery',
        verbose_name='ออเดอร์',
    )
    recipient_name = models.CharField(max_length=100, verbose_name='ชื่อผู้รับ')
    phone = models.CharField(max_length=20, verbose_name='เบอร์โทรศัพท์')
    address = models.TextField(verbose_name='ที่อยู่จัดส่ง')
    # พิกัดตำแหน่งปลายทาง (GPS) — ใช้คำนวณระยะทางและเปิดเส้นทางนำทาง
    recipient_lat = models.FloatField(
        null=True,
        blank=True,
        verbose_name='ละติจูด (ปลายทาง)',
        help_text='ได้จากแผนที่ — กดเลือกตำแหน่งบนแผนที่',
    )
    recipient_lng = models.FloatField(
        null=True,
        blank=True,
        verbose_name='ลองจิจูด (ปลายทาง)',
        help_text='ได้จากแผนที่ — กดเลือกตำแหน่งบนแผนที่',
    )
    distance_km = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='ระยะทาง (กิโลเมตร)',
        help_text='คำนวณอัตโนมัติจากพิกัดของร้าน → ปลายทาง',
    )
    fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        verbose_name='ค่าจัดส่ง (บาท)',
        help_text='พร้อมแก้เองได้ หรือกดคำนวณอัตโนมัติจากระยะทาง',
    )
    status = models.CharField(
        max_length=20,
        choices=DELIVERY_STATUS_CHOICES,
        default='pending',
        db_index=True,
        verbose_name='สถานะการจัดส่ง',
    )
    status_changed_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
        verbose_name='เวลาที่สถานะจัดส่งเปลี่ยนล่าสุด',
    )
    assigned_rider = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='delivery_jobs',
        db_index=True,
        verbose_name='ไรเดอร์ที่รับงาน',
        help_text='บริหารจัดการกำหนดได้ หรือไรเดอร์รับงานเอง',
    )
    rider_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='ชื่อไรเดอร์',
    )
    rider_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='เบอร์ไรเดอร์',
    )
    tracking_note = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='หมายเลขติดตาม / หมายเหตุ',
    )
    accepted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='เวลาที่ไรเดอร์รับงาน',
    )
    picked_up_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='เวลาที่รับอาหารแล้ว',
    )
    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='เวลาที่จัดส่งสำเร็จ',
    )
    fee_locked = models.BooleanField(
        default=False,
        verbose_name='ล็อกค่าส่งที่ตั้งเอง',
        help_text='ถ้าเปิด ระบบจะไม่คำนวณค่าส่งทับค่าเดิม (ใช้เมื่อพนักงานตั้งค่าส่งเอง)',
    )
    release_count = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='จำนวนครั้งที่ปล่อยงานอัตโนมัติ',
        help_text='จำนวนครั้งที่งานถูกปล่อยออกจากไรเดอร์เพราะไม่คืบหน้า (กันวนซ้ำ)',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='เวลาที่บันทึก')

    class Meta:
        verbose_name = 'ข้อมูลเดลิเวอร์รี่'
        verbose_name_plural = 'ข้อมูลเดลิเวอร์รี่'

    def __str__(self):
        return f'Delivery #{self.order.display_code} -> {self.recipient_name}'

    def save(self, *args, **kwargs):
        """บันทึกอัตโนมัติ:
        - ถ้ามีพิกัดครบและไม่ได้ล็อกค่าส่ง ให้คำนวณระยะทาง + ค่าส่งเองทุกครั้ง
        - อัปเดตเวลาที่สถานะเปลี่ยนล่าสุด (status_changed_at)
        """
        if self.order_id and self.recipient_lat is not None and self.recipient_lng is not None \
                and not self.fee_locked:
            self.update_distance_and_fee(save=False)

        if self.pk:
            try:
                old = Delivery.objects.only('status').get(pk=self.pk).status
            except Delivery.DoesNotExist:
                old = None
        else:
            old = None
        if old is None or old != self.status:
            self.status_changed_at = timezone.now()
        elif self.status_changed_at is None:
            self.status_changed_at = timezone.now()

        super().save(*args, **kwargs)

    def calc_distance_km(self):
        """คำนวณระยะทางตรง (Haversine) ระหว่างร้านกับปลายทาง หน่วย: กิโลเมตร"""
        store = StoreLocation.get_setting()
        if not (store.lat and store.lng and self.recipient_lat and self.recipient_lng):
            return None
        return haversine_km(store.lat, store.lng, self.recipient_lat, self.recipient_lng)

    def calc_fee(self):
        """คำนวณค่าส่งอัตโนมัติ = ค่าธรรมเนียมฐาน + อัตราต่อกิโลเมตร"""
        store = StoreLocation.get_setting()
        distance = self.calc_distance_km()
        if distance is None:
            return None
        base = float(store.fee_base or 0)
        per_km = float(store.fee_per_km or 0)
        total = base + per_km * distance
        return max(total, base)

    def update_distance_and_fee(self, save=True):
        """อัปเดตระยะทาง + ค่าส่งอัตโนมัติจากพิกัด (คิดเงื่อนไขฟรีค่าส่งด้วย)"""
        distance = self.calc_distance_km()
        if distance is not None:
            self.distance_km = Decimal(str(round(distance, 2)))
            store = StoreLocation.get_setting()
            subtotal = sum(item.subtotal for item in self.order.items.all())
            # สมาชิกที่ได้ฟรีค่าส่ง (พรีเมียม) หรือยอดเกินเกณฑ์ฟรีค่าส่งของร้าน
            profile = getattr(self.order.created_by, 'profile', None)
            if (profile and profile.free_delivery) or (
                store.free_delivery_over and subtotal >= store.free_delivery_over
            ):
                fee = Decimal('0')
            else:
                base = float(store.fee_base or 0)
                per_km = float(store.fee_per_km or 0)
                fee = max(base + per_km * distance, base)
            self.fee = Decimal(str(round(fee, 2)))
        if save:
            self.save(update_fields=['distance_km', 'fee'])

    def geocode_from_address(self, save=True):
        """ค้นหาพิกัดปลายทางจากที่อยู่จัดส่ง (API ภายนอก: Nominatim/OpenStreetMap)
        แล้วให้ Delivery.save() คำนวณระยะทาง + ค่าส่งให้อัตโนมัติ
        คืน `(lat, lng)` ถ้าจับพิกัดได้ / `None` ถ้าหาไม่เจอหรือ API ล่ม
        """
        from .services import geocode_address

        coords = geocode_address(self.address)
        if coords is None:
            return None
        self.recipient_lat, self.recipient_lng = coords
        self.fee_locked = False  # ปล่อยให้ระบบคำนวณค่าส่งใหม่จากพิกัดที่เพิ่งได้
        if save:
            self.save()
        return coords


def haversine_km(lat1, lng1, lat2, lng2):
    """ระยะทางระหว่าง 2 พิกัดบนพื้นโลก (สูตร Haversine) หน่วย: กิโลเมตร"""
    import math

    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlng / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))


# ======================================================================
# ส่วนผู้ใช้งาน (User)
# ======================================================================


class Profile(models.Model):
    """โปรไฟล์ผู้ใช้ — เก็บข้อมูลเพิ่มเติมนอกเหนือจาก User model"""

    MEMBERSHIP_CHOICES = [
        ('regular', 'สมาชิกทั่วไป'),
        ('vip', 'VIP'),
        ('premium', 'พรีเมียม'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    membership_status = models.CharField(
        max_length=10,
        choices=MEMBERSHIP_CHOICES,
        default='regular',
        verbose_name='สถานะสมาชิก',
    )
    points = models.PositiveIntegerField(
        default=0,
        verbose_name='คะแนนสะสม',
        help_text='คะแนนสะสมเพิ่มตามสถานะสมาชิก (อัตราตามสถานะ)',
    )
    max_favorites = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name='จำนวนเมนูโปรดสูงสุด',
        help_text='ปล่อยว่าง = ใช้ค่าตามสถานะ (ทั่วไป 5 / VIP 10 / พรีเมียม 20)',
    )
    avatar = models.ImageField(
        upload_to='avatars/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='รูปโปรไฟล์',
        validators=[validate_image_file],
    )
    cover = models.ImageField(
        upload_to='covers/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='รูปปกโปรไฟล์',
        validators=[validate_image_file],
    )
    is_rider = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name='เป็นไรเดอร์',
        help_text='ถ้าเปิดใช้งาน ผู้ใช้คนนี้จะเข้าถึงระบบเดลิเวอร์รี่แยก (ไรเดอร์) ได้',
    )

    class Meta:
        verbose_name = 'โปรไฟล์ผู้ใช้'
        verbose_name_plural = 'โปรไฟล์ผู้ใช้'

    def __str__(self):
        return f'Profile of {self.user.username}'

    # ------------------------------------------------------------------
    # สิทธิประโยชน์ตามสถานะสมาชิก (ทั่วไป / VIP / พรีเมียม)
    # ------------------------------------------------------------------
    MEMBERSHIP_RULES = {
        # สถานะ: (ส่วนลด %, อัตราคะแนนต่อ 1 บาท, จำนวนเมนูโปรดสูงสุด, ฟรีค่าส่งหรือไม่)
        'regular': (0, 1, 5, False),
        'vip': (5, 1.5, 10, False),
        'premium': (10, 2, 20, True),
    }

    @property
    def discount_percent(self):
        """ส่วนลด (%) ตามสถานะสมาชิก — ตั้งเองไม่ได้ เพราะกำหนดตามสถานะ"""
        return self.MEMBERSHIP_RULES[self.membership_status][0]

    @property
    def points_rate(self):
        """อัตราคะแนนสะสมที่ได้ต่อการสั่งทุก 1 บาท ตามสถานะสมาชิก"""
        return self.MEMBERSHIP_RULES[self.membership_status][1]

    @property
    def default_max_favorites(self):
        """จำนวนเมนูโปรดสูงสุดตามสถานะสมาชิก"""
        return self.MEMBERSHIP_RULES[self.membership_status][2]

    @property
    def effective_max_favorites(self):
        """จำนวนเมนูโปรดสูงสุดที่ใช้จริง (เก็บเองได้ ถ้าไม่ตั้งใช้ตามสถานะ)"""
        return self.max_favorites if self.max_favorites is not None else self.default_max_favorites

    @property
    def free_delivery(self):
        """ได้ฟรีค่าส่งหรือไม่ ตามสถานะสมาชิก"""
        return self.MEMBERSHIP_RULES[self.membership_status][3]

    def earn_points(self, amount, order=None, reason=''):
        """เพิ่มคะแนนสะสมจากยอดที่ชำระ (หลังหักส่วนลดแล้ว)
        บันทึกลง ledger (PointTransaction) เพื่อให้ผู้ใช้เห็นประวัติ
        คืนจำนวนคะแนนที่เพิ่ม เหมาะสำหรับเรียกเมื่อชำระเงิน
        """
        rate = Decimal(str(self.points_rate))
        earned = int(amount * rate)
        if earned <= 0:
            return 0
        Profile.objects.filter(pk=self.pk).update(points=models.F('points') + earned)
        self.refresh_from_db()
        PointTransaction.objects.create(
            profile=self,
            points_change=earned,
            balance_after=self.points,
            order=order,
            reason=reason or f'สะสมคะแนนอัตโนมัติ (อัตรา {self.points_rate:g} คะแนน/บาท)',
        )
        return earned

    def redeem_points(self, cost, reason='', reward=None, order=None):
        """ตัดคะแนนเพื่อใช้สิทธิ์ประโยชน์ — กัน race condition ด้วย F()
        คืน True เมื่อสำเร็จ (คะแนนพอ + หักเรียบร้อย) / False เมื่อคะแนนไม่พอ
        """
        if cost <= 0:
            return False
        updated = Profile.objects.filter(
            pk=self.pk, points__gte=cost
        ).update(points=models.F('points') - cost)
        if not updated:
            return False
        self.refresh_from_db()
        PointTransaction.objects.create(
            profile=self,
            points_change=-cost,
            balance_after=self.points,
            reward=reward,
            order=order,
            reason=reason,
        )
        return True


# ======================================================================
# ส่วนตั้งค่าระบบ / หน้าแรก (Site)
# ======================================================================


class StoreLocation(models.Model):
    """ตำแหน่งของร้าน (สำหรับคำนวณระยะทางและเปิดเส้นทางนำทาง)
    เป็นแบบ Singleton: มีได้แค่ 1 เรคคอร์ดเท่านั้น (pk=1)
    """

    name = models.CharField(
        max_length=100,
        default='อร่อยเกินเบอร์',
        verbose_name='ชื่อสาขา',
    )
    lat = models.FloatField(
        verbose_name='ละติจูด (ร้าน)',
        default=16.4539,
        help_text='พิกัดของร้าน — กดเลือกตำแหน่งบนแผนที่',
    )
    lng = models.FloatField(
        verbose_name='ลองจิจูด (ร้าน)',
        default=99.5123,
        help_text='พิกัดของร้าน — กดเลือกตำแหน่งบนแผนที่',
    )
    address = models.TextField(
        blank=True,
        verbose_name='ที่อยู่ร้าน',
        help_text='แสดงให้ไรเดอร์ใช้เป็นจุดนัดรับอาหาร',
    )
    phone = models.CharField(
        max_length=30,
        blank=True,
        default='089-XXX-XXXX',
        verbose_name='เบอร์โทรศัพท์',
    )
    fee_base = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=10,
        verbose_name='ค่าส่งพื้นฐาน (บาท)',
    )
    fee_per_km = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=5,
        verbose_name='อัตราค่าส่งต่อกิโลเมตร (บาท)',
    )
    free_delivery_over = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='ยอดสั่งที่ฟรีค่าส่ง (บาท)',
        help_text='ถ้ายอดรวมออเดอร์ตั้งแต่จำนวนนี้ คิดค่าส่ง 0 บาท (ปล่อยว่าง = ไม่มีเงื่อนไข)',
    )
    # --- การจัดสรรงานอัตโนมัติ (Auto Dispatch) ---
    auto_assign_enabled = models.BooleanField(
        default=True,
        verbose_name='จัดสรรงานให้ไรเดอร์อัตโนมัติ',
        help_text='ถ้าเปิด ระบบจะมอบงานที่ค้างเกินเวลารอให้ไรเดอร์ที่ว่างที่สุดอัตโนมัติ',
    )
    auto_assign_grace_minutes = models.PositiveSmallIntegerField(
        default=3,
        verbose_name='เวลารอรับงาน (นาที)',
        help_text='เปิดโอกาสให้ไรเดอร์รับงานเองก่อน พ้นเวลานี้แล้วระบบจะจัดสรรให้เอง',
    )
    auto_release_minutes = models.PositiveSmallIntegerField(
        default=10,
        verbose_name='เวลาสำรองงานค้าง (นาที)',
        help_text='ถ้าไรเดอร์รับงานแล้วไม่คืบหน้าเกินเวลานี้ ระบบจะปล่อยงานออกให้ไรเดอร์อื่น',
    )
    # --- ระบบชำระเงินออนไลน์ (PromptPay) ---
    promptpay_id = models.CharField(
        max_length=13,
        blank=True,
        default='',
        verbose_name='PromptPay ID (เบอร์โทร/เลขบัตร)',
        help_text='เช่น 0801234567 หรือ 13 หลัก — ใช้สร้าง QR สำหรับชำระเงินอัตโนมัติ',
    )
    # --- การแจ้งเตือน Line Notify / Email ---
    line_notify_token = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name='Line Notify Token',
        help_text='ไปขอ token ได้ที่ https://notify-bot.line.me — ปล่อยว่าง = ปิดการแจ้งเตือน Line',
    )
    notification_email = models.EmailField(
        blank=True,
        default='',
        verbose_name='อีเมลรับการแจ้งเตือน',
        help_text='ส่งการแจ้งเตือนออเดอร์/จองโต๊ะ/รีวิวใหม่ถึงอีเมลนี้ (ต้องตั้งค่า EMAIL_* ในการผลิตจริง)',
    )
    notify_order = models.BooleanField(
        default=True,
        verbose_name='แจ้งเตือนเมื่อมีออเดอร์ใหม่',
    )
    notify_reservation = models.BooleanField(
        default=True,
        verbose_name='แจ้งเตือนเมื่อมีการจองโต๊ะใหม่',
    )
    notify_review = models.BooleanField(
        default=True,
        verbose_name='แจ้งเตือนเมื่อมีรีวิวใหม่',
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name='อัปเดตล่าสุด')

    class Meta:
        verbose_name = 'ตำแหน่งร้าน (เดลิเวอร์รี่)'
        verbose_name_plural = 'ตำแหน่งร้าน (เดลิเวอร์รี่)'

    def __str__(self):
        return f'ตำแหน่งร้าน: {self.name}'

    @classmethod
    def get_setting(cls):
        """ดึงค่า singleton — สร้างเรคคอร์ดแรกถ้ายังไม่มี"""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def maps_url(self):
        """ลิงก์เปิดเส้นทางไปร้านใน Google Maps"""
        return f'https://www.google.com/maps/dir/?api=1&destination={self.lat},{self.lng}'


# ======================================================================
# ระบบอัตโนมัติ (Autopilot / แจ้งเตือน)
# ======================================================================


class AutomationSettings(models.Model):
    """ตั้งค่านาฬิกาเดินสถานะอัตโนมัติ (Autopilot) แบบ Singleton
    กำหนดเวลารอของแต่ละขั้นตอน (นาที) ระบบจะเดินสถานะเองจนจบรอบ
    """

    enabled = models.BooleanField(
        default=False,
        verbose_name='เปิดระบบอัตโนมัติทั้งหมด (Autopilot)',
        help_text='เปิดแล้วระบบจะเดินสถานะออเดอร์/จัดส่ง และมอบงานให้ไรเดอร์เอง',
    )
    preparing_minutes = models.PositiveSmallIntegerField(
        default=5, verbose_name='เวลาเตรียมอาหาร (นาที)',
        help_text='กี่นาทีหลังเปิดออเดอร์ จึงขึ้นเป็นกำลังเตรียม',
    )
    ready_minutes = models.PositiveSmallIntegerField(
        default=10, verbose_name='เวลาเสร็จพร้อมเสิร์ฟ (นาที)',
        help_text='กี่นาทีหลังกำลังเตรียม จึงเสร็จพร้อมเสิร์ฟ',
    )
    served_minutes = models.PositiveSmallIntegerField(
        default=15, verbose_name='เวลาเสิร์ฟ/ทาน (นาที)',
        help_text='กี่นาทีหลังเสร็จพร้อมเสิร์ฟ จึงถือว่าเสิร์ฟแล้วและจบออเดอร์',
    )
    auto_pay = models.BooleanField(
        default=False,
        verbose_name='ตัดชำระเงินอัตโนมัติเมื่อทานเสร็จ',
        help_text='เปิดแล้วระบบจะปิดบิล (ชำระแล้ว) ให้เองเมื่อครบเวลาทานในร้านหรือส่งสำเร็จ',
    )
    picking_up_minutes = models.PositiveSmallIntegerField(
        default=4, verbose_name='เวลาไปรับอาหาร (นาที)',
        help_text='กี่นาทีหลังรับงาน จึงถึงที่ร้าน (ไปรับอาหาร)',
    )
    out_for_delivery_minutes = models.PositiveSmallIntegerField(
        default=8, verbose_name='เวลากำลังจัดส่ง (นาที)',
        help_text='กี่นาทีหลังไปรับอาหาร จึงกำลังจัดส่ง',
    )
    delivered_minutes = models.PositiveSmallIntegerField(
        default=14, verbose_name='เวลาจัดส่งสำเร็จ (นาที)',
        help_text='กี่นาทีหลังกำลังจัดส่ง จึงถือว่าจัดส่งสำเร็จ',
    )
    auto_earn_points = models.BooleanField(
        default=True,
        verbose_name='สะสมคะแนนสมาชิกอัตโนมัติ',
        help_text='เมื่อออเดอร์ชำระเสร็จ ส่วนลด/คะแนนตามสถานะสมาชิกจะถูกคิดให้เอง',
    )

    class Meta:
        verbose_name = 'ตั้งค่าระบบอัตโนมัติ'
        verbose_name_plural = 'ตั้งค่าระบบอัตโนมัติ'

    def __str__(self):
        state = 'เปิด' if self.enabled else 'ปิด'
        return f'ระบบอัตโนมัติ: {state}'

    @classmethod
    def get_setting(cls):
        """ดึงค่า singleton — สร้างเรคคอร์ดแรกถ้ายังไม่มี"""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Notification(models.Model):
    """การแจ้งเตือนในระบบ (สร้างอัตโนมัติจาก automation engine)"""

    KIND_CHOICES = [
        ('order', 'ออเดอร์'),
        ('delivery', 'การจัดส่ง'),
        ('rider', 'ไรเดอร์'),
        ('report', 'รายงาน'),
        ('system', 'ระบบ'),
    ]

    recipient = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True,
        db_index=True,
        verbose_name='ผู้รับ',
        help_text='ปล่อยว่าง = แจ้งเตือนทุกคน (Staff)',
    )
    kind = models.CharField(
        max_length=10,
        choices=KIND_CHOICES,
        default='system',
        verbose_name='ประเภท',
    )
    title = models.CharField(max_length=200, verbose_name='หัวข้อ')
    message = models.TextField(blank=True, verbose_name='รายละเอียด')
    link = models.CharField(max_length=300, blank=True, verbose_name='ลิงก์')
    is_read = models.BooleanField(default=False, db_index=True, verbose_name='อ่านแล้ว')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='เวลาสร้าง')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'การแจ้งเตือน'
        verbose_name_plural = 'การแจ้งเตือน'

    def __str__(self):
        return self.title


class HomeImage(models.Model):
    """รูปภาพหน้าต้อนรับ (Hero) บนหน้าแรก — เปลี่ยนได้เฉพาะผู้ดูแล (Staff)
    เป็นแบบ Singleton: มีได้แค่ 1 เรคคอร์ดเท่านั้น (pk=1)
    """

    hero_image = models.ImageField(
        upload_to='home_images/%Y/%m/',
        blank=True,
        null=True,
        verbose_name='รูปภาพหน้าต้อนรับ',
        help_text='ถ้าไม่ตั้ง จะใช้รูปเริ่มต้นของระบบ',
        validators=[validate_image_file],
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name='อัปเดตล่าสุด')

    class Meta:
        verbose_name = 'รูปภาพหน้าต้อนรับ'
        verbose_name_plural = 'รูปภาพหน้าต้อนรับ'

    def __str__(self):
        if self.hero_image:
            return f'ภาพหน้าต้อนรับ (อัปเดตล่าสุด: {self.updated_at:%d/%m/%Y %H:%M})'
        return 'ภาพหน้าต้อนรับ (ใช้รูปเริ่มต้นของระบบ)'

    @classmethod
    def get_setting(cls):
        """ดึงค่า singleton — สร้างเรคคอร์ดแรกถ้ายังไม่มี"""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


# ======================================================================
# ระบบคูปอง / โปรโมชั่น
# ======================================================================


class Coupon(models.Model):
    """คูปองส่วนลด — ใช้ได้กับออเดอร์ที่มียอดถึงเกณฑ์ขั้นต่ำ"""

    TYPE_CHOICES = [
        ('percent', 'ส่วนลดเป็นเปอร์เซ็นต์ (%)'),
        ('fixed', 'ส่วนลดเป็นเงิน (บาท)'),
    ]

    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name='รหัสคูปอง',
        help_text='ลูกค้ากรอกรหัสนี้ตอนสั่งอาหาร (เช่น HAPPY10)',
    )
    owner = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='owned_coupons',
        verbose_name='เจ้าของคูปอง',
        help_text='ถ้าระบุ (เช่น คูปองที่ได้จากการแลกคะแนน) จะใช้ได้เฉพาะผู้ใช้นี้',
    )
    discount_type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        default='percent',
        verbose_name='ประเภทส่วนลด',
    )
    value = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name='จำนวนส่วนลด',
        help_text='เปอร์เซ็นต์ (เช่น 10) หรือบาท (เช่น 50)',
    )
    min_order = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        verbose_name='ยอดขั้นต่ำที่ใช้ได้ (บาท)',
        help_text='ยอดรวมออเดอร์ต้องอย่างน้อยเท่านี้ (ก่อนหักส่วนลด)'
    )
    max_uses = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='จำนวนครั้งที่ใช้ได้ทั้งหมด',
        help_text='ปล่อยว่าง = ใช้ได้ไม่จำกัด',
    )
    used_count = models.PositiveIntegerField(
        default=0,
        verbose_name='จำนวนครั้งที่ใช้แล้ว',
    )
    valid_from = models.DateField(
        default=timezone.localdate,
        verbose_name='วันที่เริ่มใช้ได้',
    )
    valid_until = models.DateField(
        null=True,
        blank=True,
        verbose_name='วันหมดอายุ',
        help_text='ปล่อยว่าง = ไม่มีวันหมดอายุ',
    )
    is_active = models.BooleanField(default=True, db_index=True, verbose_name='เปิดใช้งาน')

    class Meta:
        ordering = ['-valid_from']
        verbose_name = 'คูปอง'
        verbose_name_plural = 'คูปอง'

    def __str__(self):
        label = f'{self.value}%' if self.discount_type == 'percent' else f'{self.value} บาท'
        return f'{self.code} ({label})'

    def save(self, *args, **kwargs):
        self.code = (self.code or '').strip().upper()
        super().save(*args, **kwargs)

    def is_valid(self, order_price=None):
        """คูปองนี้ใช้ได้หรือไม่ (วันที่ / จำนวนครั้ง / ยอดขั้นต่ำ / ปิดใช้งาน)"""
        today = timezone.localdate()
        if not self.is_active:
            return False
        if self.valid_from and today < self.valid_from:
            return False
        if self.valid_until and today > self.valid_until:
            return False
        if self.max_uses is not None and self.used_count >= self.max_uses:
            return False
        if order_price is not None and order_price < self.min_order:
            return False
        return True

    def discount_for(self, order_price):
        """คำนวณส่วนลดจากยอดรวม (บาท) — ไม่เกินยอดรวม"""
        if self.discount_type == 'percent':
            amount = order_price * (self.value / Decimal('100'))
        else:
            amount = self.value
        return max(min(amount, order_price), Decimal('0'))

    def mark_used(self):
        """เพิ่มจำนวนครั้งที่ใช้แล้ว"""
        self.used_count = models.F('used_count') + 1
        self.save(update_fields=['used_count'])


# ======================================================================
# ระบบสต็อก / วัตถุดิบ
# ======================================================================


class Ingredient(models.Model):
    """รายการวัตถุดิบ + คงคลัง (ตัดสต็อกอัตโนมัติเมื่อออเดอร์เข้าครัว)"""

    name = models.CharField(max_length=100, unique=True, verbose_name='ชื่อวัตถุดิบ')
    unit = models.CharField(max_length=20, default='หน่วย', verbose_name='หน่วย',
                            help_text='เช่น กรัม, กิโล, ลูก, กล่อง')
    stock_qty = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='คงเหลือ',
    )
    reorder_level = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='ระดับเตือนสต็อก',
        help_text='ถ้าคงเหลือต่ำกว่าค่านี้ จะขึ้นเตือน "ใกล้หมด"',
    )
    is_active = models.BooleanField(default=True, db_index=True, verbose_name='เปิดใช้งาน')

    class Meta:
        ordering = ['name']
        verbose_name = 'วัตถุดิบ'
        verbose_name_plural = 'วัตถุดิบ'

    def __str__(self):
        return f'{self.name} ({self.stock_qty} {self.unit})'

    @property
    def is_low_stock(self):
        if not self.is_active:
            return False
        return self.reorder_level > 0 and self.stock_qty <= self.reorder_level

    @property
    def is_out_stock(self):
        return self.is_active and self.stock_qty <= 0

    def adjust_stock(self, delta):
        """เพิ่ม/ลดสต็อก (delta ติดลบ = ตัดออก) — คงเหลือไม่ติดลบ"""
        # คำนวณใน SQL เพื่อกัน race condition ระหว่างพนักงานหลายคน
        Ingredient.objects.filter(pk=self.pk).update(
            stock_qty=models.F('stock_qty') + delta
        )
        # ตัดค่าติดลบเป็น 0 ด้วย conditional UPDATE (atomic ที่ database —
        # ไม่ต้องอ่านค่ามาก่อนแล้วค่อยเขียน เหมือนสูตรเดิม)
        Ingredient.objects.filter(pk=self.pk, stock_qty__lt=0).update(stock_qty=0)
        self.refresh_from_db()


class MenuIngredient(models.Model):
    """สัดส่วนวัตถุดิบที่ใช้ต่อเมนู (Recipe) — ใช้ตัดสต็อกอัตโนมัติ"""

    menu = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name='ingredients',
        verbose_name='เมนู',
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='used_in',
        verbose_name='วัตถุดิบ',
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='ปริมาณที่ใช้ (ต่อ 1 จาน)',
    )

    class Meta:
        unique_together = ('menu', 'ingredient')
        ordering = ['menu__name', 'ingredient__name']
        verbose_name = 'สัดส่วนวัตถุดิบ'
        verbose_name_plural = 'สัดส่วนวัตถุดิบ'

    def __str__(self):
        return f'{self.menu.name}: {self.ingredient.name} {self.quantity} {self.ingredient.unit}'


def consume_stock_for_order(order):
    """ตัดสต็อกทั้งหมดของออเดอร์ (เมนู x จำนวน) — เรียกเมื่อออเดอร์เริ่มเข้าครัว

    วนตาม pk ของ order item และ ingredient เพื่อให้ทุกออเดอร์ล็อกตาราง
    วัตถุดิบในลำดับเดียวกัน กัน deadlock ตอนสองออเดอร์ตัดสต็อกพร้อมกัน
    """
    consumed = 0
    for item in order.items.order_by('pk'):
        recipes = item.menu.ingredients.select_related('ingredient').order_by(
            'ingredient_id', 'pk'
        )
        for recipe in recipes:
            used = recipe.quantity * item.quantity
            recipe.ingredient.adjust_stock(-used)
            consumed += 1
    return consumed


# ======================================================================
# ระบบจองโต๊ะ (Reservation)
# ======================================================================


class Reservation(models.Model):
    """การจองโต๊ะของลูกค้า — จองล่วงหน้าผ่านหน้าเว็บได้"""

    STATUS_CHOICES = [
        ('requested', 'รอยืนยัน'),
        ('confirmed', 'ยืนยันแล้ว'),
        ('seated', 'นั่งแล้ว'),
        ('completed', 'เสร็จสิ้น'),
        ('cancelled', 'ยกเลิก'),
        ('no_show', 'ไม่มา'),
    ]

    customer_name = models.CharField(max_length=100, verbose_name='ชื่อผู้จอง')
    phone = models.CharField(max_length=20, verbose_name='เบอร์โทรศัพท์')
    party_size = models.PositiveSmallIntegerField(default=1, verbose_name='จำนวนคน')
    table_number = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name='เลขโต๊ะ (ถ้าระบุได้)',
    )
    reservation_date = models.DateField(verbose_name='วันที่จอง')
    reservation_time = models.TimeField(verbose_name='เวลาที่จอง')
    notes = models.TextField(blank=True, verbose_name='หมายเหตุ')
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='requested',
        db_index=True,
        verbose_name='สถานะ',
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reservations',
        verbose_name='จองโดย',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='เวลาที่จอง')

    class Meta:
        ordering = ['reservation_date', 'reservation_time']
        verbose_name = 'การจองโต๊ะ'
        verbose_name_plural = 'การจองโต๊ะ'

    def __str__(self):
        t = self.reservation_time
        time_str = t.strftime('%H:%M') if hasattr(t, 'strftime') else str(t)
        return f'จอง {self.customer_name} ({self.party_size} คน) {self.reservation_date:%d/%m/%Y} {time_str}'


# ======================================================================
# ระบบรีวิว / ให้คะแนนเมนู
# ======================================================================


class Review(models.Model):
    """รีวิว + คะแนน (1-5 ดาว) ของเมนู — ผู้ใช้ให้ได้เมนูละครั้ง"""

    menu = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='เมนู',
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='ผู้รีวิว',
    )
    rating = models.PositiveSmallIntegerField(
        default=5,
        verbose_name='คะแนน (1-5)',
        help_text='5 = อร่อยมากที่สุด, 1 = ต้องปรับปรุง'
    )
    comment = models.TextField(
        blank=True,
        verbose_name='ความคิดเห็น',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='เวลารีวิว')

    class Meta:
        unique_together = ('menu', 'user')
        ordering = ['-created_at']
        verbose_name = 'รีวิว'
        verbose_name_plural = 'รีวิว'

    def __str__(self):
        return f'{self.menu.name} ★{self.rating} โดย {self.user.username}'

    def save(self, *args, **kwargs):
        if not (1 <= self.rating <= 5):
            from django.core.exceptions import ValidationError
            raise ValidationError({'rating': 'คะแนนต้องอยู่ระหว่าง 1-5'})
        super().save(*args, **kwargs)


class PointReward(models.Model):
    """รายการสิทธิ์ประโยชน์ที่แลกได้ด้วยคะแนนสะสม (เช่น ส่วนลด / คูปอง)"""

    TYPE_CHOICES = [
        ('percent', 'ส่วนลดเป็นเปอร์เซ็นต์ (%)'),
        ('fixed', 'ส่วนลดเป็นเงิน (บาท)'),
    ]

    name = models.CharField(max_length=100, verbose_name='ชื่อสิทธิ์')
    description = models.TextField(blank=True, verbose_name='รายละเอียด')
    points_cost = models.PositiveIntegerField(verbose_name='คะแนนที่ต้องใช้')
    discount_type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        default='fixed',
        verbose_name='ประเภทส่วนลด',
    )
    value = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name='มูลค่าส่วนลด',
        help_text='% ถ้าเป็นแบบเปอร์เซ็นต์, บาท ถ้าเป็นแบบเงิน',
    )
    min_order = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        verbose_name='ยอดขั้นต่ำ (บาท)',
    )
    is_active = models.BooleanField(default=True, verbose_name='เปิดใช้งาน')

    class Meta:
        ordering = ['points_cost', 'id']
        verbose_name = 'สิทธิ์แลกคะแนน'
        verbose_name_plural = 'สิทธิ์แลกคะแนน'

    def __str__(self):
        return f'{self.name} ({self.points_cost} คะแนน)'


class PointTransaction(models.Model):
    """ประวัติการได้/ใช้คะแนนสะสม (ledger) กันการใช้สิทธิ์ซ้ำซ้อน"""

    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name='point_transactions',
        verbose_name='สมาชิก',
    )
    points_change = models.IntegerField(
        verbose_name='จำนวนคะแนน (+สะสม / -ใช้)',
        help_text='ค่าบวก = สะสม, ค่าลบ = ใช้สิทธิ์',
    )
    balance_after = models.PositiveIntegerField(verbose_name='ยอดคงเหลือหลังรายการ')
    reason = models.CharField(max_length=200, verbose_name='เหตุผล')
    reward = models.ForeignKey(
        PointReward,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name='สิทธิ์ที่แลก',
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='point_transactions',
        verbose_name='ออเดอร์',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='เวลา')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'รายการคะแนน'
        verbose_name_plural = 'รายการคะแนน'

    def __str__(self):
        return (
            f'{self.profile.user.username} '
            f'({self.points_change:+d}) เหลือ {self.balance_after} - {self.reason}'
        )

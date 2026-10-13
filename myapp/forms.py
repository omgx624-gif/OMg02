from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone

from .models import (
    AddOn,
    Category,
    Coupon,
    Delivery,
    HomeImage,
    Ingredient,
    MenuIngredient,
    MenuItem,
    Order,
    Profile,
    Reservation,
    Review,
    StoreLocation,
    haversine_km,
)
from .validators import validate_image_file


class MenuItemForm(forms.ModelForm):
    """ฟอร์มจาก Model สำหรับเพิ่ม/แก้ไขเมนูอาหาร"""

    class Meta:
        model = MenuItem
        fields = ['name', 'category', 'price', 'spice_level', 'description',
                  'available', 'date_added', 'image']
        labels = {
            'name': 'ชื่อเมนู',
            'category': 'หมวดหมู่',
            'price': 'ราคา (บาท)',
            'spice_level': 'ระดับความเผ็ด',
            'description': 'รายละเอียดเมนู',
            'available': 'พร้อมขาย',
            'date_added': 'วันที่เพิ่มเมนู',
            'image': 'รูปภาพเมนู',
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'เช่น ข้าวผัดกะเพราหมูสับ',
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00',
            }),
            'spice_level': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'อธิบายรายละเอียดของเมนู วัตถุดิบ หรือจุดเด่นของรสชาติ',
            }),
            'available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'date_added': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def clean_name(self):
        """ตรวจสอบว่าชื่อเมนูไม่ซ้ำกัน"""
        name = self.cleaned_data.get('name')
        if name:
            qs = MenuItem.objects.filter(name__iexact=name.strip())
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('มีเมนูชื่อนี้อยู่ในระบบแล้ว กรุณาใช้ชื่ออื่น')
        return name

    def clean_price(self):
        """ตรวจสอบว่าราคาต้องมากกว่า 0"""
        price = self.cleaned_data.get('price')
        if price is not None and price <= 0:
            raise forms.ValidationError('ราคาต้องมากกว่า 0 บาท')
        return price


class OrderForm(forms.ModelForm):
    """ฟอร์มเปิดออเดอร์ใหม่ — เลือกทานในร้าน (กรอกเลขโต๊ะ) หรือเดลิเวอร์รี่"""

    class Meta:
        model = Order
        fields = ['order_type', 'table_number']
        labels = {
            'order_type': 'ประเภทออเดอร์',
            'table_number': 'เลขโต๊ะ',
        }
        widgets = {
            'order_type': forms.Select(attrs={'class': 'form-select'}),
            'table_number': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '999',
                'placeholder': 'เช่น 5',
            }),
        }

    def clean_table_number(self):
        table_number = self.cleaned_data.get('table_number')
        order_type = self.cleaned_data.get('order_type') or self.data.get('order_type', 'dine_in')
        if order_type == 'delivery':
            return None
        if table_number is None:
            raise forms.ValidationError('กรุณากรอกเลขโต๊ะ (1-999) สำหรับออเดอร์ทานในร้าน')
        if table_number <= 0:
            raise forms.ValidationError('เลขโต๊ะต้องมากกว่า 0')
        return table_number


class DeliveryForm(forms.ModelForm):
    """ฟอร์มกรอก/แก้ไขข้อมูลการจัดส่ง (เดลิเวอร์รี่)"""

    class Meta:
        model = Delivery
        fields = [
            'recipient_name',
            'phone',
            'address',
            'recipient_lat',
            'recipient_lng',
            'distance_km',
            'fee',
            'assigned_rider',
            'rider_name',
            'rider_phone',
            'tracking_note',
        ]
        labels = {
            'recipient_name': 'ชื่อผู้รับ',
            'phone': 'เบอร์โทรศัพท์',
            'address': 'ที่อยู่จัดส่ง',
            'recipient_lat': 'ละติจูด (ปลายทาง)',
            'recipient_lng': 'ลองจิจูด (ปลายทาง)',
            'distance_km': 'ระยะทาง (กิโลเมตร)',
            'fee': 'ค่าจัดส่ง (บาท)',
            'assigned_rider': 'ไรเดอร์',
            'rider_name': 'ชื่อไรเดอร์',
            'rider_phone': 'เบอร์ไรเดอร์',
            'tracking_note': 'หมายเลขติดตาม / หมายเหตุ',
        }
        widgets = {
            'recipient_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'เช่น สมชาย ใจดี',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'เช่น 089-123-4567',
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'บ้านเลขที่ ถนน แขวง/เขต จังหวัด รหัสไปรษณีย์',
            }),
            'recipient_lat': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'recipient_lng': forms.NumberInput(attrs={'class': 'form-control', 'step': 'any'}),
            'distance_km': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'readonly': 'readonly'}),
            'fee': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01', 'min': '0', 'placeholder': '0.00',
            }),
            'assigned_rider': forms.Select(attrs={'class': 'form-select'}),
            'rider_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'เช่น ไรเดอร์มนตรี'}),
            'rider_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'เช่น 098-XXX-XXXX'}),
            'tracking_note': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'เลขพัสดุ, ป้ายจุดสังเกต ฯลฯ'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assigned_rider'].queryset = User.objects.filter(
            profile__is_rider=True
        ).order_by('username')
        self.fields['assigned_rider'].required = False
        self.fields['assigned_rider'].empty_label = '-- ยังไม่กำหนด / ให้ไรเดอร์รับเอง --'

    def clean_fee(self):
        fee = self.cleaned_data.get('fee')
        if fee is None:
            fee = 0
        if fee < 0:
            raise forms.ValidationError('ค่าจัดส่งต้องไม่น้อยกว่า 0 บาท')
        return fee

    def clean(self):
        cleaned = super().clean()
        lat = cleaned.get('recipient_lat')
        lng = cleaned.get('recipient_lng')
        if lat is not None and lng is not None:
            if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                self.add_error('recipient_lat', 'พิกัดไม่ถูกต้อง กรุณาเลือกตำแหน่งบนแผนที่ใหม่')

        # ตรวจจับว่าเจ้าหน้าที่ตั้งค่าส่งเองหรือปล่อยให้ระบบคำนวณอัตโนมัติ
        # - ถ้ามีพิกัด + ค่ากรอกเบี่ยงเบนจากค่าอัตโนมัติ (และไม่ใช่ 0/ว่าง) → ล็อกค่าไว้
        # - กรณีอื่น → ปล่อยให้ระบบคำนวณเองทุกครั้งที่บันทึก
        fee = cleaned.get('fee')
        store = StoreLocation.get_setting()
        if (
            lat is not None
            and lng is not None
            and fee is not None
            and float(fee) > 0
        ):
            distance = haversine_km(store.lat, store.lng, lat, lng)
            expected = max(
                float(store.fee_base or 0) + float(store.fee_per_km or 0) * distance,
                float(store.fee_base or 0),
            )
            self.instance.fee_locked = abs(float(fee) - expected) > 0.01
        else:
            self.instance.fee_locked = False
        return cleaned


class OrderItemForm(forms.Form):
    """ฟอร์มเพิ่มเมนูลงออเดอร์"""

    menu = forms.ModelChoiceField(
        queryset=MenuItem.objects.filter(available=True),
        label='เลือกเมนู',
        empty_label='-- เลือกเมนูที่ต้องการสั่ง --',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    quantity = forms.IntegerField(
        min_value=1,
        max_value=99,
        initial=1,
        label='จำนวน (จาน/แก้ว)',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '99'}),
    )
    addons = forms.ModelMultipleChoiceField(
        queryset=AddOn.objects.filter(is_active=True),
        required=False,
        label='เครื่องเคียง (คิดครั้งละ 1 ราคา ต่อรายการ)',
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
    )
    notes = forms.CharField(
        label='หมายเหตุ',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'เช่น ไม่ใส่พริก เผ็ดพิเศษ'}),
    )


class AddOnForm(forms.ModelForm):
    """ฟอร์มเพิ่ม/แก้ไขเครื่องเคียง"""

    class Meta:
        model = AddOn
        fields = ['name', 'price', 'is_active']
        labels = {
            'name': 'ชื่อเครื่องเคียง',
            'price': 'ราคา (บาท)',
            'is_active': 'เปิดใช้งาน',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'เช่น ข้าวเพิ่ม, ไข่ดาว'}),
            'price': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01', 'min': '0', 'placeholder': '0.00',
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price <= 0:
            raise forms.ValidationError('ราคาต้องมากกว่า 0 บาท')
        return price

class UserAvatarForm(forms.ModelForm):
    """ฟอร์มแก้ไขรูปโปรไฟล์ของผู้ใช้เอง"""

    class Meta:
        model = Profile
        fields = ['avatar']
        labels = {
            'avatar': 'รูปโปรไฟล์',
        }
        widgets = {
            'avatar': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }


class UserCoverForm(forms.ModelForm):
    """ฟอร์มแก้ไขรูปปกโปรไฟล์ของผู้ใช้เอง"""

    class Meta:
        model = Profile
        fields = ['cover']
        labels = {
            'cover': 'รูปปกโปรไฟล์',
        }
        widgets = {
            'cover': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }


class UserBasicForm(forms.ModelForm):
    """ฟอร์มแก้ไขข้อมูลพื้นฐานของ User (ชื่อจริง นามสกุล อีเมล)"""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        labels = {
            'first_name': 'ชื่อจริง',
            'last_name': 'นามสกุล',
            'email': 'อีเมล',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'กรอกชื่อจริง'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'กรอกนามสกุล'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@example.com'}),
        }


class UserChangePasswordForm(forms.Form):
    """ฟอร์มเปลี่ยนรหัสผ่านของผู้ใช้เอง"""

    current_password = forms.CharField(
        label='รหัสผ่านปัจจุบัน',
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'กรอกรหัสผ่านปัจจุบัน'}),
    )
    new_password1 = forms.CharField(
        label='รหัสผ่านใหม่',
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'กรอกรหัสผ่านใหม่'}),
    )
    new_password2 = forms.CharField(
        label='ยืนยันรหัสผ่านใหม่',
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'กรอกรหัสผ่านใหม่อีกครั้ง'}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        password = self.cleaned_data.get('current_password')
        if not self.user.check_password(password):
            raise forms.ValidationError('รหัสผ่านปัจจุบันไม่ถูกต้อง')
        return password

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('new_password1') != cleaned_data.get('new_password2'):
            self.add_error('new_password2', 'รหัสผ่านทั้งสองช่องไม่ตรงกัน')
        return cleaned_data

    def save(self):
        password = self.cleaned_data['new_password1']
        validate_password(password, user=self.user)
        self.user.set_password(password)
        self.user.save()
        return self.user


class CategoryForm(forms.ModelForm):
    """ฟอร์มจัดการหมวดหมู่"""

    class Meta:
        model = Category
        fields = ['name', 'slug', 'sort_order', 'is_active']
        labels = {
            'name': 'ชื่อหมวดหมู่',
            'slug': 'Slug (URL)',
            'sort_order': 'ลำดับการแสดง',
            'is_active': 'เปิดใช้งาน',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'เช่น ผัด/ข้าวราดแกง'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'เช่น rice (ภาษาอังกฤษตัวเล็ก)'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            qs = Category.objects.filter(name__iexact=name.strip())
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('มีหมวดหมู่ชื่อนี้อยู่แล้ว กรุณาใช้ชื่ออื่น')
        return name

    def clean_slug(self):
        slug = self.cleaned_data.get('slug')
        if slug:
            qs = Category.objects.filter(slug=slug)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('มี Slug นี้อยู่แล้ว กรุณาใช้Slug อื่น')
        return slug


class _UserBaseForm(forms.ModelForm):
    """ฟอร์มพื้นฐานข้อมูลผู้ใช้ (ใช้ร่วมกันระหว่างสร้าง/แก้ไข)"""

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_staff', 'is_superuser', 'is_active']
        labels = {
            'username': 'ชื่อผู้ใช้',
            'first_name': 'ชื่อจริง',
            'last_name': 'นามสกุล',
            'email': 'อีเมล',
            'is_staff': 'สถานะพนักงาน (Staff)',
            'is_superuser': 'สถานะผู้ดูแลระบบ (Superuser)',
            'is_active': 'เปิดใช้งานบัญชี',
        }
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ภาษาอังกฤษ ตัวเลข หรือ @ . + - เท่านั้น',
            }),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@example.com'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_superuser': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    avatar = forms.ImageField(
        label='รูปโปรไฟล์',
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        # ฟิลด์ประกาศเองบนฟอร์ม User (ไม่ใช่ field ของโมเดล) จึงต้องผูก
        # validator ตรงนี้ — จุดอื่น (Profile.avatar/cover/menu image) ผูกที่โมเดล
        validators=[validate_image_file],
    )

    membership_status = forms.ChoiceField(
        choices=Profile.MEMBERSHIP_CHOICES,
        label='สถานะสมาชิก',
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    def __init__(self, *args, can_set_staff=False, **kwargs):
        # can_set_staff=True เฉพาะตอนที่ผู้เรียกเป็น superuser —
        # staff ทั่วไปจะไม่เห็น/ตั้งค่า is_staff ไม่ได้เลย (กันยกระดับสิทธิ์)
        self.can_set_staff = can_set_staff
        super().__init__(*args, **kwargs)
        if not can_set_staff:
            self.fields.pop('is_staff', None)
            self.fields.pop('is_superuser', None)
        if self.instance and self.instance.pk:
            try:
                profile = self.instance.profile
                self.fields['membership_status'].initial = profile.membership_status
            except Profile.DoesNotExist:
                pass

    def clean_avatar(self):
        # ขนาด/ประเภทไฟล์ถูกตรวจโดย validate_image_file ที่ผูกกับ field แล้ว
        return self.cleaned_data.get('avatar')

    def clean_membership_status(self):
        status = self.cleaned_data.get('membership_status')
        return status or 'regular'

    def _save_profile(self, user):
        """บันทึก avatar และสถานะสมาชิกลง Profile"""
        profile, _ = Profile.objects.get_or_create(user=user)
        membership_status = self.cleaned_data.get('membership_status') or 'regular'
        if membership_status not in dict(Profile.MEMBERSHIP_CHOICES):
            membership_status = 'regular'
        profile.membership_status = membership_status
        avatar = self.cleaned_data.get('avatar')
        if avatar:
            if profile.avatar:
                profile.avatar.delete(save=False)
            profile.avatar = avatar
        profile.save()
        return profile

    def clean_username(self):
        """ตรวจสอบว่าชื่อผู้ใช้ไม่ซ้ำกัน"""
        username = self.cleaned_data.get('username')
        qs = User.objects.filter(username__iexact=username)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('มีชื่อผู้ใช้นี้ในระบบแล้ว กรุณาใช้ชื่ออื่น')
        return username


class UserRegisterForm(_UserBaseForm):
    """ฟอร์มสมัครสมาชิกสำหรับผู้ใช้ทั่วไป (ไม่สามารถเลือกเป็นผู้ดูแล/Staff ได้)
    - ต้องตอบคำถามแคปต์ชาเพื่อกันสแปม
    - บัญชีใหม่จะถูกตั้งค่า is_active=False และต้องให้ผู้ดูแลอนุมัติก่อนใช้งาน
    """

    class Meta(_UserBaseForm.Meta):
        fields = ['username', 'first_name', 'last_name', 'email']
        labels = {
            'username': 'ชื่อผู้ใช้',
            'first_name': 'ชื่อจริง',
            'last_name': 'นามสกุล',
            'email': 'อีเมล',
        }

    password1 = forms.CharField(
        label='รหัสผ่าน',
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••'}),
    )
    password2 = forms.CharField(
        label='ยืนยันรหัสผ่าน',
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'กรอกรหัสผ่านซ้ำอีกครั้ง'}),
    )
    captcha_answer = forms.IntegerField(
        label='คำตอบ',
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'ใส่คำตอบของโจทย์',
            'autocomplete': 'off',
        }),
    )

    membership_status = forms.ChoiceField(
        choices=Profile.MEMBERSHIP_CHOICES,
        initial='regular',
        required=False,
        widget=forms.HiddenInput(),
    )

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if password:
            validate_password(password)
        return password

    def clean_captcha_answer(self):
        """ตรวจสอบคำตอบแคปต์ชา (โจทย์ถูกสร้างไว้ใน session)"""
        answer = self.cleaned_data.get('captcha_answer')
        captcha = self.captcha_data or {}
        if not captcha:
            raise forms.ValidationError('กรุณาโหลดหน้าอีกครั้งแล้วลองใหม่')
        expected = captcha.get('answer')
        if answer is None or answer != expected:
            raise forms.ValidationError('คำตอบไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง')
        return answer

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('password1') != cleaned_data.get('password2'):
            self.add_error('password2', 'รหัสผ่านทั้งสองช่องไม่ตรงกัน')
        return cleaned_data

    def save(self, commit=True):
        """สร้างผู้ใช้ทั่วไปเท่านั้น — ไม่สามารถตั้งค่าเป็น Staff ได้ และต้องรอผู้ดูแลอนุมัติ"""
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        user.is_staff = False
        user.is_superuser = False
        user.is_active = False
        self.cleaned_data['membership_status'] = 'regular'
        if commit:
            user.save()
            self._save_profile(user)
        return user


class HomeImageForm(forms.ModelForm):
    """ฟอร์มเปลี่ยนรูปภาพหน้าต้อนรับ (Hero) บนหน้าแรก — เฉพาะผู้ดูแล (Staff)"""

    class Meta:
        model = HomeImage
        fields = ['hero_image']
        labels = {
            'hero_image': 'เลือกรูปภาพใหม่',
        }
        widgets = {
            'hero_image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
        }


class UserCreateForm(_UserBaseForm):
    """ฟอร์มสร้างผู้ใช้ใหม่ (ต้องตั้งรหัสผ่าน)"""

    password1 = forms.CharField(
        label='รหัสผ่าน',
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '••••••••'}),
    )
    password2 = forms.CharField(
        label='ยืนยันรหัสผ่าน',
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'กรอกรหัสผ่านซ้ำอีกครั้ง'}),
    )

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if password:
            validate_password(password)
        return password

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('password1') != cleaned_data.get('password2'):
            self.add_error('password2', 'รหัสผ่านทั้งสองช่องไม่ตรงกัน')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
            self._save_profile(user)
        return user


class UserUpdateForm(_UserBaseForm):
    """ฟอร์มแก้ไขผู้ใช้ (รหัสผ่านเว้นว่างไว้ได้ = ไม่เปลี่ยน)"""

    new_password = forms.CharField(
        label='รหัสผ่านใหม่',
        required=False,
        strip=False,
        help_text='เว้นว่างไว้ = ไม่เปลี่ยนรหัสผ่านเดิม',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'เว้นว่างถ้าไม่ต้องการเปลี่ยน'}),
    )

    def clean_new_password(self):
        password = self.cleaned_data.get('new_password')
        if password:
            validate_password(password)
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        new_password = self.cleaned_data.get('new_password')
        if new_password:
            user.set_password(new_password)
        if commit:
            user.save()
            self._save_profile(user)
        return user


# ======================================================================
# ระบบคูปอง / โปรโมชั่น
# ======================================================================


class CouponForm(forms.ModelForm):
    """ฟอร์มสร้าง/แก้ไขคูปอง"""

    class Meta:
        model = Coupon
        fields = ['code', 'discount_type', 'value', 'min_order',
                  'max_uses', 'valid_from', 'valid_until', 'is_active']
        labels = {
            'code': 'รหัสคูปอง',
            'discount_type': 'ประเภทส่วนลด',
            'value': 'จำนวนส่วนลด',
            'min_order': 'ยอดขั้นต่ำที่ใช้ได้ (บาท)',
            'max_uses': 'จำนวนครั้งที่ใช้ได้ทั้งหมด',
            'valid_from': 'วันที่เริ่มใช้ได้',
            'valid_until': 'วันหมดอายุ',
            'is_active': 'เปิดใช้งาน',
        }
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'เช่น HAPPY10, WELCOME50',
            }),
            'discount_type': forms.Select(attrs={'class': 'form-select'}),
            'value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'min_order': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'max_uses': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'valid_from': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'valid_until': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if code:
            code = code.strip().upper()
            qs = Coupon.objects.filter(code__iexact=code)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('มีรหัสคูปองนี้อยู่แล้ว กรุณาใช้รหัสอื่น')
        return code

    def clean_value(self):
        value = self.cleaned_data.get('value')
        discount_type = self.cleaned_data.get('discount_type')
        if value is not None:
            if value <= 0:
                raise forms.ValidationError('จำนวนส่วนลดต้องมากกว่า 0')
            if discount_type == 'percent' and value > 100:
                raise forms.ValidationError('ส่วนลดเป็นเปอร์เซ็นต์ต้องไม่เกิน 100%')
        return value

    def clean(self):
        cleaned = super().clean()
        valid_from = cleaned.get('valid_from')
        valid_until = cleaned.get('valid_until')
        if valid_from and valid_until and valid_until < valid_from:
            self.add_error('valid_until', 'วันหมดอายุต้องไม่ก่อนวันที่เริ่มใช้ได้')
        return cleaned


class CouponApplyForm(forms.Form):
    """ฟอร์มกรอกรหัสคูปองตอนสั่งอาหาร (บังคับใช้กับออเดอร์)"""

    coupon_code = forms.CharField(
        label='รหัสคูปอง',
        required=False,
        strip=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'เช่น HAPPY10',
            'autocomplete': 'off',
        }),
    )

    def clean_coupon_code(self):
        code = (self.cleaned_data.get('coupon_code') or '').strip().upper()
        if not code:
            return code
        if not Coupon.objects.filter(code__iexact=code, is_active=True).exists():
            raise forms.ValidationError('ไม่พบรหัสคูปองนี้ในระบบ หรือคูปองถูกปิดใช้งาน')
        return code


# ======================================================================
# ระบบสต็อก / วัตถุดิบ
# ======================================================================


class IngredientForm(forms.ModelForm):
    """ฟอร์มเพิ่ม/แก้ไขวัตถุดิบ"""

    class Meta:
        model = Ingredient
        fields = ['name', 'unit', 'stock_qty', 'reorder_level', 'is_active']
        labels = {
            'name': 'ชื่อวัตถุดิบ',
            'unit': 'หน่วย',
            'stock_qty': 'คงเหลือ',
            'reorder_level': 'ระดับเตือนสต็อก',
            'is_active': 'เปิดใช้งาน',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'เช่น หมูสับ, ใบกะเพรา, ข้าวสาร'}),
            'unit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'เช่น กรัม, กิโล, ลูก'}),
            'stock_qty': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'reorder_level': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            qs = Ingredient.objects.filter(name__iexact=name.strip())
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('มีวัตถุดิบชื่อนี้อยู่แล้ว กรุณาใช้ชื่ออื่น')
        return name

    def clean_stock_qty(self):
        stock = self.cleaned_data.get('stock_qty')
        if stock is not None and stock < 0:
            raise forms.ValidationError('คงเหลือต้องไม่น้อยกว่า 0')
        return stock


class MenuIngredientForm(forms.ModelForm):
    """ฟอร์มจับคู่เมนูกับสัดส่วนวัตถุดิบ (ในหน้าแก้ไขเมนู)"""

    class Meta:
        model = MenuIngredient
        fields = ['menu', 'ingredient', 'quantity']
        labels = {
            'menu': 'เมนู',
            'ingredient': 'วัตถุดิบ',
            'quantity': 'ปริมาณที่ใช้ (ต่อ 1 จาน)',
        }
        widgets = {
            'menu': forms.Select(attrs={'class': 'form-select'}),
            'ingredient': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.01', 'min': '0.01',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ingredient'].queryset = Ingredient.objects.filter(is_active=True)


# ======================================================================
# ระบบจองโต๊ะ (Reservation)
# ======================================================================


class ReservationForm(forms.ModelForm):
    """ฟอร์มจองโต๊ะสำหรับลูกค้า + แก้ไขโดยพนักงาน"""

    class Meta:
        model = Reservation
        fields = ['customer_name', 'phone', 'party_size', 'table_number',
                  'reservation_date', 'reservation_time', 'notes']
        labels = {
            'customer_name': 'ชื่อผู้จอง',
            'phone': 'เบอร์โทรศัพท์',
            'party_size': 'จำนวนคน',
            'table_number': 'เลขโต๊ะ (ถ้าระบุได้)',
            'reservation_date': 'วันที่จอง',
            'reservation_time': 'เวลาที่จอง',
            'notes': 'หมายเหตุ',
        }
        widgets = {
            'customer_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'เช่น นางสาวอรทัย ใจดี'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'เช่น 089-123-4567'}),
            'party_size': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '99'}),
            'table_number': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '999'}),
            'reservation_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reservation_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'เช่น ขอโต๊ะติดหน้าต่าง'}),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone and len(''.join(ch for ch in phone if ch.isdigit())) < 9:
            raise forms.ValidationError('กรุณากรอกเบอร์โทรศัพท์ให้ถูกต้อง (อย่างน้อย 9 หลัก)')
        return phone

    def clean_party_size(self):
        size = self.cleaned_data.get('party_size')
        if size is not None and size <= 0:
            raise forms.ValidationError('จำนวนคนต้องมากกว่า 0')
        return size

    def clean(self):
        cleaned = super().clean()
        res_date = cleaned.get('reservation_date')
        res_time = cleaned.get('reservation_time')
        if res_date and res_time:
            if timezone.make_aware(
                timezone.datetime.combine(res_date, res_time)
            ) < timezone.now():
                self.add_error('reservation_time', 'ไม่สามารถจองย้อนหลังได้ กรุณาเลือกเวลาในอนาคต')
        return cleaned


# ======================================================================
# ระบบรีวิว / ให้คะแนนเมนู
# ======================================================================


class CustomerQRPaymentForm(forms.ModelForm):
    """ฟอร์มให้ลูกค้าแจ้งชำระเงินด้วย QR PromptPay + แนบสลิป/เลขอ้างอิง"""

    class Meta:
        model = Order
        fields = ['qr_payment_reference', 'qr_payment_slip']
        widgets = {
            'qr_payment_reference': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'เช่น เลขอ้างอิง/เวลาโอน (ไม่บังคับ)'}
            ),
            'qr_payment_slip': forms.FileInput(
                attrs={'class': 'form-control', 'accept': 'image/*'}
            ),
        }
        labels = {
            'qr_payment_reference': 'เลขอ้างอิง (ถ้ามี)',
            'qr_payment_slip': 'สลิป/ภาพหลักฐาน (ถ้ามี)',
        }

    def __init__(self, *args, require_slip=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['qr_payment_slip'].required = bool(require_slip)
        self.fields['qr_payment_reference'].required = False

    def clean_qr_payment_slip(self):
        value = self.cleaned_data.get('qr_payment_slip')
        if value:
            validate_image_file(value)
        return value


class ReviewForm(forms.ModelForm):
    """ฟอร์มรีวิว + ให้คะแนนเมนู (ผู้ใช้ให้ได้เมนูละครั้ง)"""

    class Meta:
        model = Review
        fields = ['rating', 'comment']
        labels = {
            'rating': 'ให้คะแนน',
            'comment': 'ความคิดเห็น',
        }
        widgets = {
            'rating': forms.Select(
                choices=[(i, f'{"★" * i}{"☆" * (5 - i)}') for i in range(5, 0, -1)],
                attrs={'class': 'form-select'},
            ),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'เล่าความรู้สึกของคุณเกี่ยวกับเมนูนี้ (ไม่บังคับ)',
            }),
        }

    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if rating is not None and not (1 <= rating <= 5):
            raise forms.ValidationError('คะแนนต้องอยู่ระหว่าง 1-5 ดาว')
        return rating

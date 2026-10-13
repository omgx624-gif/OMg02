from django.contrib import admin

from .models import (
    AddOn,
    AutomationSettings,
    Category,
    Coupon,
    DailySequence,
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


@admin.register(DailySequence)
class DailySequenceAdmin(admin.ModelAdmin):
    list_display = ('date', 'last_number')
    search_fields = ('date',)
    list_per_page = 30


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'sort_order', 'is_active')
    list_editable = ('sort_order', 'is_active')
    search_fields = ('name', 'slug')
    list_per_page = 15


class MenuIngredientInline(admin.TabularInline):
    model = MenuIngredient
    extra = 1


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'spice_level', 'available', 'date_added', 'image_tag')
    list_filter = ('category', 'available')
    search_fields = ('name', 'description')
    list_per_page = 15
    readonly_fields = ('image_tag',)
    inlines = [MenuIngredientInline]

    @admin.display(description='ตัวอย่างรูป')
    def image_tag(self, obj):
        from django.utils.html import format_html
        if obj.image:
            return format_html('<img src="{}" style="height:60px;border-radius:6px;" />', obj.image.url)
        return '-'


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('daily_code', 'order_type', 'table_number', 'status', 'created_at', 'item_count_display', 'total_display')
    list_filter = ('order_type', 'status')
    search_fields = ('table_number', 'daily_code', 'delivery__recipient_name', 'delivery__phone')
    inlines = [OrderItemInline]
    list_per_page = 15
    readonly_fields = ('daily_code', 'daily_number', 'coupon_code', 'coupon_discount')
    list_select_related = ('created_by',)

    @admin.display(description='จำนวนชิ้น')
    def item_count_display(self, obj):
        return obj.item_count

    @admin.display(description='ราคารวม (บาท)')
    def total_display(self, obj):
        return f'{obj.total_price:,.2f}'


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = (
        'delivery_code', 'recipient_name', 'phone', 'fee',
        'status', 'rider_name', 'rider_phone', 'delivered_at',
    )
    list_filter = ('status',)
    search_fields = ('recipient_name', 'phone', 'address', 'rider_name')
    list_per_page = 15

    @admin.display(description='ออเดอร์')
    def delivery_code(self, obj):
        return obj.order.display_code


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'membership_status', 'discount_badge',
        'points', 'effective_favorites_badge', 'free_delivery', 'avatar',
    )
    list_filter = ('membership_status',)
    search_fields = ('user__username', 'user__email')
    list_per_page = 15

    @admin.display(description='ส่วนลด')
    def discount_badge(self, obj):
        return f'{obj.discount_percent}%'

    @admin.display(description='เมนูโปรดสูงสุด')
    def effective_favorites_badge(self, obj):
        return obj.effective_max_favorites


@admin.register(AddOn)
class AddOnAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'is_active')
    list_editable = ('is_active',)
    list_filter = ('is_active',)
    search_fields = ('name',)
    list_per_page = 15


@admin.register(HomeImage)
class HomeImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'image_tag', 'updated_at')

    @admin.display(description='รูปภาพ')
    def image_tag(self, obj):
        from django.utils.html import format_html
        if obj.hero_image:
            return format_html('<img src="{}" style="height:60px;border-radius:6px;" />', obj.hero_image.url)
        return '(ใช้รูปเริ่มต้นของระบบ)'


@admin.register(AutomationSettings)
class AutomationSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ('สถานะเปิด/ปิดระบบ', {
            'fields': ('enabled', 'auto_pay', 'auto_earn_points'),
        }),
        ('ออเดอร์ทานในร้าน (นาที)', {
            'fields': ('preparing_minutes', 'ready_minutes', 'served_minutes'),
        }),
        ('การจัดส่ง (นาที)', {
            'fields': ('picking_up_minutes', 'out_for_delivery_minutes', 'delivered_minutes'),
        }),
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('kind', 'title', 'recipient', 'is_read', 'created_at')
    list_filter = ('kind', 'is_read')
    search_fields = ('title', 'message')


@admin.register(StoreLocation)
class StoreLocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'lat', 'lng', 'fee_base', 'fee_per_km', 'free_delivery_over', 'updated_at')
    list_editable = ('fee_base', 'fee_per_km', 'free_delivery_over')
    fieldsets = (
        (None, {
            'fields': ('name', 'lat', 'lng', 'address', 'phone'),
            'description': 'ตำแหน่งร้านใช้คำนวณระยะทางกับไรเดอร์ (Singleton pk=1)',
        }),
        ('ค่าส่ง', {
            'fields': ('fee_base', 'fee_per_km', 'free_delivery_over'),
        }),
        ('ระบบจัดสรรงานอัตโนมัติ', {
            'fields': ('auto_assign_enabled', 'auto_assign_grace_minutes', 'auto_release_minutes'),
        }),
        ('ระบบชำระเงิน (PromptPay)', {
            'fields': ('promptpay_id',),
        }),
        ('การแจ้งเตือน (Line / Email)', {
            'fields': ('line_notify_token_display', 'line_notify_token', 'notification_email',
                       'notify_order', 'notify_reservation', 'notify_review'),
        }),
    )
    readonly_fields = ('line_notify_token_display',)

    def get_form(self, request, obj=None, **kwargs):
        # เฉพาะ superuser เท่านั้นที่แก้ Line Notify Token ได้
        # (token ใช้ยิงแจ้งเตือนออกข้างนอก — ไม่ให้ staff ทั่วไปหยิบไปใช้/แก้)
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            form.base_fields.pop('line_notify_token', None)
        return form

    @admin.display(description='Line Notify Token (แสดงแบบซ่อน)')
    def line_notify_token_display(self, obj):
        from .services import mask_token
        if not obj.line_notify_token:
            return '— ยังไม่ได้ตั้ง token (แจ้งเตือน Line ปิดอยู่) —'
        return f'{mask_token(obj.line_notify_token)} — กำหนดค่าใหม่ได้ที่ช่องด้านล่าง'


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'owner', 'discount_type', 'value', 'min_order', 'used_count',
                    'max_uses', 'valid_from', 'valid_until', 'is_active')
    list_filter = ('is_active', 'discount_type', 'owner')
    search_fields = ('code', 'owner__username')
    list_editable = ('is_active',)
    fieldsets = (
        (None, {
            'fields': ('code', 'owner', 'discount_type', 'value', 'min_order'),
        }),
        ('การใช้งาน', {
            'fields': ('max_uses', 'used_count', 'valid_from', 'valid_until', 'is_active'),
        }),
    )
    readonly_fields = ('used_count',)


@admin.register(PointReward)
class PointRewardAdmin(admin.ModelAdmin):
    list_display = ('name', 'points_cost', 'discount_type', 'value', 'min_order', 'is_active')
    list_editable = ('points_cost', 'is_active')
    list_filter = ('discount_type', 'is_active')
    search_fields = ('name',)


@admin.register(PointTransaction)
class PointTransactionAdmin(admin.ModelAdmin):
    list_display = ('profile', 'points_change', 'balance_after', 'reason', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('profile__user__username', 'reason')
    readonly_fields = ('profile', 'points_change', 'balance_after', 'reason',
                       'reward', 'order', 'created_at')


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit', 'stock_qty', 'reorder_level', 'stock_status', 'is_active')
    list_editable = ('is_active',)
    list_filter = ('is_active',)
    search_fields = ('name',)
    readonly_fields = ('stock_status',)

    @admin.display(description='สถานะสต็อก')
    def stock_status(self, obj):
        if obj.is_out_stock:
            return '✖ หมด'
        if obj.is_low_stock:
            return '⚠ ใกล้หมด'
        return '✓ พอใช้'


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('customer_name', 'phone', 'party_size', 'table_number',
                    'reservation_date', 'reservation_time', 'status', 'created_at')
    list_filter = ('status', 'reservation_date')
    search_fields = ('customer_name', 'phone')
    list_editable = ('status', 'table_number')
    date_hierarchy = 'reservation_date'


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('menu', 'user', 'rating', 'short_comment', 'created_at')
    list_filter = ('rating', 'menu')
    search_fields = ('menu__name', 'user__username', 'comment')
    date_hierarchy = 'created_at'

    @admin.display(description='ความคิดเห็น')
    def short_comment(self, obj):
        return obj.comment[:40] if obj.comment else '-'

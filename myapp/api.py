from django.db.models import Q
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import (
    AddOn,
    Category,
    Coupon,
    Delivery,
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
from .services import order_coupon_status, validate_coupon
from .validators import validate_image_file


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'sort_order', 'is_active']


class MenuItemSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = MenuItem
        fields = [
            'id', 'name', 'category', 'category_display',
            'price', 'spice_level', 'description', 'available',
            'date_added', 'image',
        ]
        read_only_fields = ['id']


class AddOnSerializer(serializers.ModelSerializer):
    class Meta:
        model = AddOn
        fields = ['id', 'name', 'price', 'is_active']
        read_only_fields = ['id']


class OrderItemSerializer(serializers.ModelSerializer):
    menu = serializers.CharField(source='menu.name', read_only=True)
    unit_price = serializers.DecimalField(source='menu.price', max_digits=8, decimal_places=2, read_only=True)
    addons = AddOnSerializer(many=True, read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'menu', 'unit_price', 'quantity', 'subtotal', 'notes', 'addons']
        read_only_fields = ['id']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    order_type_display = serializers.CharField(source='get_order_type_display', read_only=True)
    payment_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    delivery_fee = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    table_display = serializers.CharField(read_only=True)
    is_paid = serializers.BooleanField(read_only=True)
    discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    discounted_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_type', 'order_type_display', 'table_number', 'table_display',
            'status', 'status_display', 'payment_method', 'payment_display',
            'created_at', 'paid_at', 'total_price', 'delivery_fee', 'is_paid', 'items',
            'coupon_code', 'coupon_discount', 'discount_amount', 'discounted_total',
        ]
        read_only_fields = [
            'id',
            # สถานะ/การชำระเงินต้องเปลี่ยนผ่านระบบหลังบ้านเท่านั้น
            # กันผู้ใช้ PATCH ให้ออเดอร์ตัวเอง "ชำระแล้ว" โดยไม่ต้องจ่าย
            'status',
            'payment_method',
            'paid_at',
        ]


class DeliverySerializer(serializers.ModelSerializer):
    order_code = serializers.CharField(source='order.display_code', read_only=True)
    order_status = serializers.CharField(source='order.status', read_only=True)
    order_total = serializers.DecimalField(
        source='order.total_price', max_digits=10, decimal_places=2, read_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Delivery
        fields = [
            'id', 'order', 'order_code', 'order_status', 'order_total',
            # ข้อมูลผู้รับ/ที่อยู่ ปล่อยว่างสำหรับผู้ใช้ทั่วไป (Staff/ไรเดอร์เห็นทั้งหมด)
            'recipient_name', 'phone', 'address',
            'recipient_lat', 'recipient_lng',
            'fee', 'status', 'status_display',
            'rider_name', 'rider_phone', 'tracking_note', 'delivered_at', 'created_at',
        ]
        read_only_fields = ['id']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = kwargs.get('context', {}).get('request')
        if request and not getattr(request.user, 'is_staff', False):
            # กัน mass-assignment: ลูกค้าห้ามกำหนดค่าส่งเอง/สถานะล่วงหน้า/ข้อมูลไรเดอร์
            # (ค่าส่งจะถูกคำนวณจากพิกัดใน Delivery.save() แทน)
            # ส่วนข้อมูลผู้รับยังกรอกได้ (ของตัวเอง ตรงกับฟอร์มบนเว็บ)
            # แต่ตอน "อ่าน" จะถูก mask ใน to_representation เหมือนเดิม
            for _name in ('fee', 'status', 'rider_name', 'rider_phone', 'delivered_at'):
                if _name in self.fields:
                    self.fields[_name].read_only = True

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if request and not getattr(request.user, 'is_staff', False):
            # ซ่อนข้อมูลส่วนบุคคล: เก็บชื่อเต็มให้เห็นแค่บางส่วน
            name = data.get('recipient_name') or ''
            if name:
                data['recipient_name'] = name[:2] + '***'
            phone = data.get('phone') or ''
            if phone:
                data['phone'] = phone[:3] + '****' + phone[-2:] if len(phone) >= 5 else '***'
            if data.get('address'):
                data['address'] = '*** (ซ่อนไว้)'
            if data.get('rider_phone'):
                data['rider_phone'] = '***'
        return data


class ProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    # DRF ไม่ดึง model validator มาเอง — ผูกตรงนี้เพื่อให้ API อัปโหลด
    # ถูกตรวจขนาด/ความเป็นรูปจริง เท่ากับฟอร์มบนเว็บ (ดู myapp/validators.py)
    avatar = serializers.ImageField(required=False, validators=[validate_image_file])
    cover = serializers.ImageField(required=False, validators=[validate_image_file])

    class Meta:
        model = Profile
        fields = ['id', 'username', 'avatar', 'cover']
        read_only_fields = ['id']


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """API อ่านรายการหมวดหมู่"""
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class MenuItemViewSet(viewsets.ModelViewSet):
    """API จัดการเมนูอาหาร (อ่านได้ทุกคน แก้ไขได้เฉพาะ Staff)"""
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticatedOrReadOnly()]


class AddOnViewSet(viewsets.ModelViewSet):
    """API จัดการเครื่องเคียง"""
    queryset = AddOn.objects.filter(is_active=True)
    serializer_class = AddOnSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticatedOrReadOnly()]


class OrderViewSet(viewsets.ModelViewSet):
    """API จัดการออเดอร์ — ผู้ใช้ทั่วไปเห็นเฉพาะของตัวเอง"""
    serializer_class = OrderSerializer

    def get_queryset(self):
        qs = Order.objects.prefetch_related(
            'items', 'items__menu', 'items__addons'
        ).order_by('-created_at')
        if self.request.user.is_staff:
            return qs
        if self.request.user.is_authenticated:
            return qs.filter(created_by=self.request.user)
        return qs.none()

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticatedOrReadOnly()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def _user_may_manage(self, order):
        user = self.request.user
        return user.is_staff or order.created_by_id == user.id

    @action(detail=True, methods=['post'])
    def apply_coupon(self, request, pk=None):
        """ใช้คูปองกับออเดอร์ — ใช้ validate_coupon ร่วมกับหน้าเว็บ order_apply_coupon"""
        order = self.get_object()
        if not self._user_may_manage(order):
            return Response({'error': 'คุณไม่มีสิทธิ์แก้ไขออเดอร์นี้'},
                            status=status.HTTP_403_FORBIDDEN)

        can_apply, used = order_coupon_status(order)
        if not can_apply:
            if used:
                return Response({'error': f'ออเดอร์นี้ใช้คูปอง {used.code} ไปแล้ว '
                                          'กรุณาเอารหัสออกก่อนถ้าต้องการเปลี่ยน'},
                                status=status.HTTP_400_BAD_REQUEST)
            return Response({'error': 'ไม่สามารถใช้คูปองกับออเดอร์ที่ปิดบิล/ยกเลิกแล้วได้'},
                            status=status.HTTP_400_BAD_REQUEST)

        coupon, discount, error = validate_coupon(
            request.data.get('code'), order.total_price, request.user,
        )
        if error:
            code_status = (
                status.HTTP_404_NOT_FOUND if error[0] == 'not_found'
                else status.HTTP_400_BAD_REQUEST
            )
            return Response({'error': error[1]}, status=code_status)

        order.coupon_code = coupon.code
        order.coupon_discount = discount
        order.save(update_fields=['coupon_code', 'coupon_discount'])
        return Response({
            'code': coupon.code,
            'discount': discount,
            'total_after_discount': order.discounted_total,
        })

    @action(detail=True, methods=['post'])
    def remove_coupon(self, request, pk=None):
        """เอารหัสคูปองออกจากออเดอร์"""
        order = self.get_object()
        if not self._user_may_manage(order):
            return Response({'error': 'คุณไม่มีสิทธิ์แก้ไขออเดอร์นี้'},
                            status=status.HTTP_403_FORBIDDEN)
        order.coupon_code = ''
        order.coupon_discount = 0
        order.save(update_fields=['coupon_code', 'coupon_discount'])
        return Response({'ok': True})


class DeliveryViewSet(viewsets.ModelViewSet):
    """API จัดการข้อมูลเดลิเวอร์รี่ — Staff เห็นทั้งหมด ผู้ใช้ทั่วไปเห็นเฉพาะออเดอร์ตัวเอง"""
    serializer_class = DeliverySerializer

    def get_queryset(self):
        qs = Delivery.objects.select_related('order').order_by('-created_at')
        if self.request.user.is_staff:
            return qs
        if self.request.user.is_authenticated:
            return qs.filter(order__created_by=self.request.user)
        return qs.none()

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            if self.action in ('update', 'partial_update', 'destroy'):
                return [permissions.IsAdminUser()]
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        # ผู้ใช้ทั่วไปกำหนดให้ผูกกับออเดอร์ของตัวเองเท่านั้น (ป้องกันผูกกับออเดอร์คนอื่น)
        order_id = serializer.validated_data.get('order')
        if order_id is None:
            raise serializers.ValidationError({'order': 'กรุณาระบุออเดอร์'})
        # validated_data['order'] เป็น Order instance (PrimaryKeyRelatedField)
        order = order_id if not isinstance(order_id, int) else Order.objects.get(pk=order_id)
        if not self.request.user.is_staff and order.created_by_id != self.request.user.id:
            raise serializers.ValidationError({'order': 'สามารถสร้างข้อมูลจัดส่งสำหรับออเดอร์ของตัวเองเท่านั้น'})
        if Delivery.objects.filter(order=order).exists():
            # OneToOne — กัน 500 IntegrityError เมื่อออเดอร์มีข้อมูลจัดส่งแล้ว
            raise serializers.ValidationError({'order': 'ออเดอร์นี้มีข้อมูลจัดส่งอยู่แล้ว'})
        if not self.request.user.is_staff:
            # บังคับสถานะเริ่มต้น + ให้ Delivery.save() คำนวณค่าส่งจากพิกัดเอง
            serializer.save(order=order, status='pending')
        else:
            serializer.save(order=order)


# ======================================================================
# API เพิ่มเติม: จองโต๊ะ / คูปอง / สต็อก / รีวิว / คะแนน / แจ้งเตือน / ฯลฯ
# ======================================================================


class ReservationSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Reservation
        fields = [
            'id', 'customer_name', 'phone', 'party_size', 'table_number',
            'reservation_date', 'reservation_time', 'notes',
            'status', 'status_display', 'created_at',
        ]
        read_only_fields = ['id', 'status', 'created_at']


class CouponSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner.username', read_only=True)

    class Meta:
        model = Coupon
        fields = [
            'id', 'code', 'owner', 'owner_username', 'discount_type', 'value',
            'min_order', 'max_uses', 'used_count', 'valid_from', 'valid_until',
            'is_active',
        ]
        read_only_fields = ['id', 'used_count']


class IngredientSerializer(serializers.ModelSerializer):
    is_low_stock = serializers.BooleanField(read_only=True)
    is_out_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Ingredient
        fields = [
            'id', 'name', 'unit', 'stock_qty', 'reorder_level',
            'is_active', 'is_low_stock', 'is_out_stock',
        ]
        read_only_fields = ['id']


class MenuIngredientSerializer(serializers.ModelSerializer):
    menu_name = serializers.CharField(source='menu.name', read_only=True)
    ingredient_name = serializers.CharField(source='ingredient.name', read_only=True)
    ingredient_unit = serializers.CharField(source='ingredient.unit', read_only=True)

    class Meta:
        model = MenuIngredient
        fields = [
            'id', 'menu', 'menu_name', 'ingredient', 'ingredient_name',
            'ingredient_unit', 'quantity',
        ]
        read_only_fields = ['id']


class ReviewSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'menu', 'username', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'username', 'created_at']
        extra_kwargs = {
            'rating': {'min_value': 1, 'max_value': 5},
        }


class PointRewardSerializer(serializers.ModelSerializer):
    class Meta:
        model = PointReward
        fields = [
            'id', 'name', 'description', 'points_cost', 'discount_type',
            'value', 'min_order', 'is_active',
        ]
        read_only_fields = ['id']


class PointTransactionSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source='profile.user.username', read_only=True)
    reward_name = serializers.CharField(source='reward.name', read_only=True, default=None)

    class Meta:
        model = PointTransaction
        fields = [
            'id', 'user', 'points_change', 'balance_after', 'reason',
            'reward', 'reward_name', 'created_at',
        ]
        read_only_fields = fields


class NotificationSerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source='get_kind_display', read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'kind', 'kind_display', 'title', 'message', 'link', 'is_read', 'created_at']
        read_only_fields = fields


# ------------------------------------------------------------------


class ReservationViewSet(viewsets.ModelViewSet):
    """API จองโต๊ะ — สร้างได้ทุกคน (ไม่ต้องล็อกอิน) 
    ดู/แก้ได้เฉพาะเจ้าของ (Staff เห็นทั้งหมด)
    """
    serializer_class = ReservationSerializer
    throttle_scope = 'reservation'

    def get_queryset(self):
        if self.request.user.is_staff:
            return Reservation.objects.select_related('created_by').order_by(
                'reservation_date', 'reservation_time'
            )
        if self.request.user.is_authenticated:
            return Reservation.objects.filter(created_by=self.request.user)
        return Reservation.objects.none()

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        if self.action in ('update', 'partial_update', 'destroy', 'update_status'):
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]

    def get_throttles(self):
        # จำกัดสแปมจองโต๊ะ: 5 ครั้ง/ชั่วโมง ต่อผู้ใช้ (ไม่รวม Staff)
        if self.action == 'create' and not getattr(self.request.user, 'is_staff', False):
            return [ScopedRateThrottle()]
        return []

    def perform_create(self, serializer):
        reservation = serializer.save(status='requested')
        if getattr(self.request.user, 'is_authenticated', False):
            Reservation.objects.filter(pk=reservation.pk).update(created_by=self.request.user)
        from .services import announce_new_reservation
        announce_new_reservation(reservation)

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """เปลี่ยนสถานะการจอง (เฉพาะ Staff) เช่น ยืนยัน/นั่งแล้ว/ยกเลิก"""
        reservation = self.get_object()
        new_status = request.data.get('status', '')
        if new_status not in dict(Reservation.STATUS_CHOICES):
            return Response({'error': 'สถานะไม่ถูกต้อง'}, status=status.HTTP_400_BAD_REQUEST)
        reservation.status = new_status
        reservation.save(update_fields=['status'])
        return Response(ReservationSerializer(reservation, context=self.get_serializer_context()).data)


class CouponViewSet(viewsets.ModelViewSet):
    """API คูปอง — ผู้ใช้ทั่วไปเห็นเฉพาะคูปองสาธารณะ/ของตัวเอง 
    สร้าง/แก้/ลบ เฉพาะ Staff
    """
    serializer_class = CouponSerializer

    def get_queryset(self):
        qs = Coupon.objects.all()
        if not self.request.user.is_staff:
            if self.request.user.is_authenticated:
                return qs.filter(is_active=True).filter(
                    Q(owner__isnull=True) | Q(owner=self.request.user)
                )
            return qs.filter(is_active=True, owner__isnull=True)
        return qs

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticatedOrReadOnly()]

    @action(detail=False, methods=['post'])
    def validate(self, request):
        """ตรวจสอบคูปอง: รับ code + order_price คืนว่ามีสิทธิ์ใช้/ส่วนลดเท่าไหร่"""
        from decimal import Decimal
        code = request.data.get('code', '').strip()
        order_price = request.data.get('order_price') or 0
        try:
            order_price = Decimal(str(order_price))
        except Exception:
            return Response({'error': 'order_price ต้องเป็นตัวเลข'}, status=status.HTTP_400_BAD_REQUEST)

        coupon, discount, error = validate_coupon(
            code, order_price, request.user, owned_only=True,
        )
        if error:
            code_status = (
                status.HTTP_404_NOT_FOUND if error[0] == 'not_found'
                else status.HTTP_400_BAD_REQUEST
            )
            return Response({'error': error[1]}, status=code_status)
        return Response({
            'code': coupon.code,
            'discount_type': coupon.discount_type,
            'discount': discount,
            'min_order': coupon.min_order,
        })


class IngredientViewSet(viewsets.ModelViewSet):
    """API วัตถุดิบ/สต็อก — แก้ไขได้เฉพาะ Staff"""
    queryset = Ingredient.objects.order_by('name')
    serializer_class = IngredientSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticatedOrReadOnly()]


class MenuIngredientViewSet(viewsets.ModelViewSet):
    """API สัดส่วนวัตถุดิบของเมนู (Recipe) — แก้ไขได้เฉพาะ Staff"""
    queryset = MenuIngredient.objects.select_related('menu', 'ingredient').order_by('menu__name', 'ingredient__name')
    serializer_class = MenuIngredientSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticatedOrReadOnly()]

    def get_queryset(self):
        qs = super().get_queryset()
        menu = self.request.query_params.get('menu')
        if menu:
            qs = qs.filter(menu_id=menu)
        return qs


class ReviewViewSet(viewsets.ModelViewSet):
    """API รีวิว/ให้คะแนนเมนู — ผู้ใช้ให้เมนูละ 1 ครั้ง (แก้ไข/ลบได้เฉพาะของตัวเอง)"""
    serializer_class = ReviewSerializer

    def get_queryset(self):
        qs = Review.objects.select_related('user').order_by('-created_at')
        menu = self.request.query_params.get('menu')
        if menu:
            qs = qs.filter(menu_id=menu)
        return qs

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        # เลียนแบบหน้าเว็บ: ผู้ใช้ให้เมนูละครั้ง — รีวิวซ้ำ = อัปเดตของเดิม
        review, _ = Review.objects.update_or_create(
            menu=serializer.validated_data['menu'],
            user=self.request.user,
            defaults={
                'rating': serializer.validated_data.get('rating'),
                'comment': serializer.validated_data.get('comment', ''),
            },
        )
        return review

    def perform_update(self, serializer):
        # กัน IDOR: แก้ไขได้เฉพาะรีวิวของตัวเอง (หรือ staff) — และห้ามยึดรีวิวคนอื่น
        # ด้วยการ save(user=...) เด็ดขาด (ของเดิมทำให้ผู้โจมตีเป็นเจ้าของรีวิว)
        if serializer.instance.user_id != self.request.user.id and not self.request.user.is_staff:
            raise serializers.ValidationError('แก้ไขได้เฉพาะรีวิวของตัวเอง')
        serializer.save()

    def perform_destroy(self, instance):
        if instance.user_id != self.request.user.id and not self.request.user.is_staff:
            raise serializers.ValidationError('ลบได้เฉพาะรีวิวของตัวเอง')
        instance.delete()


class PointRewardViewSet(viewsets.ReadOnlyModelViewSet):
    """API สิทธิ์แลกคะแนน — อ่านได้ทุกคน + แลกด้วยคะแนน (ต้องล็อกอิน)"""
    serializer_class = PointRewardSerializer

    def get_queryset(self):
        qs = PointReward.objects.order_by('points_cost')
        if not self.request.user.is_staff:
            return qs.filter(is_active=True)
        return qs

    @action(detail=True, methods=['post'])
    def redeem(self, request, pk=None):
        """แลกคะแนนเป็นสิทธิ์ — ออกคูปอง PTS-... ผูกเจ้าของ อายุ 30 วัน"""
        from datetime import timedelta
        from uuid import uuid4

        from django.utils import timezone

        reward = self.get_object()
        profile, _ = Profile.objects.get_or_create(user=request.user)
        if not profile.redeem_points(
            reward.points_cost,
            reason=f'แลกสิทธิ์ "{reward.name}"',
            reward=reward,
        ):
            return Response(
                {'error': f'คะแนนไม่พอ (มี {profile.points} ต้องใช้ {reward.points_cost} คะแนน)'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        code = f'PTS-{reward.pk}-{uuid4().hex[:6].upper()}'
        coupon = Coupon.objects.create(
            code=code,
            owner=request.user,
            is_active=True,
            discount_type=reward.discount_type,
            value=reward.value,
            min_order=reward.min_order,
            valid_until=timezone.now() + timedelta(days=30),
        )
        return Response({
            'error': None,
            'code': code,
            'balance': profile.points,
            'reward': {
                'name': reward.name,
                'discount_type': coupon.discount_type,
                'value': coupon.value,
                'valid_until': coupon.valid_until,
            },
        })


class PointTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """API ประวัติคะแนนของตัวเอง (อ่านได้อย่างเดียว กันแก้ ledger)"""
    serializer_class = PointTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = PointTransaction.objects.select_related('profile__user', 'reward', 'order')
        if self.request.user.is_staff:
            return qs
        return qs.filter(profile__user=self.request.user)


class ProfileViewSet(viewsets.GenericViewSet):
    """API โปรไฟล์ตัวเอง — ดู/แก้ได้เฉพาะเจ้าของเท่านั้น"""
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def _get_profile(self):
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        return profile

    @action(detail=False, methods=['get'])
    def me(self, request):
        """ดูโปรไฟล์ตัวเอง + ยอดคะแนน/สถานะสมาชิก"""
        profile = self._get_profile()
        return Response({
            'id': profile.pk,
            'username': request.user.username,
            'email': request.user.email,
            'avatar': request.build_absolute_uri(profile.avatar.url) if profile.avatar else None,
            'cover': request.build_absolute_uri(profile.cover.url) if profile.cover else None,
            'membership_status': profile.membership_status,
            'points': profile.points,
            'points_rate': profile.points_rate,
            'discount_percent': profile.discount_percent,
            'free_delivery': profile.free_delivery,
            'max_favorites': profile.effective_max_favorites,
        })

    @action(detail=False, methods=['patch', 'put'], url_path='me')
    def update_me(self, request):
        """แก้ไขโปรไฟล์ตัวเอง (avatar / cover — ใช้ multipart/form-data ในการ PATCH)"""
        profile = self._get_profile()
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """API แจ้งเตือนของตัวเอง — อ่านได้อย่างเดียว + เปลี่ยนสถานะอ่านแล้ว"""
    serializer_class = NotificationSerializer
    throttle_scope = 'notification'

    def get_queryset(self):
        qs = Notification.objects.all().order_by('-created_at')
        if self.request.user.is_staff:
            return qs.filter(Q(recipient__isnull=True) | Q(recipient=self.request.user))
        return qs.filter(recipient=self.request.user)

    def get_permissions(self):
        return [permissions.IsAuthenticated()]

    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        """ทำเครื่องหมายว่าอ่านแล้ว"""
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return Response({'ok': True})

    @action(detail=False, methods=['post'])
    def read_all(self, request):
        """อ่านทั้งหมด"""
        updated = self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({'ok': True, 'updated': updated})


class StoreInfoView(APIView):
    """API ข้อมูลร้าน (พิกัด/ค่าส่ง/แผนที่) — เผยแพร่สาธารณะ ห้ามรั่ว token"""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        store = StoreLocation.get_setting()
        data = {
            'name': store.name,
            'lat': store.lat,
            'lng': store.lng,
            'address': store.address,
            'fee_base': store.fee_base,
            'fee_per_km': store.fee_per_km,
            'free_delivery_over': store.free_delivery_over,
            'maps_url': store.maps_url,
        }
        # Staff ดูรายละเอียดการตั้งค่าเพิ่มเติม (แต่ไม่โชว์ token)
        if getattr(request.user, 'is_staff', False):
            data.update({
                'auto_assign_enabled': store.auto_assign_enabled,
                'auto_assign_grace_minutes': store.auto_assign_grace_minutes,
                'auto_release_minutes': store.auto_release_minutes,
                'promptpay_id': store.promptpay_id,
                'notification_email': store.notification_email,
                'notify_order': store.notify_order,
                'notify_reservation': store.notify_reservation,
                'notify_review': store.notify_review,
            })
        return Response(data)
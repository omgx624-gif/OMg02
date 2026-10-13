from django.contrib.auth import views as auth_views
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views
from .api import (
    AddOnViewSet,
    CategoryViewSet,
    CouponViewSet,
    DeliveryViewSet,
    IngredientViewSet,
    MenuIngredientViewSet,
    MenuItemViewSet,
    NotificationViewSet,
    OrderViewSet,
    PointRewardViewSet,
    PointTransactionViewSet,
    ProfileViewSet,
    ReservationViewSet,
    ReviewViewSet,
    StoreInfoView,
)

router = DefaultRouter()
router.register('categories', CategoryViewSet, basename='api-category')
router.register('menus', MenuItemViewSet, basename='api-menu')
router.register('addons', AddOnViewSet, basename='api-addon')
router.register('orders', OrderViewSet, basename='api-order')
router.register('deliveries', DeliveryViewSet, basename='api-delivery')
router.register('reservations', ReservationViewSet, basename='api-reservation')
router.register('coupons', CouponViewSet, basename='api-coupon')
router.register('ingredients', IngredientViewSet, basename='api-ingredient')
router.register('recipes', MenuIngredientViewSet, basename='api-recipe')
router.register('reviews', ReviewViewSet, basename='api-review')
router.register('points/rewards', PointRewardViewSet, basename='api-point-reward')
router.register('points/transactions', PointTransactionViewSet, basename='api-point-transaction')
router.register('profile', ProfileViewSet, basename='api-profile')
router.register('notifications', NotificationViewSet, basename='api-notification')

api_urlpatterns = router.urls + [
    path('store/', StoreInfoView.as_view(), name='api-store'),
]

urlpatterns = [
    # Health check สาธารณะ สำหรับ Docker/load balancer (ไม่ต้องล็อกอิน)
    path('healthz', views.healthz, name='healthz'),
    path('', views.home, name='home'),
    path('welcome-banner/update/', views.welcome_banner_update, name='welcome_banner_update'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('login/google/', views.google_login_redirect, name='google_login_redirect'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('contact/', views.contact, name='contact'),
    path('education/', views.education, name='education'),

    # URL สำหรับลืมรหัสผ่าน / เปลี่ยนรหัสผ่านใหม่ (อีเมล)
    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='core/auth/password_reset_form.html',
            email_template_name='core/auth/password_reset_email.html',
            subject_template_name='core/auth/password_reset_subject.txt',
            success_url='/password-reset/done/',
        ),
        name='password_reset',
    ),
    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='core/auth/password_reset_done.html',
        ),
        name='password_reset_done',
    ),
    path(
        'password-reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='core/auth/password_reset_confirm.html',
            success_url='/password-reset/complete/',
        ),
        name='password_reset_confirm',
    ),
    path(
        'password-reset/complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='core/auth/password_reset_complete.html',
        ),
        name='password_reset_complete',
    ),

    # URL สำหรับจัดการข้อมูลเมนูอาหาร (CRUD)
    path('menu/', views.menu_list, name='menu_list'),
    path('menu/add/', views.menu_create, name='menu_create'),
    path('menu/<int:pk>/edit/', views.menu_update, name='menu_update'),
    path('menu/<int:pk>/delete/', views.menu_delete, name='menu_delete'),

    # URL สำหรับจัดการหมวดหมู่ (Category)
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_update, name='category_update'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),

    # URL สำหรับจัดการเครื่องเคียง (AddOn)
    path('addons/', views.addon_list, name='addon_list'),
    path('addons/add/', views.addon_create, name='addon_create'),
    path('addons/<int:pk>/edit/', views.addon_update, name='addon_update'),
    path('addons/<int:pk>/delete/', views.addon_delete, name='addon_delete'),

    # URL สำหรับระบบสั่งอาหาร (Order)
    path('orders/', views.order_list, name='order_list'),
    path('orders/<int:pk>/', views.order_detail, name='order_detail'),
    path('orders/<int:pk>/delete/', views.order_delete, name='order_delete'),
    path('orders/<int:pk>/pay/', views.order_pay, name='order_pay'),
    path('orders/<int:pk>/pay/qr/', views.order_pay_qr, name='order_pay_qr'),
    path('orders/<int:pk>/status/', views.order_update_status, name='order_update_status'),
    path('orders/<int:pk>/add-item/', views.order_add_item, name='order_add_item'),
    path('orders/item/<int:item_pk>/qty/', views.order_item_qty, name='order_item_qty'),
    path('orders/item/<int:item_pk>/remove/', views.order_item_remove, name='order_item_remove'),

    # URL สำหรับระบบเดลิเวอร์รี่ (Staff Dashboard)
    path('delivery/', views.delivery_dashboard, name='delivery_dashboard'),
    path('delivery/<int:delivery_pk>/status/', views.delivery_update_status, name='delivery_update_status'),
    path('delivery/<int:delivery_pk>/assign-rider/', views.delivery_assign_rider, name='delivery_assign_rider'),
    path('delivery/<int:delivery_pk>/calc-fee/', views.delivery_calc_fee, name='delivery_calc_fee'),
    path('delivery/<int:delivery_pk>/geocode/', views.delivery_geocode, name='delivery_geocode'),
    path('delivery/settings/', views.delivery_settings, name='delivery_settings'),
    path('delivery/settings/test-line/', views.line_notify_test, name='line_notify_test'),

    # URL สำหรับระบบเดลิเวอร์รี่แยก (Delivery Module: หน้าแรก / ติดตาม / ไรเดอร์)
    path('delivery/home/', views.delivery_home, name='delivery_home'),
    path('delivery/track/', views.delivery_tracking, name='delivery_tracking'),
    path('delivery/rider/', views.rider_dashboard, name='rider_dashboard'),
    path('delivery/rider/my-jobs/', views.rider_my_jobs, name='rider_my_jobs'),
    path('delivery/rider/<int:delivery_pk>/accept/', views.rider_accept_job, name='rider_accept_job'),
    path('delivery/rider/<int:delivery_pk>/status/', views.rider_update_status, name='rider_update_status'),

    # URL สำหรับจัดการผู้ใช้งาน (เฉพาะ Staff)
    path('users/', views.user_list, name='user_list'),
    path('users/add/', views.user_create, name='user_create'),
    path('users/<int:pk>/edit/', views.user_update, name='user_update'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),
    path('users/<int:pk>/profile/', views.user_profile_detail, name='user_profile_detail'),

    # URL สำหรับหน้าเว็บสำหรับผู้ใช้ทั่วไป
    path('profile/', views.user_profile, name='user_profile'),
    path('profile/change-password/', views.user_change_password, name='user_change_password'),
    path('my-orders/', views.user_order_history, name='user_order_history'),

    # URL สำหรับระบบอัตโนมัติ (Autopilot) และการแจ้งเตือน
    path('automation/settings/', views.automation_settings, name='automation_settings'),
    path('notifications/', views.notifications_center, name='notifications_center'),
    path('notifications/read/', views.mark_notifications_read, name='mark_notifications_read'),
    path('notifications/<int:pk>/', views.notification_redirect, name='notification_redirect'),

    # URL สำหรับหน้าเมนูรายละเอียด
    path('menu/<int:pk>/detail/', views.menu_detail, name='menu_detail'),

    # URL สำหรับใบเสร็จ / QR โต๊ะ / ส่งออกรายงาน
    path('orders/<int:pk>/receipt/', views.order_receipt, name='order_receipt'),
    path('table/<int:table_number>/qr/', views.table_qr, name='table_qr'),
    path('export/orders/csv/', views.export_orders_csv, name='export_orders_csv'),
    path('export/orders/xlsx/', views.export_orders_xlsx, name='export_orders_xlsx'),

    # URL สำหรับระบบคูปอง / โปรโมชั่น (Staff CRUD + การใช้กับออเดอร์)
    path('coupons/', views.coupon_list, name='coupon_list'),
    path('coupons/add/', views.coupon_create, name='coupon_create'),
    path('coupons/<int:pk>/edit/', views.coupon_update, name='coupon_update'),
    path('coupons/<int:pk>/delete/', views.coupon_delete, name='coupon_delete'),
    path('orders/<int:pk>/apply-coupon/', views.order_apply_coupon, name='order_apply_coupon'),
    path('orders/<int:pk>/remove-coupon/', views.order_remove_coupon, name='order_remove_coupon'),
    path('points/', views.points_redemption, name='points_redemption'),

    # URL สำหรับระบบสต็อก / วัตถุดิบ (Inventory)
    path('inventory/', views.inventory_dashboard, name='inventory_dashboard'),
    path('inventory/ingredients/add/', views.ingredient_create, name='ingredient_create'),
    path('inventory/ingredients/<int:pk>/edit/', views.ingredient_update, name='ingredient_update'),
    path('inventory/ingredients/<int:pk>/delete/', views.ingredient_delete, name='ingredient_delete'),
    path('inventory/recipes/', views.menu_ingredient_list, name='menu_ingredient_list'),
    path('inventory/recipes/add/', views.menu_ingredient_create, name='menu_ingredient_create'),
    path('inventory/recipes/<int:pk>/edit/', views.menu_ingredient_update, name='menu_ingredient_update'),
    path('inventory/recipes/<int:pk>/delete/', views.menu_ingredient_delete, name='menu_ingredient_delete'),

    # URL สำหรับระบบจองโต๊ะ (Reservation)
    path('reserve/', views.reservation_create, name='reservation_create'),
    path('my-reservations/', views.reservation_list, name='reservation_list'),
    path('reservation/dashboard/', views.reservation_dashboard, name='reservation_dashboard'),
    path('reservation/<int:pk>/status/', views.reservation_update_status, name='reservation_update_status'),
    path('reservation/<int:pk>/delete/', views.reservation_delete, name='reservation_delete'),

    # URL สำหรับระบบรีวิว / ให้คะแนนเมนู
    path('menu/<int:menu_pk>/review/', views.review_create, name='review_create'),
    path('review/<int:pk>/delete/', views.review_delete, name='review_delete'),

    # URL สำหรับระบบหน้าจอครัว (Kitchen Display System)
    path('kitchen/', views.kitchen_display, name='kitchen_display'),
    path('kitchen/<int:pk>/advance/', views.kds_update_status, name='kds_update_status'),

    # REST API (Django REST Framework)
    path('api/', include(api_urlpatterns)),
]

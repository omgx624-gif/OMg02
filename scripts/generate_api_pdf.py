# -*- coding: utf-8 -*-
"""Generate API connection summary PDF (Thai) using reportlab."""

import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

FONT_PATH = r"C:\Windows\Fonts\tahoma.ttf"
FONT_BOLD_PATH = r"C:\Windows\Fonts\tahomabd.ttf"
FONT_NAME = "Tahoma"
FONT_BOLD = "Tahoma-Bold"

pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH))
pdfmetrics.registerFont(TTFont(FONT_BOLD, FONT_BOLD_PATH))
pdfmetrics.registerFontFamily(FONT_NAME, normal=FONT_NAME, bold=FONT_BOLD,
                              italic=FONT_NAME, boldItalic=FONT_BOLD)

OUTPUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "API_เอกสารสรุป.pdf")

ENDPOINTS = [
    {
        "name": "categories",
        "service": "CategoryViewSet",
        "file": "myapp/api.py:151",
        "type": "อ่านอย่างเดียว",
        "methods": "GET ✅",
        "params": "-",
        "auth": "เข้าชมได้ทุกคน",
        "detail": "รายการหมวดหมู่เมนูที่เปิดใช้งานอยู่ (is_active=True) เรียงตาม sort_order",
        "fields": "id, name, slug, sort_order, is_active",
    },
    {
        "name": "menus",
        "service": "MenuItemViewSet",
        "file": "myapp/api.py:158",
        "type": "CRUD",
        "methods": "GET ✅ | POST | PUT/PATCH | DELETE ✅",
        "params": "-",
        "auth": "อ่าน: ทุกคน | สร้าง/แก้/ลบ: เฉพาะ Admin",
        "detail": "จัดการเมนูอาหาร รองรับการกรอง/เรียงลำดับโครงสร้าง Django ORM",
        "fields": "id, name, category, category_display, price, spice_level, description, available, date_added, image",
    },
    {
        "name": "addons",
        "service": "AddOnViewSet",
        "file": "myapp/api.py:169",
        "type": "CRUD",
        "methods": "GET ✅ | POST | PUT/PATCH | DELETE ✅",
        "params": "-",
        "auth": "อ่าน: ทุกคน | สร้าง/แก้/ลบ: เฉพาะ Admin",
        "detail": "จัดการเครื่องเคียง/ออปชันเสริม (แสดงเฉพาะที่เปิดใช้งาน)",
        "fields": "id, name, price, is_active",
    },
    {
        "name": "orders",
        "service": "OrderViewSet",
        "file": "myapp/api.py:180",
        "type": "CRUD + Action",
        "methods": "GET ✅ | POST | PUT/PATCH ✅ | DELETE ✅ | apply_coupon ✅ | remove_coupon ✅",
        "params": "apply_coupon: {code} / remove_coupon: -",
        "auth": "อ่าน/แก้: ล็อกอินแล้ว เห็นเฉพาะออเดอร์ตัวเอง (Staff เห็นทั้งหมด) | สร้าง: ล็อกอิน",
        "detail": "จัดการออเดอร์ สถานะ/ชำระเงินถูกบังคับเป็น read-only (กันแก้ status เอง)",
        "fields": "id, order_type(+display), table_number(+display), status(+display), payment_method, created_at, paid_at, total_price, delivery_fee, is_paid, items, coupon_code, coupon_discount, discount_amount, discounted_total",
        "actions": [
            ("POST /api/orders/{id}/apply_coupon/", "ใช้คูปองกับออเดอร์ (คำนวณส่วนลด snapshot เช่นเดียวกับหน้าเว็บ) สำเร็จคืน {code, discount, total_after_discount}"),
            ("POST /api/orders/{id}/remove_coupon/", "เอารหัสคูปองออกจากออเดอร์ คืน {ok: True}"),
        ],
    },
    {
        "name": "deliveries",
        "service": "DeliveryViewSet",
        "file": "myapp/api.py:272",
        "type": "CRUD",
        "methods": "GET ✅ | POST | PUT/PATCH ✅ | DELETE ✅",
        "params": "-",
        "auth": "อ่าน/สร้าง: ล็อกอิน (เฉพาะออเดอร์ตัวเอง) | แก้/ลบ: เฉพาะ Admin",
        "detail": "ข้อมูลจัดส่ง — ผู้ใช้ทั่วไปเห็นข้อมูลผู้รับ/ที่อยู่แบบซ่อน (mask): ชื่อชื่อ 2 ตัวแรก, เบอร์ 3 ตัวแรก+2 ตัวท้าย, ที่อยู่ซ่อนทั้งหมด",
        "fields": "id, order, order_code, order_status, order_total, recipient_name, phone, address, fee, status(+display), rider_name, rider_phone, tracking_note, delivered_at, created_at",
    },
    {
        "name": "reservations",
        "service": "ReservationViewSet",
        "file": "myapp/api.py:408",
        "type": "CRUD + Action",
        "methods": "GET ✅ | POST (ไม่ต้องล็อกอิน) | PUT/PATCH ✅ | DELETE ✅ | update_status ✅",
        "params": "update_status: {status}",
        "auth": "สร้าง: ทุกคน (ไม่ล็อกอิน) | อ่าน: เจ้าของ/ล็อกอิน, Staff เห็นทั้งหมด | แก้/ลบ/เปลี่ยนสถานะ: เฉพาะ Admin",
        "detail": "จองโต๊ะ — กันสแปมด้วย Throttle 5 ครั้ง/ชั่วโมง/ผู้ใช้ (ยกเว้น Staff) เมื่อสร้างสำเร็จจะแจ้งเตือนผ่าน LINE (announce_new_reservation)",
        "fields": "id, customer_name, phone, party_size, table_number, reservation_date, reservation_time, notes, status(+display), created_at",
        "actions": [
            ("POST /api/reservations/{id}/update_status/", "เปลี่ยนสถานะการจอง (ยืนยัน/นั่งแล้ว/ยกเลิก) เฉพาะ Staff คืนข้อมูลการจองล่าสุด"),
        ],
    },
    {
        "name": "coupons",
        "service": "CouponViewSet",
        "file": "myapp/api.py:456",
        "type": "CRUD + Action",
        "methods": "GET ✅ | POST ✅ | PUT/PATCH ✅ | DELETE ✅ | validate ✅",
        "params": "validate: {code, order_price}",
        "auth": "อ่าน: ล็อกอินเห็นคูปองสาธารณะ+ของตัวเอง, แขกเห็นเฉพาะสาธารณะ | สร้าง/แก้/ลบ: เฉพาะ Admin",
        "detail": "ระบบคูปองส่วนลด รองรับทั้งคูปองสาธารณะและคูปองส่วนตัว (owner)",
        "fields": "id, code, owner, owner_username, discount_type, value, min_order, max_uses, used_count, valid_from, valid_until, is_active",
        "actions": [
            ("POST /api/coupons/validate/", "ตรวจสอบคูปองก่อนใช้ คืน {code, discount_type, discount, min_order} — Staff ข้ามข้อจำกัดเจ้าของ"),
        ],
    },
    {
        "name": "ingredients",
        "service": "IngredientViewSet",
        "file": "myapp/api.py:507",
        "type": "CRUD",
        "methods": "GET ✅ | POST | PUT/PATCH | DELETE ✅",
        "params": "-",
        "auth": "อ่าน: ทุกคน | สร้าง/แก้/ลบ: เฉพาะ Admin",
        "detail": "วัตถุดิบ/สต็อก เรียงตามชื่อ คำนวณสถานะ is_low_stock / is_out_stock อัตโนมัติ",
        "fields": "id, name, unit, stock_qty, reorder_level, is_active, is_low_stock, is_out_stock",
    },
    {
        "name": "recipes",
        "service": "MenuIngredientViewSet",
        "file": "myapp/api.py:518",
        "type": "CRUD",
        "methods": "GET ✅ | POST | PUT/PATCH | DELETE ✅",
        "params": "?menu=<id> (กรองรายการของเมนูนั้น)",
        "auth": "อ่าน: ทุกคน | สร้าง/แก้/ลบ: เฉพาะ Admin",
        "detail": "สัดส่วนวัตถุดิบต่อเมนู (Recipe) รองรับกรองด้วย query param menu",
        "fields": "id, menu, menu_name, ingredient, ingredient_name, ingredient_unit, quantity",
    },
    {
        "name": "reviews",
        "service": "ReviewViewSet",
        "file": "myapp/api.py:536",
        "type": "CRUD",
        "methods": "GET ✅ | POST | PUT/PATCH | DELETE ✅",
        "params": "?menu=<id> (กรองรีวิวของเมนู)",
        "auth": "อ่าน: ทุกคน | เขียน/แก้/ลบ: ต้องล็อกอิน (ลบได้เฉพาะรีวิวตัวเอง)",
        "detail": "รีวิว/ให้คะแนนเมนู 1-5 ดาว — ผู้ใช้ให้เมนูละ 1 ครั้ง (รีวิวซ้ำ = อัปเดตอันเดิม ด้วย update_or_create)",
        "fields": "id, menu, username, rating (1-5), comment, created_at",
    },
    {
        "name": "points/rewards",
        "service": "PointRewardViewSet",
        "file": "myapp/api.py:573",
        "type": "อ่านอย่างเดียว + Action",
        "methods": "GET ✅ | redeem ✅",
        "params": "redeem: -",
        "auth": "อ่าน: ทุกคน (เห็นเฉพาะที่เปิดใช้งาน) | แลก: ต้องล็อกอิน",
        "detail": "สิทธิ์แลกคะแนน แลกสำเร็จจะออกคูปองรหัส PTS-... ผูกเจ้าของ อายุ 30 วัน และตัดคะแนนผ่าน ledger",
        "fields": "id, name, description, points_cost, discount_type, value, min_order, is_active",
        "actions": [
            ("POST /api/points/rewards/{id}/redeem/", "แลกคะแนนเป็นสิทธิ์ คืน {error, code, balance, reward{...}} — คะแนนไม่พอคืน 400"),
        ],
    },
    {
        "name": "points/transactions",
        "service": "PointTransactionViewSet",
        "file": "myapp/api.py:626",
        "type": "อ่านอย่างเดียว",
        "methods": "GET ✅",
        "params": "-",
        "auth": "ต้องล็อกอิน เห็นเฉพาะประวัติของตัวเอง (Staff เห็นทั้งหมด)",
        "detail": "ประวัติคะแนน (ledger) — read-only ทั้งหมด กันแก้ไขย้อนหลัง",
        "fields": "id, user, points_change, balance_after, reason, reward, reward_name, created_at",
    },
    {
        "name": "profile",
        "service": "ProfileViewSet",
        "file": "myapp/api.py:638",
        "type": "Action เดียว",
        "methods": "me: GET ✅ | me: PATCH/PUT ✅",
        "params": "PATCH me: multipart/form-data (avatar, cover)",
        "auth": "ต้องล็อกอิน (พบเฉพาะตัวเอง)",
        "detail": "โปรไฟล์ตัวเอง + ยอดคะแนน/สถานะสมาชิก — อัปเดต avatar/cover ด้วย multipart",
        "fields": "id, username, email, avatar, cover, membership_status, points, points_rate, discount_percent, free_delivery, max_favorites",
        "actions": [
            ("GET /api/profile/me/", "ดูโปรไฟล์ตัวเอง + คะแนน/สถานะสมาชิก/ส่วนลด"),
            ("PATCH /api/profile/me/", "แก้ไขโปรไฟล์ตัวเอง (avatar / cover ใช้ multipart/form-data)"),
        ],
    },
    {
        "name": "notifications",
        "service": "NotificationViewSet",
        "file": "myapp/api.py:676",
        "type": "อ่านอย่างเดียว + Action",
        "methods": "GET ✅ | read ✅ | read_all ✅",
        "params": "-",
        "auth": "ต้องล็อกอิน เห็นเฉพาะแจ้งเตือนของตัวเอง (Staff เห็นส่วนกลางด้วย)",
        "detail": "รายการแจ้งเตือน — Throttle 60 ครั้ง/นาที เครื่องหมายอ่านแล้ว/อ่านทั้งหมด",
        "fields": "id, kind(+display), title, message, link, is_read, created_at",
        "actions": [
            ("POST /api/notifications/{id}/read/", "ทำเครื่องหมายว่าอ่านแล้ว คืน {ok: True}"),
            ("POST /api/notifications/read_all/", "อ่านทั้งหมด คืน {ok: True, updated: <จำนวน>}"),
        ],
    },
    {
        "name": "store",
        "service": "StoreInfoView",
        "file": "myapp/api.py:705",
        "type": "อ่านอย่างเดียว",
        "methods": "GET ✅",
        "params": "-",
        "auth": "เข้าชมได้ทุกคน (Staff เห็นการตั้งค่าเพิ่มเติม)",
        "detail": "ข้อมูลร้าน พิกัด/ค่าส่ง/แผนที่ — เผยแพร่สาธารณะ ห้ามรั่ว LINE token แต่ Staff เห็น promptpay_id, notification_email",
        "fields": "name, lat, lng, address, fee_base, fee_per_km, free_delivery_over, maps_url + (Staff) auto_assign_enabled, auto_assign_grace_minutes, auto_release_minutes, promptpay_id, notification_email, notify_order, notify_reservation, notify_review",
    },
]

PERMISSION_MAP = {
    "admin": "เฉพาะ Admin (is_staff/superuser)",
    "login": "ต้องล็อกอิน",
    "login_rw": "ล็อกอินสำหรับเขียน, อ่านได้ทุกคน",
    "public": "ทุกคน (AllowAny)",
    "owner": "เฉพาะเจ้าของข้อมูล",
}


def build_cover(styles, brand):
    flow = []
    flow.append(Spacer(1, 40 * mm))
    flow.append(Paragraph("สรุปการเชื่อมต่อ API", brand["h1"]))
    flow.append(Spacer(1, 6 * mm))
    flow.append(Paragraph("Django REST Framework — ระบบร้านค้าอาหารออนไลน์", brand["sub"]))
    flow.append(Spacer(1, 18 * mm))
    flow.append(HRFlowable(width="70%", thickness=1.2, color=colors.HexColor("#b3261e")))
    flow.append(Spacer(1, 10 * mm))
    summary = Table([
        ["ไฟล์ API หลัก", "myapp/api.py"],
        ["ลงทะเบียน URL", "myapp/urls.py : path('api/', include(api_urlpatterns))"],
        ["จุดรวม (Prefix)", "/api/"],
        ["วงจร Endpoint", f"{len(ENDPOINTS)} กลุ่ม"],
        ["การยืนยันตัวตน", "SessionAuthentication"],
        ["การแบ่งหน้า", "PageNumberPagination (20 รายการ/หน้า)"],
        ["จำกัดอัตรา (Throttle)", "reservation: 5/ชม. | notification: 60/นาที"],
    ], colWidths=[45 * mm, 105 * mm])
    summary.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
        ("FONTNAME", (0, 0), (0, -1), FONT_BOLD),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#b3261e")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#fff4e6")),
        ("ROWBACKGROUNDS", (1, 0), (1, -1), [colors.white, colors.HexColor("#faf6ef")]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d8cbb8")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    flow.append(summary)
    return flow


def build_overview(styles, brand):
    flow = []
    flow.append(Paragraph("ภาพรวมการออกแบบ", brand["h2"]))
    flow.append(Spacer(1, 3 * mm))
    rows = [
        ["สถานะแบบบังคับ (Read-only)", "orders.status, orders.payment_method, orders.paid_at ถูกห้ามแก้ผ่าน API กันผู้ใช้ PATCH ให้ออเดอร์ตัวเอง 'จ่ายแล้ว' โดยไม่ต้องจ่าย"],
        ["แยกสิทธิ์ตามบทบาท", "ระบุชัดเจนทุก ViewSet ว่าใครอ่านได้/เขียนได้ (ทุกคน / ล็อกอิน / เฉพาะเจ้าของ / เฉพาะ Admin)"],
        ["กรองข้อมูลส่วนบุคคล", "Delivery ซ่อนชื่อ/เบอร์/ที่อยู่ สำหรับผู้ใช้ทั่วไป (ข้อมูลผู้รับแบบ Mask)"],
        ["ป้องกันการแก้ย้อนหลัง", "points/transactions เป็น read-only (กันแก้ ledger), รีวิวลบได้เฉพาะเจ้าของ"],
        ["กันสแปม/โจมตี", "Throttle การจองโต๊ะและแจ้งเตือน, สร้าง data ของผู้ใช้คนอื่นไม่ได้ (ผูก created_by/owner)"],
        ["เผยแพร่ข้อมูลสาธารณะ", "เมนู/หมวดหมู่/เครื่องเคียง/คูปอง/สิทธิ์แลกคะแนน อ่านได้โดยไม่ต้องล็อกอิน"],
        ["Integration LINE", "จองโต๊ะสำเร็จ -> announce_new_reservation ส่ง LINE Notify (myapp/services.py:105)"],
    ]
    t = Table([[Paragraph(r[0], brand["cell_bold"]), Paragraph(r[1], brand["cell"])] for r in rows],
              colWidths=[42 * mm, 108 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#b3261e")),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
        ("ROWBACKGROUNDS", (1, 0), (1, -1), [colors.white, colors.HexColor("#faf6ef")]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d8cbb8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    flow.append(t)
    return flow


def build_endpoints(styles, brand):
    flow = []
    flow.append(Paragraph("ตารางรวม Endpoint ทั้งหมด", brand["h2"]))
    flow.append(Spacer(1, 3 * mm))
    header = ["URL (ภายใต้ /api/)", "Method / Action", "สิทธิ์การเข้าถึง"]
    rows = [header]
    for ep in ENDPOINTS:
        rows.append([
            f"<b>{ep['name']}</b>",
            ep["methods"],
            ep["auth"],
        ])
    t = Table([[Paragraph(c, brand["th"]) for c in header]]
              + [[Paragraph(r[0], brand["cell_bold"]),
                  Paragraph(r[1], brand["cell"]),
                  Paragraph(r[2], brand["cell"])] for r in rows[1:]],
              colWidths=[34 * mm, 52 * mm, 64 * mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#b3261e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#faf6ef")]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d8cbb8")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    flow.append(t)

    # รายละเอียดรายกลุ่ม
    flow.append(PageBreak())
    for i, ep in enumerate(ENDPOINTS, 1):
        flow.append(Paragraph(
            f"{i}. {ep['name']}  <font size=9 color='#8a6d5f'>— {ep['service']} ({ep['file']})</font>",
            brand["h3"]))
        flow.append(Paragraph(
            f"ประเภท: {ep['type']}  |  ข้อความส่ง: {ep['params']}", brand["meta"]))
        flow.append(Spacer(1, 2 * mm))

        detail_rows = [
            ["รายละเอียด", ep["detail"]],
            ["สิทธิ์เข้าถึง", ep["auth"]],
            ["ฟิลด์ (Fields)", ep["fields"]],
        ]
        if ep.get("actions"):
            for method, desc in ep["actions"]:
                detail_rows.append(["Action (POST)", f"<b>{method}</b><br/>{desc}"])
        dt = Table([[Paragraph(r[0], brand["cell_bold"]), Paragraph(r[1], brand["cell"])]
                    for r in detail_rows], colWidths=[40 * mm, 110 * mm])
        dt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f5ded5")),
            ("FONTNAME", (0, 0), (0, -1), FONT_BOLD),
            ("ROWBACKGROUNDS", (1, 0), (1, -1), [colors.white, colors.HexColor("#fdf7ef")]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dcc4b4")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        flow.append(dt)
        flow.append(Spacer(1, 4 * mm))

    # สรุปหัวข้อกฎความปลอดภัย
    flow.append(Paragraph("ข้อควรจำด้านสิทธิ์ (สรุป)", brand["h2"]))
    rules = [
        "อ่านได้ทุกคน (AllowAny / IsAuthenticatedOrReadOnly): categories, menus, addons, store, reviews (GET), points/rewards (GET)",
        "อ่านต้องล็อกอิน: profile, notifications, points/transactions",
        "เขียนต้องล็อกอิน: orders, deliveries (สร้าง), reviews (เขียน/แก้/ลบ), points/rewards (redeem), coupons (validate)",
        "เฉพาะ Admin (IsAdminUser): สร้าง/แก้/ลบ menus, addons, ingredients, recipes, coupons, reservations (แก้/ลบ/สถานะ), deliveries (แก้/ลบ)",
        "ทั้งหมดถูกปิดด้วย DEFAULT_PERMISSION_CLASSES = IsAuthenticatedOrReadOnly ที่ settings.py:220",
    ]
    for r in rules:
        flow.append(Paragraph(f"• {r}", brand["cell"]))
        flow.append(Spacer(1, 1.5 * mm))

    return flow


def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(FONT_NAME, 8)
    canvas.setFillColor(colors.HexColor("#8a6d5f"))
    canvas.drawString(15 * mm, 14 * mm,
                      "สรุปการเชื่อมต่อ API — สร้างอัตโนมัติจาก myapp/api.py + myapp/urls.py")
    canvas.drawRightString(195 * mm, 14 * mm, f"หน้า {doc.page}")
    canvas.setStrokeColor(colors.HexColor("#dcc4b4"))
    canvas.setLineWidth(0.4)
    canvas.line(15 * mm, 17 * mm, 195 * mm, 17 * mm)
    canvas.restoreState()


def main():
    ss = getSampleStyleSheet()
    brand = {
        "h1": ParagraphStyle("h1", parent=ss["Title"], fontName=FONT_BOLD, fontSize=26,
                             leading=32, textColor=colors.HexColor("#b3261e"),
                             alignment=TA_CENTER),
        "sub": ParagraphStyle("sub", parent=ss["BodyText"], fontName=FONT_NAME, fontSize=13,
                              leading=18, textColor=colors.HexColor("#6b564a"),
                              alignment=TA_CENTER),
        "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontName=FONT_BOLD, fontSize=16,
                             leading=20, spaceAfter=6, textColor=colors.HexColor("#b3261e")),
        "h3": ParagraphStyle("h3", parent=ss["Heading3"], fontName=FONT_BOLD, fontSize=11.5,
                             leading=15, spaceBefore=6, spaceAfter=1,
                             textColor=colors.HexColor("#333333")),
        "meta": ParagraphStyle("meta", parent=ss["Normal"], fontName=FONT_NAME, fontSize=8.5,
                               leading=12, textColor=colors.HexColor("#8a6d5f")),
        "cell": ParagraphStyle("cell", parent=ss["Normal"], fontName=FONT_NAME, fontSize=9,
                               leading=12.5),
        "cell_bold": ParagraphStyle("cell_bold", parent=ss["Normal"], fontName=FONT_BOLD,
                                    fontSize=9, leading=12.5),
        "th": ParagraphStyle("th", parent=ss["Normal"], fontName=FONT_BOLD, fontSize=9.5,
                             leading=13, textColor=colors.white),
    }
    doc = SimpleDocTemplate(OUTPUT, pagesize=A4,
                            leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=18 * mm, bottomMargin=20 * mm,
                            title="สรุปการเชื่อมต่อ API",
                            author="Generated by opencode")
    story = []
    story.extend(build_cover(brand, brand))
    story.append(PageBreak())
    story.extend(build_overview(brand, brand))
    story.extend(build_endpoints(brand, brand))
    doc.build(story, onFirstPage=lambda c, d: header_footer(c, d),
              onLaterPages=lambda c, d: header_footer(c, d))
    print("SAVED:", OUTPUT)
    print("SIZE:", os.path.getsize(OUTPUT), "bytes")


if __name__ == "__main__":
    main()
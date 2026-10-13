# -*- coding: utf-8 -*-
"""Generate external API connection summary PDF (Thai) using reportlab."""

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
                      "docs", "สรุป_API_ภายนอก.pdf")

# ----------------------------------------------------------------------
# ข้อมูล API ภายนอกของโปรเจกต์
# ----------------------------------------------------------------------

APIS = [
    {
        "name": "Google Maps Embed",
        "endpoint": "https://maps.google.com/maps?output=embed",
        "purpose": "แสดงแผนที่ตำแหน่งร้าน / ปลายทางเดลิเวอร์รี่บนหน้าเว็บ (iframe)",
        "how": "แทรก &lt;iframe src=&quot;https://maps.google.com/maps?q=&lt;lat&gt;,&lt;lng&gt;&amp;z=&lt;zoom&gt;&amp;output=embed&quot;&gt;",
        "auth": "ไม่ต้องใช้ API Key (ฟรี)",
        "type": "แสดงผล (Display) — โหลดจากฝั่งเบราว์เซอร์",
        "files": "myapp/templates/core/contact.html, myapp/templates/delivery/delivery_settings.html, myapp/templates/order/order_detail.html",
        "notes": "เลือกตำแหน่งใหม่ ใช้ปุ่ม \"เปิด Google Maps เต็มจอ\" จากนั้นก๊อปปี้พิกัดมาวางที่ช่องละติจูด/ลองจิจูด (แผนที่ฝั่งเว็บจะอัปเดตให้อัตโนมัติผ่าน JS)",
    },
    {
        "name": "Line Notify",
        "endpoint": "POST https://notify-api.line.me/api/notify",
        "purpose": "ส่งแจ้งเตือนออเดอร์ใหม่ / จองโต๊ะ / รีวิวใหม่ ไปยัง Line ของร้าน",
        "how": "requests.post()  Header: Authorization: Bearer <token>  ตัวแปร: message",
        "auth": "Line Notify Token — ตั้งที่ Admin (StoreLocation.line_notify_token) หรือตัวแปรสภาพแวดล้อม LINE_NOTIFY_TOKEN",
        "type": "ส่งออก (Outbound) — ฝั่งเซิร์ฟเวอร์",
        "files": "myapp/services.py: notify_line(), line_notify_status(), announce_*(); myapp/views.py: line_notify_test; URL: /delivery/settings/test-line/",
        "notes": "หมดเวลา 8 วินาที/ครั้ง, ลองใหม่ (Retry) รวม 3 ครั้งเมื่อเจอ 429/5xx/เน็ตหลุด — token ผิด (400) จบเลย ไม่เสียเวลาลองซ้ำ; มีปุ่ม \"ส่งข้อความทดสอบ\" ที่หน้าตั้งค่าเดลิเวอร์รี่; token แสดงแบบซ่อนใน Admin",
    },
    {
        "name": "Nominatim / OpenStreetMap",
        "endpoint": "GET https://nominatim.openstreetmap.org/search",
        "purpose": "เปลี่ยนที่อยู่จัดส่ง (ข้อความ) → พิกัด GPS แล้วคำนวณระยะทาง/ค่าส่งอัตโนมัติ",
        "how": "requests.get()  ตัวแปร: q=<address>, format=json, limit=1, countrycodes=th  Header ต้องมี User-Agent ตามนโยบาย OSM",
        "auth": "ไม่ต้องใช้ API Key — มีข้อจำกัด 1 คำขอ/วินาที ใช้เฉพาะตอนกดปุ่ม \"ค้นหาพิกัดที่อยู่\"",
        "type": "ส่งออก (Outbound) — ฝั่งเซิร์ฟเวอร์",
        "files": "myapp/services.py: geocode_address(); myapp/models.py: Delivery.geocode_from_address(); myapp/views.py: delivery_geocode; URL: /delivery/<pk>/geocode/",
        "notes": "จับ error ทั้งหมดคืน None (ไม่ทำให้สั่งอาหารพัง); เจอพิกัดแล้ว Delivery.save() คำนวณระยะทาง (Haversine) + ค่าส่งให้เอง",
    },
    {
        "name": "Google OAuth 2.0 (Sign-In)",
        "endpoint": "ระบบ OAuth ของ Google (ผ่าน django-allauth)",
        "purpose": "ให้ผู้ใช้ล็อกอินด้วยบัญชี Google แทนการสมัครสมาชิกแบบฟอร์ม",
        "how": "allauth.socialaccount.providers.google — เบราว์เซอร์พาผู้ใช้ไปหน้า Google แล้วรับ token กลับมา",
        "auth": "GOOGLE_OAUTH_CLIENT_ID + GOOGLE_OAUTH_CLIENT_SECRET (env) + SocialApp ในฐานข้อมูล",
        "type": "OAuth (Web Redirect flow) — ฝั่งเบราว์เซอร์ + เซิร์ฟเวอร์",
        "files": "myproject/settings.py; myapp/views.py: google_login_redirect; myapp/management/commands/create_google_app.py",
        "notes": "ตั้งค่าได้ผ่านคำสั่ง `python manage.py create_google_app` — เลื่อนเปิด Social login เมื่อข้อมูลครบ แล้วหน้า Login จะแสดงปุ่ม \"เข้าสู่ระบบด้วย Google\"",
    },
    {
        "name": "Email (SMTP)",
        "endpoint": "โปรโตคอล SMTP (ตาม EMAIL_BACKEND)",
        "purpose": "ส่งอีเมลแจ้งเตือน + ลิงก์รีเซ็ตรหัสผ่าน",
        "how": "Django send_mail() — โหมดพัฒนา (default) ใช้ Console backend ส่งอีเมลลง terminal เพื่อไม่ต้องตั้ง SMTP จริง",
        "auth": "คอนฟิกผ่าน env: DJANGO_EMAIL_BACKEND, DEFAULT_FROM_EMAIL (และ SMTP_HOST/USER/PASSWORD ตาม backend)",
        "type": "ส่งออก (Outbound) — ฝั่งเซิร์ฟเวอร์",
        "files": "myapp/services.py: notify_email(); myapp/templates/core/auth/password_reset_form.html (เจเนอเรต URL ยืนยันจาก Django)",
        "notes": "notify_email() ยอมรับ list/str และพยายามส่งแบบ fail_silently เพื่อไม่ให้บางไปเพราะอีเมล",
    },
]

PRINCIPLES = [
    "แยกงานภายนอกไว้ในไฟล์เดียว `myapp/services.py` — หน้าเว็บ/API ภายในเรียกผ่านฟังก์ชันพวกนี้ ไม่เรียก requests เอง",
    "เก็บความลับไว้นอกโค้ด — token/key ผ่านตัวแปรสภาพแวดล้อม (env) หรือฐานข้อมูล (StoreLocation) ไม่ฝังใน source",
    "กันระบบพัง — ทุกฟังก์ชันจับ error แล้วคืน False/None (เช่น เน็ตหลุดแค่ข้ามการแจ้งเตือน ไม่ทำให้สั่งอาหารผิด)",
    "หมดเวลาทุกครั้ง — ทุกการเรียกใช้ timeout=8 วินาที ไม่ปล่อยให้ค้างคา request ไว้",
    "เทสต์โดยไม่ยิง API จริง — ใช้ unittest.mock แทน requests.get/post ทั้งหมดใน myapp/tests.py (178 เทสต์ผ่าน)",
    "ตั้งค่า/จัดการได้จากหน้าเว็บ — ปุ่ม \"ค้นหาพิกัดที่อยู่\" (Geocode), \"ส่งข้อความทดสอบ\" (Line), ตั้งตำแหน่งร้านในหน้าตั้งค่าเดลิเวอร์รี่",
]

SECURITY_NOTES = [
    "Line Notify token ถูกซ่อนผ่าน mask_token() — Admin โชว์แค่ท้าย 4 ตัว, REST API /api/store/ กรองข้อมูลนี้ไม่ให้รั่วออกนอก",
    "Nominatim ต้องส่ง User-Agent บอกตัวตนทุกครั้ง ตามนโยบายการใช้งานของ OpenStreetMap (GeoNames/OSMF policy)",
    "Google OAuth ใช้ SOCIALACCOUNT_ONLY + ตรวจ EMAIL_VERIFICATION='none' เพื่อให้เข้าสู่ระบบรวดเร็วแต่ยืนยันตัวตนจาก Google แล้ว",
    "ฟีเจอร์ลากหมุดเพื่อตั้งพิกัด ต้องใช้ Google Maps JavaScript API (ต้องมี API Key) — โครงการนี้ใช้วิธีกรอกพิกัด + ลิงก์เปิด Google Maps แทน (embed แบบไม่ใช้ Key)",
]


def build_cover(brand):
    flow = []
    flow.append(Spacer(1, 40 * mm))
    flow.append(Paragraph("สรุปการเชื่อมต่อ API ภายนอก", brand["h1"]))
    flow.append(Spacer(1, 6 * mm))
    flow.append(Paragraph("ระบบร้านอาหารออนไลน์ \"อร่อยเกินเบอร์\"", brand["sub"]))
    flow.append(Spacer(1, 18 * mm))
    flow.append(HRFlowable(width="70%", thickness=1.2, color=colors.HexColor("#b3261e")))
    flow.append(Spacer(1, 10 * mm))
    summary = Table([
        ["ไฟล์รวมฟังก์ชัน API ภายนอก", "myapp/services.py"],
        ["จำนวนบริการที่เชื่อมต่อ", f"{len(APIS)} บริการ"],
        ["แบบใช้ API Key", "Line Notify (Token), Google OAuth (Client ID/Secret), SMTP (ตาม backend)"],
        ["แบบไม่ใช้ Key (ฟรี)", "Google Maps Embed, Nominatim/OpenStreetMap"],
        ["ไลบรารี", "requests (ส่งคำขอ) | reportlab (สร้างเอกสารฉบับนี้)"],
        ["การทดสอบ", "mock ทั้งหมดใน myapp/tests.py — 178 เทสต์"]
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


def build_principles(brand):
    flow = []
    flow.append(Paragraph("หลักการออกแบบการเชื่อมต่อ API ภายนอก", brand["h2"]))
    flow.append(Spacer(1, 3 * mm))
    rows = [[Paragraph(f"{PRINCIPLES[i].split(' — ')[0]}", brand["cell_bold"]),
             Paragraph(PRINCIPLES[i].split(" — ", 1)[1], brand["cell"])]
            for i in range(len(PRINCIPLES))]
    t = Table(rows, colWidths=[45 * mm, 105 * mm])
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


def build_apis(brand):
    flow = []
    flow.append(Paragraph("ตารางรวมบริการภายนอกทั้งหมด", brand["h2"]))
    flow.append(Spacer(1, 3 * mm))
    header = ["บริการ", "ใช้ทำอะไร", "ต้องใช้ Key?"]
    rows = [header] + [
        [api["name"], api["purpose"], api["auth"]]
        for api in APIS
    ]
    t = Table([[Paragraph(c, brand["th"]) for c in header]]
              + [[Paragraph(r[0], brand["cell_bold"]),
                  Paragraph(r[1], brand["cell"]),
                  Paragraph(r[2], brand["cell"])] for r in rows[1:]],
              colWidths=[38 * mm, 66 * mm, 46 * mm], repeatRows=1)
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

    # รายละเอียดรายบริการ
    flow.append(PageBreak())
    for i, api in enumerate(APIS, 1):
        flow.append(Paragraph(
            f"{i}. {api['name']}  <font size=9 color='#8a6d5f'>— {api['type']}</font>",
            brand["h3"]))
        flow.append(Paragraph(f"Endpoint: {api['endpoint']}", brand["meta"]))
        flow.append(Spacer(1, 2 * mm))

        detail_rows = [
            ["วัตถุประสงค์", api["purpose"]],
            ["วิธีเรียกใช้", api["how"]],
            ["การยืนยันตัวตน", api["auth"]],
            ["ไฟล์ที่เกี่ยวข้อง", api["files"]],
            ["หมายเหตุ", api["notes"]],
        ]
        dt = Table([[Paragraph(r[0], brand["cell_bold"]), Paragraph(r[1], brand["cell"])]
                    for r in detail_rows], colWidths=[38 * mm, 112 * mm])
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
        flow.append(Spacer(1, 5 * mm))

    # หมายเหตุความปลอดภัย
    flow.append(Paragraph("หมายเหตุด้านความปลอดภัย", brand["h2"]))
    for note in SECURITY_NOTES:
        flow.append(Paragraph(f"• {note}", brand["cell"]))
        flow.append(Spacer(1, 1.5 * mm))

    return flow


def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(FONT_NAME, 8)
    canvas.setFillColor(colors.HexColor("#8a6d5f"))
    canvas.drawString(15 * mm, 14 * mm,
                      "สรุปการเชื่อมต่อ API ภายนอก — สร้างอัตโนมัติจาก myapp/services.py + settings.py")
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
                            title="สรุปการเชื่อมต่อ API ภายนอก",
                            author="Generated by opencode")
    story = []
    story.extend(build_cover(brand))
    story.append(PageBreak())
    story.extend(build_principles(brand))
    story.extend(build_apis(brand))
    doc.build(story, onFirstPage=lambda c, d: header_footer(c, d),
              onLaterPages=lambda c, d: header_footer(c, d))
    print("SAVED:", OUTPUT)
    print("SIZE:", os.path.getsize(OUTPUT), "bytes")


if __name__ == "__main__":
    main()
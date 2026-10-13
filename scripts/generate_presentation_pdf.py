# -*- coding: utf-8 -*-
"""Generate Thai Presentation Slide PDF (Landscape 16:9/A4) for Django Project using ReportLab."""

import os
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_PDF = os.path.join(BASE_DIR, "docs", "ไฟล์นำเสนอ_โครงงานระบบจัดการร้านอาหาร.pdf")

FONT_PATH = r"C:\Windows\Fonts\tahoma.ttf"
FONT_BOLD_PATH = r"C:\Windows\Fonts\tahomabd.ttf"
FONT_NAME = "Tahoma"
FONT_BOLD = "Tahoma-Bold"

pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH))
pdfmetrics.registerFont(TTFont(FONT_BOLD, FONT_BOLD_PATH))
pdfmetrics.registerFontFamily(FONT_NAME, normal=FONT_NAME, bold=FONT_BOLD,
                              italic=FONT_NAME, boldItalic=FONT_BOLD)

PRIMARY_COLOR = colors.HexColor("#b3261e")
SECONDARY_COLOR = colors.HexColor("#6b564a")
ACCENT_COLOR = colors.HexColor("#1b5e20")
DARK_COLOR = colors.HexColor("#212121")
LIGHT_BG = colors.HexColor("#faf6ef")
CARD_BG = colors.HexColor("#ffffff")
BORDER_COLOR = colors.HexColor("#d8cbb8")
TOTAL_SLIDES = 14


def slide_decorator(canvas, doc):
    canvas.saveState()
    # Header line
    if doc.page > 1:
        canvas.setFont(FONT_NAME, 8)
        canvas.setFillColor(SECONDARY_COLOR)
        canvas.drawString(15 * mm, 198 * mm, "โครงงานพัฒนาระบบเว็บแอปพลิเคชันด้วย Django Framework | ระบบจัดการร้านอาหาร 'อร่อยเกินเบอร์'")
        canvas.setStrokeColor(BORDER_COLOR)
        canvas.setLineWidth(0.4)
        canvas.line(15 * mm, 195 * mm, 282 * mm, 195 * mm)

    # Footer
    canvas.setFont(FONT_NAME, 8)
    canvas.setFillColor(SECONDARY_COLOR)
    canvas.drawString(15 * mm, 8 * mm, "URL: https://omg02.onrender.com | GitHub: omgx624-gif/OMg02")
    canvas.drawRightString(282 * mm, 8 * mm, f"สไลด์ที่ {doc.page} / {TOTAL_SLIDES}")
    canvas.setStrokeColor(BORDER_COLOR)
    canvas.setLineWidth(0.4)
    canvas.line(15 * mm, 11 * mm, 282 * mm, 11 * mm)
    canvas.restoreState()


def get_slide_styles():
    ss = getSampleStyleSheet()
    styles = {
        "slide_title": ParagraphStyle("SlideTitle", fontName=FONT_BOLD, fontSize=18, leading=22, textColor=PRIMARY_COLOR, spaceAfter=2),
        "slide_subtitle": ParagraphStyle("SlideSubtitle", fontName=FONT_NAME, fontSize=10, leading=14, textColor=SECONDARY_COLOR, spaceAfter=4),
        "cover_main": ParagraphStyle("CoverMain", fontName=FONT_BOLD, fontSize=24, leading=30, textColor=PRIMARY_COLOR, alignment=TA_CENTER),
        "cover_sub": ParagraphStyle("CoverSub", fontName=FONT_NAME, fontSize=12, leading=17, textColor=SECONDARY_COLOR, alignment=TA_CENTER),
        "card_title": ParagraphStyle("CardTitle", fontName=FONT_BOLD, fontSize=11, leading=15, textColor=PRIMARY_COLOR, spaceAfter=2),
        "card_body": ParagraphStyle("CardBody", fontName=FONT_NAME, fontSize=9, leading=13.5, textColor=DARK_COLOR),
        "bullet": ParagraphStyle("SlideBullet", fontName=FONT_NAME, fontSize=9.5, leading=14.5, textColor=DARK_COLOR, leftIndent=8, spaceAfter=2),
        "th": ParagraphStyle("SlideTH", fontName=FONT_BOLD, fontSize=9, leading=12, textColor=colors.white, alignment=TA_CENTER),
        "cell": ParagraphStyle("SlideCell", fontName=FONT_NAME, fontSize=8.5, leading=11.5, textColor=DARK_COLOR),
        "cell_center": ParagraphStyle("SlideCellCenter", fontName=FONT_NAME, fontSize=8.5, leading=11.5, textColor=DARK_COLOR, alignment=TA_CENTER),
        "cell_bold": ParagraphStyle("SlideCellBold", fontName=FONT_BOLD, fontSize=8.5, leading=11.5, textColor=DARK_COLOR),
    }
    return styles


def make_card(title, content, styles, width=128 * mm, bg=LIGHT_BG, border=PRIMARY_COLOR):
    data = [
        [Paragraph(title, styles["card_title"])],
        [Paragraph(content, styles["card_body"])],
    ]
    t = Table(data, colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("BOX", (0, 0), (-1, -1), 1, border),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ]))
    return t


def build_slides(s):
    story = []

    # -------------------------------------------------------------
    # SLIDE 1: หน้าปก (Title Slide)
    # -------------------------------------------------------------
    story.append(Spacer(1, 15 * mm))
    story.append(Paragraph("การนำเสนอโครงงานพัฒนาระบบเว็บแอปพลิเคชัน (Django Framework)", s["cover_sub"]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("ระบบจัดการร้านอาหารและสั่งอาหารออนไลน์<br/>'อร่อยเกินเบอร์' (Aroy Gern Ber)", s["cover_main"]))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("กรณีศึกษา: ร้านผัดกะเพรารวมมิตร ครอบคลุมระบบสั่งอาหาร โต๊ะ QR เดลิเวอรี่ และคลังสต็อก", s["cover_sub"]))
    story.append(Spacer(1, 5 * mm))
    story.append(HRFlowable(width="50%", thickness=2, color=PRIMARY_COLOR, spaceAfter=8 * mm))

    cover_meta = [
        [Paragraph("<b>เทคโนโลยีหลัก:</b> Python 3.14 · Django 6.0 · Bootstrap 5 · Docker · Render Cloud", s["cell_center"])],
        [Paragraph("<b>URL ใช้งานจริง:</b> https://omg02.onrender.com | <b>GitHub:</b> omgx624-gif/OMg02", s["cell_center"])],
        [Paragraph("<b>บัญชีทดสอบ:</b> Admin: admin (Admin1234!) | Staff: staff (Staff1234!) | Customer: customer (User1234!)", s["cell_center"])],
    ]
    t_cm = Table(cover_meta, colWidths=[240 * mm])
    t_cm.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
        ("BOX", (0, 0), (-1, -1), 1, BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_cm)
    story.append(PageBreak())

    # -------------------------------------------------------------
    # SLIDE 2: ปัญหาและที่มาของโครงงาน (Problem Statement)
    # -------------------------------------------------------------
    story.append(Paragraph("ปัญหาและที่มาของโครงงาน (Problem Statement & Motivation)", s["slide_title"]))
    story.append(Paragraph("การบริหารจัดการร้านอาหารแบบดั้งเดิม vs การแก้ปัญหาด้วยเว็บแอปพลิเคชัน", s["slide_subtitle"]))
    story.append(Spacer(1, 3 * mm))

    col1 = make_card(
        "❌ ปัญหาของร้านอาหารแบบดั้งเดิม (Pain Points)",
        "• <b>การจดออเดอร์ด้วยกระดาษ:</b> เกิดข้อผิดพลาดง่าย ลายมืออ่านยาก ออเดอร์ตกหล่น<br/>"
        "• <b>การส่งออเดอร์เข้าห้องครัวล่าช้า:</b> พนักงานต้องเดินไปส่งใบออเดอร์ เสียเวลาบริการลูกค้า<br/>"
        "• <b>ไม่ทราบสต็อกวัตถุดิบเรียลไทม์:</b> วัตถุดิบหมดกลางคันโดยไม่รู้ล่วงหน้า เสียโอกาสขาย<br/>"
        "• <b>คิดเงินและคำนวณยอดขายช้า:</b> สรุปยอดขายประจำวันต้องนับบิลกระดาษ ตรวจสอบย้อนหลังยาก<br/>"
        "• <b>การจัดส่งเดลิเวอรี่ไม่มีระบบ:</b> จดที่อยู่ผิด พลาดการติดตามสถานะการส่งของไรเดอร์",
        s, width=130 * mm, bg=colors.HexColor("#ffebee"), border=PRIMARY_COLOR
    )

    col2 = make_card(
        "✅ โซลูชันของระบบ 'อร่อยเกินเบอร์' (Our Solution)",
        "• <b>สั่งอาหารผ่านเว็บ/QR โต๊ะ:</b> ลูกค้าสั่งเองได้ทันที ไม่ต้องรอพนักงานมารับรายการ<br/>"
        "• <b>ระบบ Kitchen Display:</b> ออเดอร์เด้งเข้าห้องครัวแบบเรียลไทม์ พร้อมตัวนับเวลารอ<br/>"
        "• <b>สูตรอาหารตัดสต็อกอัตโนมัติ:</b> สั่งเมนูไหน วัตถุดิบในคลังลดลงทันที พร้อมเตือนใกล้หมด<br/>"
        "• <b>แดชบอร์ดสรุปยอดขาย + Chart.js:</b> สถิติรายวัน/สัปดาห์/เดือน พร้อมส่งออก Excel/CSV<br/>"
        "• <b>เดลิเวอรี่คำนวณพิกัด GPS อัตโนมัติ:</b> ปักหมุดที่อยู่ คำนวณระยะทางและค่าส่งตามจริง",
        s, width=130 * mm, bg=colors.HexColor("#e8f5e9"), border=ACCENT_COLOR
    )

    t_p2 = Table([[col1, col2]], colWidths=[133 * mm, 133 * mm])
    t_p2.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(t_p2)
    story.append(PageBreak())

    # -------------------------------------------------------------
    # SLIDE 3: วัตถุประสงค์และภาพรวมระบบ (Objectives & System Overview)
    # -------------------------------------------------------------
    story.append(Paragraph("วัตถุประสงค์และภาพรวมระบบ (Objectives & Architecture)", s["slide_title"]))
    story.append(Paragraph("เป้าหมายการพัฒนา และสถาปัตยกรรม Model-Template-View (MTV)", s["slide_subtitle"]))
    story.append(Spacer(1, 3 * mm))

    objs_text = (
        "<b>วัตถุประสงค์หลักของโครงงาน:</b><br/>"
        "1. พัฒนาระบบเว็บแอปพลิเคชันบริหารจัดการร้านอาหารครบวงจรด้วย Django Framework 6.0<br/>"
        "2. รองรับกระบวนการสั่งอาหารทั้งหน้าร้าน (Dine-in) และจัดส่งถึงบ้าน (Delivery)<br/>"
        "3. ออกแบบระบบควบคุมสิทธิ์ผู้ใช้ 3 บทบาทจริง (Customer, Staff, Admin)<br/>"
        "4. พัฒนาฟังก์ชันโบนัสขั้นสูง: REST API, External API, กราฟสถิติ, และ Automated Tests 245 ข้อ<br/>"
        "5. ติดตั้งใช้งานจริงบน Cloud Platform (Render.com) ผ่าน Docker Containerization"
    )
    c_obj = make_card("🎯 วัตถุประสงค์โครงงาน", objs_text, s, width=130 * mm, bg=LIGHT_BG, border=PRIMARY_COLOR)

    mtv_text = (
        "<b>สถาปัตยกรรม MTV (Model-Template-View):</b><br/>"
        "• <b>Model (Data & Logic):</b> myapp/models.py — ควบคุมตารางฐานข้อมูลและกฎความสัมพันธ์<br/>"
        "• <b>Template (Presentation):</b> myapp/templates/ — หน้าจอ UI พัฒนาด้วย Bootstrap 5<br/>"
        "• <b>View (Business Controller):</b> myapp/views/*.py — รับคำขอ ตรวจสิทธิ์ และประมวลผลตรรกะ<br/>"
        "• <b>URLs Router:</b> myproject/urls.py — กำหนดเส้นทางเข้าถึงแต่ละโมดูลอย่างเป็นสัดส่วน<br/>"
        "• <b>Service Layer:</b> myapp/services.py — เชื่อมต่อภายนอก (Google Maps, LINE, Nominatim)"
    )
    c_mtv = make_card("🏗️ สถาปัตยกรรม Django MTV", mtv_text, s, width=130 * mm, bg=LIGHT_BG, border=SECONDARY_COLOR)

    t_p3 = Table([[c_obj, c_mtv]], colWidths=[133 * mm, 133 * mm])
    t_p3.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(t_p3)
    story.append(PageBreak())

    # -------------------------------------------------------------
    # SLIDE 4: โครงสร้างฐานข้อมูล & ความสัมพันธ์ Model (Database Design)
    # -------------------------------------------------------------
    story.append(Paragraph("โครงสร้างฐานข้อมูล & ความสัมพันธ์ Model (Entity Relationships)", s["slide_title"]))
    story.append(Paragraph("ออกแบบความสัมพันธ์เชิงสัมพันธ์ครบทั้ง 3 รูปแบบตามทฤษฎีฐานข้อมูล", s["slide_subtitle"]))
    story.append(Spacer(1, 2 * mm))

    db_rel_rows = [
        ["รูปแบบความสัมพันธ์", "คู่ความสัมพันธ์ในระบบ", "Model ที่เกี่ยวข้อง", "ความสำคัญทางธุรกิจ"],
        ["One-to-One (1:1)", "User <--> Profile", "django.auth.User <-> Profile", "ขยายข้อมูลผู้ใช้: เก็บรูปโปรไฟล์, ปก, คะแนนสะสม, สถานะสมาชิก"],
        ["One-to-Many (1:N)", "Category --> MenuItem", "Category (1) -> MenuItem (N)", "หมวดหมู่อาหาร 1 หมวด บรรจุเมนูอาหารได้หลายเมนู"],
        ["One-to-Many (1:N)", "Order --> OrderItem", "Order (1) -> OrderItem (N)", "ออเดอร์ 1 ครั้ง สั่งอาหารได้หลายรายการ พร้อมนับจำนวนและราคา"],
        ["One-to-Many (1:N)", "User --> Order", "User (1) -> Order (N)", "ลูกค้า 1 บัญชี สามารถดูประวัติการสั่งอาหารย้อนหลังทั้งหมดได้"],
        ["Many-to-Many (N:M)", "MenuItem <--> Ingredient", "MenuItem <-> MenuIngredient <-> Ingredient", "สูตรอาหาร (Recipe): 1 เมนูใช้วัตถุดิบหลายตัว ใช้ตัดสต็อกอัตโนมัติ"],
        ["Many-to-Many (N:M)", "OrderItem <--> AddOn", "OrderItem <-> AddOn (ManyToManyField)", "รายการที่สั่ง 1 จาน สามารถเลือกเครื่องเคียงได้หลายรายการ"],
    ]
    t_dbr = Table([[Paragraph(c, s["th"]) for c in db_rel_rows[0]]] +
                  [[Paragraph(r[0], s["cell_bold"]), Paragraph(r[1], s["cell_center"]), Paragraph(r[2], s["cell"]), Paragraph(r[3], s["cell"])] for r in db_rel_rows[1:]],
                  colWidths=[38 * mm, 50 * mm, 75 * mm, 100 * mm])
    t_dbr.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_COLOR),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("GRID", (0, 0), (-1, -1), 0.3, BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_dbr)
    story.append(PageBreak())

    # -------------------------------------------------------------
    # SLIDE 5: บทบาทและสิทธิ์ผู้ใช้งาน (User Roles & Permissions)
    # -------------------------------------------------------------
    story.append(Paragraph("บทบาทและสิทธิ์ผู้ใช้งาน (User Roles & Permissions Matrix)", s["slide_title"]))
    story.append(Paragraph("การกำหนดสิทธิ์ 3 บทบาทจริง ป้องกันความปลอดภัยด้วย Decorator & Mixins", s["slide_subtitle"]))
    story.append(Spacer(1, 2 * mm))

    role_matrix = [
        ["โมดูล / ฟังก์ชันการทำงาน", "ลูกค้า (Customer)", "พนักงาน (Staff)", "ผู้ดูแลระบบ (Admin)"],
        ["ดูเมนูอาหาร, ค้นหา, กรองหมวดหมู่", "✅ เข้าชมได้", "✅ เข้าชมได้", "✅ เข้าชมได้"],
        ["สั่งอาหาร, เลือกเครื่องเคียง, แนบสลิป", "✅ สั่งได้", "✅ สั่งแทนลูกค้าได้", "✅ สั่งได้"],
        ["ดูประวัติออเดอร์ของตนเอง", "✅ ดูได้เฉพาะของตนเอง", "✅ ดูได้ทั้งหมด", "✅ ดูได้ทั้งหมด"],
        ["เพิ่ม / แก้ไข / ลบ เมนูอาหาร (CRUD)", "❌ ไม่มีสิทธิ์ (403)", "✅ จัดการได้", "✅ จัดการได้"],
        ["จัดการสต็อกวัตถุดิบ & ปรับปรุงคลัง", "❌ ไม่มีสิทธิ์ (403)", "✅ จัดการสต็อกได้", "✅ จัดการได้"],
        ["Kitchen Display & ปรับสถานะทำอาหาร", "❌ ไม่มีสิทธิ์ (403)", "✅ จัดการได้", "✅ จัดการได้"],
        ["Dashboard ยอดขาย & ส่งออก Excel/CSV", "❌ ไม่มีสิทธิ์ (403)", "✅ ดูสถิติ/Export ได้", "✅ ดูสถิติ/Export ได้"],
        ["เข้าใช้งาน Django Admin (/admin/)", "❌ ไม่มีสิทธิ์ (บล็อก)", "❌ ไม่มีสิทธิ์", "✅ สิทธิ์เต็ม (Superuser)"],
    ]
    t_rm = Table([[Paragraph(c, s["th"]) for c in role_matrix[0]]] +
                 [[Paragraph(r[0], s["cell_bold"]), Paragraph(r[1], s["cell_center"]), Paragraph(r[2], s["cell_center"]), Paragraph(r[3], s["cell_center"])] for r in role_matrix[1:]],
                 colWidths=[90 * mm, 55 * mm, 55 * mm, 60 * mm])
    t_rm.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_COLOR),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("GRID", (0, 0), (-1, -1), 0.3, BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]))
    story.append(t_rm)
    story.append(PageBreak())

    # -------------------------------------------------------------
    # SLIDE 6: ตรวจสอบความครบถ้วนตามเกณฑ์ 10 ข้อ (Core Requirements Checklist)
    # -------------------------------------------------------------
    story.append(Paragraph("ตรวจสอบเกณฑ์ขั้นต่ำ 10 ข้อ (Core Requirements Checklist)", s["slide_title"]))
    story.append(Paragraph("ระบบผ่านเกณฑ์ขั้นต่ำของโจทย์ครบถ้วน 100% ทุกข้อ", s["slide_subtitle"]))
    story.append(Spacer(1, 2 * mm))

    core_rows = [
        ["#", "เกณฑ์ที่กำหนดตามโจทย์", "ฟังก์ชันในระบบ 'อร่อยเกินเบอร์'", "สถานะ"],
        ["1", "ระบบสมัครสมาชิก เข้าสู่ระบบ และออกจากระบบ", "Register, Login, Logout, รองรับ Google OAuth 2.0 (django-allauth)", "✅ ผ่าน 100%"],
        ["2", "ผู้ใช้งานอย่างน้อย 2 บทบาท พร้อมกำหนดสิทธิ์จริง", "3 บทบาท: Customer, Staff, Admin ตรวจสอบด้วย @login_required, @user_passes_test", "✅ ผ่าน 100%"],
        ["3", "การเพิ่ม แสดง แก้ไข ลบข้อมูล (CRUD) ด้วย Model", "CRUD เมนูอาหาร, หมวดหมู่, ออเดอร์, วัตถุดิบ, คูปอง ผ่าน Django ModelForm", "✅ ผ่าน 100%"],
        ["4", "ระบบค้นหาข้อมูล (Search & Filter)", "ค้นหาชื่อเมนู, กรองตามหมวดหมู่, กรองช่วงราคา, ระดับความเผ็ด และค้นหาออเดอร์", "✅ ผ่าน 100%"],
        ["5", "ระบบอัปโหลดรูปภาพหรือไฟล์", "อัปโหลดรูปเมนูอาหาร, รูปโปรไฟล์ และสลิป พร้อมตัวตรวจสอบไฟล์ <= 10MB ด้วย Pillow", "✅ ผ่าน 100%"],
        ["6", "การแบ่งหน้ารายการข้อมูล (Pagination)", "ใช้ Django Paginator ในหน้ารายการอาหาร (menu_list) และประวัติออเดอร์", "✅ ผ่าน 100%"],
        ["7", "ความสัมพันธ์ระหว่าง Model อย่างน้อย 1 รูปแบบ", "มีครบทั้ง 3 แบบ: One-to-One, One-to-Many, และ Many-to-Many", "✅ ผ่าน 100%"],
        ["8", "การตรวจสอบความถูกต้องของข้อมูลในฟอร์ม", "Form Validation: ราคา > 0, เลขโต๊ะ 1-999, ชื่อไม่ซ้ำ, นามสกุลและขนาดไฟล์", "✅ ผ่าน 100%"],
        ["9", "UI มีรูปแบบสม่ำเสมอ อ่านง่าย ใช้งานได้จริง", "พัฒนาด้วย Bootstrap 5, Font Awesome, Responsive Design ทุกอุปกรณ์", "✅ ผ่าน 100%"],
        ["10", "นำระบบขึ้น Hosting/Cloud ใช้งานผ่านเน็ตได้", "Deploy บน Render.com ผ่าน Dockerfile พร้อมใช้งานที่ https://omg02.onrender.com", "✅ ผ่าน 100%"],
    ]
    t_cr = Table([[Paragraph(c, s["th"]) for c in core_rows[0]]] +
                 [[Paragraph(r[0], s["cell_center"]), Paragraph(r[1], s["cell_bold"]), Paragraph(r[2], s["cell"]), Paragraph(r[3], s["cell_center"])] for r in core_rows[1:]],
                 colWidths=[8 * mm, 80 * mm, 137 * mm, 35 * mm])
    t_cr.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_COLOR),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("GRID", (0, 0), (-1, -1), 0.3, BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 2.8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.8),
    ]))
    story.append(t_cr)
    story.append(PageBreak())

    # -------------------------------------------------------------
    # SLIDE 7: ระบบสั่งอาหาร ใบเสร็จ และเดลิเวอรี่ (Ordering & Delivery)
    # -------------------------------------------------------------
    story.append(Paragraph("ระบบสั่งอาหาร ใบเสร็จ และเดลิเวอรี่ (Ordering & Delivery Workflow)", s["slide_title"]))
    story.append(Paragraph("ขั้นตอนการไหลของข้อมูลตั้งแต่ลูกค้าสั่งอาหารจนถึงการส่งมอบ", s["slide_subtitle"]))
    story.append(Spacer(1, 3 * mm))

    c_ord = make_card(
        "🍽️ การสั่งอาหารหน้าร้าน (Dine-in)",
        "• <b>เปิดโต๊ะ & QR Code:</b> ลูกค้าเปิดสั่งตามเลขโต๊ะ หรือสแกน QR ประจำโต๊ะ<br/>"
        "• <b>ปรับแต่งรายการ:</b> เลือกระดับความเผ็ด (0-3) และเพิ่มเครื่องเคียง เช่น ไข่ดาว/กุนเชียง<br/>"
        "• <b>รหัสออเดอร์รายวัน:</b> สร้างรหัสสั้นแสดงผล เช่น <code>#001</code> รีเซ็ตใหม่ทุกวัน<br/>"
        "• <b>ใบเสร็จรับเงิน (Receipt):</b> แสดงยอดรวม ส่วนลดคูปอง และมีปุ่มพิมพ์ใบเสร็จทันที",
        s, width=130 * mm, bg=LIGHT_BG, border=PRIMARY_COLOR
    )

    c_del = make_card(
        "🛵 การจัดส่งเดลิเวอรี่ (Delivery & GPS)",
        "• <b>บันทึกที่อยู่จัดส่ง:</b> เก็บชื่อ เบอร์โทร และที่อยู่จัดส่งของผู้สั่ง<br/>"
        "• <b>คำนวณระยะทาง GPS:</b> ใช้สูตร Haversine คำนวณระยะทางจากพิกัดร้านจริง<br/>"
        "• <b>คำนวณค่าส่งอัตโนมัติ:</b> คิดอัตราค่าส่งตามกิโลเมตรจริงอย่างเป็นธรรม<br/>"
        "• <b>Rider Dashboard:</b> ไรเดอร์สามารถกดรับงาน เปลี่ยนสถานะ และโทรติดต่อลูกค้าได้",
        s, width=130 * mm, bg=LIGHT_BG, border=ACCENT_COLOR
    )

    t_p7 = Table([[c_ord, c_del]], colWidths=[133 * mm, 133 * mm])
    t_p7.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(t_p7)
    story.append(PageBreak())

    # -------------------------------------------------------------
    # SLIDE 8: ฟังก์ชันความสามารถพิเศษ (Bonus Features - 5 คะแนนเต็ม)
    # -------------------------------------------------------------
    story.append(Paragraph("ฟังก์ชันความสามารถพิเศษ (Bonus Features - สูงสุด 5 คะแนน)", s["slide_title"]))
    story.append(Paragraph("ฟังก์ชันขั้นสูงที่พัฒนาเพิ่มเติมเกินขอบเขตขั้นต่ำ เพื่อเพิ่มคุณภาพของระบบ", s["slide_subtitle"]))
    story.append(Spacer(1, 2 * mm))

    bonus_grid = [
        ("1. RESTful API (DRF)", "เปิด Endpoint <code>/api/menus/</code>, <code>/api/orders/</code>, <code>/api/categories/</code> รองรับ CRUD และเชื่อมต่อกับระบบภายนอก"),
        ("2. External API Integration", "• Google Maps Embed (แผนที่ร้าน)<br/>• LINE Notify (แจ้งเตือนออเดอร์เข้ากลุ่มครัว)<br/>• OpenStreetMap (พิกัด GPS ที่อยู่)"),
        ("3. Dashboard & Chart.js", "หน้าแดชบอร์ดสรุปยอดขาย สถิติรายวัน/สัปดาห์/เดือน พร้อมกราฟแท่งแนวโน้มยอดขาย 7 วันย้อนหลัง และจัดอันดับเมนูขายดี"),
        ("4. Automated Testing (245 Tests)", "ชุดทดสอบอัตโนมัติครอบคลุมทั้งระบบจำนวน <b>245 ข้อ</b> ผ่าน 100% ตรวจสอบ Model, View, Security, API และ Logic"),
        ("5. Data Export (Excel & CSV)", "ส่งออกรายงานยอดขายและประวัติออเดอร์เป็นไฟล์ Excel (.xlsx) สวยงามด้วย openpyxl และไฟล์ CSV สำหรับนำไปวิเคราะห์ต่อ"),
        ("6. Docker & Containerization", "Dockerfile แบบ Multi-stage Build ปลอดภัย น้ำหนักเบา พร้อมรัน Production บน Render.com อย่างมีเสถียรภาพ"),
    ]

    b_cards = []
    for title, desc in bonus_grid:
        b_cards.append(make_card(title, desc, s, width=86 * mm, bg=LIGHT_BG, border=SECONDARY_COLOR))

    t_b1 = Table([[b_cards[0], b_cards[1], b_cards[2]]], colWidths=[88 * mm, 88 * mm, 88 * mm])
    t_b2 = Table([[b_cards[3], b_cards[4], b_cards[5]]], colWidths=[88 * mm, 88 * mm, 88 * mm])
    for tb in (t_b1, t_b2):
        tb.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(t_b1)
    story.append(Spacer(1, 3 * mm))
    story.append(t_b2)
    story.append(PageBreak())

    # -------------------------------------------------------------
    # SLIDE 9: การประกันคุณภาพและความปลอดภัย (Quality & Security)
    # -------------------------------------------------------------
    story.append(Paragraph("การประกันคุณภาพและความปลอดภัย (Quality Assurance & Security)", s["slide_title"]))
    story.append(Paragraph("ความมั่นคงปลอดภัยตามมาตรฐาน และผลการทดสอบซอฟต์แวร์ 245 ข้อ", s["slide_subtitle"]))
    story.append(Spacer(1, 3 * mm))

    c_sec = make_card(
        "🛡️ มาตรการความปลอดภัยของระบบ (Security)",
        "• <b>CSRF Protection:</b> ป้องกันการปลอมแปลงคำขอข้ามไซต์ทุกฟอร์ม<br/>"
        "• <b>Rate Limiting & Throttle:</b> ป้องกันการยิงสแปมออเดอร์และการ Brute-Force รหัสผ่าน<br/>"
        "• <b>SQL Injection Safe:</b> ใช้ Django ORM แบบ Parameterized Queries 100%<br/>"
        "• <b>Secure Headers:</b> รองรับ HSTS, HTTPS Redirect, และ SameSite Cookies<br/>"
        "• <b>File Upload Security:</b> ตรวจสอบ MIME type และขนาดไฟล์รูปภาพไม่เกิน 10MB",
        s, width=130 * mm, bg=LIGHT_BG, border=PRIMARY_COLOR
    )

    c_test = make_card(
        "🧪 ผลการทดสอบอัตโนมัติ (Automated Testing)",
        "• <b>คำสั่งรัน:</b> <code>python manage.py test</code><br/>"
        "• <b>จำนวนเคส:</b> <b>245 Test Cases</b><br/>"
        "• <b>ผลลัพธ์:</b> <b>OK (100% Passed)</b> โดยใช้เวลารัน 120 วินาที<br/>"
        "• <b>ขอบเขตที่ตรวจ:</b> Model Constraints, View Permission, Form Validation, API Endpoints, Recipe Stock Deduction, Haversine Distance Calculation",
        s, width=130 * mm, bg=LIGHT_BG, border=ACCENT_COLOR
    )

    t_p9 = Table([[c_sec, c_test]], colWidths=[133 * mm, 133 * mm])
    t_p9.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(t_p9)
    story.append(PageBreak())

    # -------------------------------------------------------------
    # SLIDE 10: การติดตั้งบน Cloud Hosting (Production Deployment)
    # -------------------------------------------------------------
    story.append(Paragraph("การติดตั้งบน Cloud Hosting (Production Deployment on Render)", s["slide_title"]))
    story.append(Paragraph("ขั้นตอนการนำระบบขึ้นคลาวด์สาธารณะผ่าน Docker Container", s["slide_subtitle"]))
    story.append(Spacer(1, 3 * mm))

    c_cloud1 = make_card(
        "🐳 โครงสร้าง Dockerfile สำหรับ Production",
        "• <b>Multi-Stage Build:</b> ใช้ Python 3.14-slim แยก Stage บิลด์เพื่อลดขนาด Image<br/>"
        "• <b>Non-Root User:</b> รันแอปพลิเคชันภายใต้ผู้ใช้ <code>appuser</code> เพื่อความปลอดภัย<br/>"
        "• <b>Gunicorn WSGI:</b> รันเว็บเซิร์ฟเวอร์แบบ Production รองรับการประมวลผลพร้อมกัน<br/>"
        "• <b>WhiteNoise:</b> บีบอัดและเสิร์ฟไฟล์ Static Files (CSS/JS) โดยตรงอย่างรวดเร็ว",
        s, width=130 * mm, bg=LIGHT_BG, border=PRIMARY_COLOR
    )

    c_cloud2 = make_card(
        "⚙️ การจัดการข้อมูลบน Cloud (Auto-Seed & Migration)",
        "• <b>Auto Migrate:</b> รัน <code>migrate --noinput</code> อัตโนมัติทุกครั้งที่บูตคอนเทนเนอร์<br/>"
        "• <b>Auto Seed Data:</b> เติมข้อมูลเมนูอาหารทั้ง 16 เมนู พร้อมรูปภาพจริงลงฐานข้อมูล<br/>"
        "• <b>Init Test Users:</b> สร้างบัญชี Admin, Staff, Customer พร้อมรหัสผ่านให้อัตโนมัติ<br/>"
        "• <b>Healthcheck:</b> มีระบบตรวจสอบสถานะเซิร์ฟเวอร์ผ่าน Endpoint <code>/healthz</code>",
        s, width=130 * mm, bg=LIGHT_BG, border=ACCENT_COLOR
    )

    t_p10 = Table([[c_cloud1, c_cloud2]], colWidths=[133 * mm, 133 * mm])
    t_p10.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(t_p10)
    story.append(PageBreak())

    # -------------------------------------------------------------
    # SLIDE 11: ลำดับขั้นตอนการสาธิตระบบจริง (Live Demonstration Flow)
    # -------------------------------------------------------------
    story.append(Paragraph("ลำดับขั้นตอนการสาธิตระบบจริง (Live Demonstration Flow)", s["slide_title"]))
    story.append(Paragraph("แนวทางการสาธิตฟังก์ชันการทำงาน 8 ขั้นตอนตามเกณฑ์การประเมินของอาจารย์", s["slide_subtitle"]))
    story.append(Spacer(1, 2 * mm))

    demo_steps = [
        ["ขั้นตอน", "กิจกรรมที่สาธิต", "สิ่งที่แสดงบนหน้าจอ", "บทบาทที่ใช้"],
        ["1. สมัครสมาชิก", "เปิดหน้า /register/ กรอกข้อมูลและสมัคร", "สมัครสำเร็จ และล็อกอินเข้าสู่ระบบทันที", "ผู้ใช้ใหม่"],
        ["2. เข้าสู่ระบบ", "เข้าหน้า /login/ ด้วยบัญชีลูกค้า", "แสดงชื่อผู้ใช้ และคะแนนสะสมบนแถบ Navbar", "Customer"],
        ["3. กำหนดสิทธิ์", "เปรียบเทียบหน้าจอ Customer vs Staff", "Staff เห็นเมนูคลังสต็อก, ออเดอร์, แดชบอร์ด (User ทั่วไปไม่เห็น)", "Staff / User"],
        ["4. CRUD ข้อมูล", "เพิ่มเมนูใหม่, แก้ไขราคา, ปรับสถานะพร้อมขาย", "ข้อมูลเปลี่ยนแปลงในฐานข้อมูลและหน้าเว็บทันที", "Staff / Admin"],
        ["5. ค้นหา & กรอง", "พิมพ์ค้นหา 'กะเพรา' และคลิกเลือกหมวด 'ผัด'", "รายการอาหารกรองตามคำค้นและหมวดหมู่อย่างถูกต้อง", "ทุกคน"],
        ["6. อัปโหลดไฟล์", "แก้ไขเมนูและอัปโหลดรูปภาพอาหารใหม่", "รูปภาพแสดงผลบนการ์ดเมนูและหน้ารายละเอียด", "Staff"],
        ["7. การแบ่งหน้า", "เข้าหน้ารายการเมนูอาหาร กดเปลี่ยนหน้า 1, 2", "Pagination แสดงจำนวนรายการต่อหน้าและปุ่มเลื่อนหน้า", "ทุกคน"],
        ["8. ใช้งาน Hosting", "เปิดเว็บจริง https://omg02.onrender.com", "ระบบตอบสนองรวดเร็ว ใช้งานได้จริงผ่านเครือข่ายอินเทอร์เน็ต", "ทุกคน"],
    ]
    t_ds = Table([[Paragraph(c, s["th"]) for c in demo_steps[0]]] +
                 [[Paragraph(r[0], s["cell_center"]), Paragraph(r[1], s["cell_bold"]), Paragraph(r[2], s["cell"]), Paragraph(r[3], s["cell_center"])] for r in demo_steps[1:]],
                 colWidths=[28 * mm, 75 * mm, 125 * mm, 34 * mm])
    t_ds.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_COLOR),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("GRID", (0, 0), (-1, -1), 0.3, BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t_ds)
    story.append(PageBreak())

    # -------------------------------------------------------------
    # SLIDE 12: ข้อมูลสำหรับทดสอบและส่งงาน (Live Access & Test Accounts)
    # -------------------------------------------------------------
    story.append(Paragraph("ข้อมูลสำหรับทดสอบและส่งงาน (Live Access & Test Accounts)", s["slide_title"]))
    story.append(Paragraph("ลิงก์ URL ระบบจริง, QR Code, และตารางบัญชีผู้ใช้สำหรับทดสอบ", s["slide_subtitle"]))
    story.append(Spacer(1, 3 * mm))

    qr_render = os.path.join(BASE_DIR, "docs", "qr_render.png")
    qr_github = os.path.join(BASE_DIR, "docs", "qr_github.png")

    img_render = Image(qr_render, width=38 * mm, height=38 * mm) if os.path.exists(qr_render) else Paragraph("[QR Code]", s["cell"])
    img_github = Image(qr_github, width=38 * mm, height=38 * mm) if os.path.exists(qr_github) else Paragraph("[QR Code]", s["cell"])

    qr_row = [
        [img_render, Paragraph("<b>🌐 Cloud Hosting URL:</b><br/><font color='#b3261e'><b>https://omg02.onrender.com</b></font><br/>(เข้าใช้งานระบบจริงผ่านอินเทอร์เน็ต)", s["cell"]),
         img_github, Paragraph("<b>💻 GitHub Repository:</b><br/><font color='#b3261e'><b>https://github.com/omgx624-gif/OMg02</b></font><br/>(ซอร์สโค้ดโครงงานฉบับสมบูรณ์)", s["cell"])]
    ]
    t_qrs = Table(qr_row, colWidths=[42 * mm, 90 * mm, 42 * mm, 90 * mm])
    t_qrs.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
        ("BOX", (0, 0), (-1, -1), 1, BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_qrs)
    story.append(Spacer(1, 4 * mm))

    acc_test_rows = [
        ["บทบาท (Role)", "Username", "Password", "สิทธิ์และสิ่งที่ทดสอบได้"],
        ["Admin (ผู้ดูแลระบบ)", "admin", "Admin1234!", "เข้า Django Admin (/admin/), จัดการฐานข้อมูลทั้งหมด, ควบคุมสิทธิ์"],
        ["Staff (พนักงาน)", "staff หรือ Jj12", "Staff1234!", "ดูแดชบอร์ดร้าน, จัดการออเดอร์, คลังสต็อก, จัดการเดลิเวอรี่"],
        ["Customer (ลูกค้า)", "customer หรือ Ff12", "User1234!", "สั่งอาหารหน้าร้าน, จองโต๊ะ, สั่งเดลิเวอรี่, สะสมแต้ม, เขียนรีวิว"],
    ]
    t_atr = Table([[Paragraph(c, s["th"]) for c in acc_test_rows[0]]] +
                  [[Paragraph(r[0], s["cell_bold"]), Paragraph(r[1], s["cell_center"]), Paragraph(r[2], s["cell_center"]), Paragraph(r[3], s["cell"])] for r in acc_test_rows[1:]],
                  colWidths=[45 * mm, 40 * mm, 40 * mm, 137 * mm])
    t_atr.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_COLOR),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("GRID", (0, 0), (-1, -1), 0.3, BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]))
    story.append(t_atr)
    story.append(PageBreak())

    # -------------------------------------------------------------
    # SLIDE 13: รายการเอกสารและสิ่งที่ต้องส่ง (Project Deliverables)
    # -------------------------------------------------------------
    story.append(Paragraph("รายการเอกสารและสิ่งที่ต้องส่ง (Project Deliverables Checklist)", s["slide_title"]))
    story.append(Paragraph("ความพร้อมของเอกสาร ซอร์สโค้ด และระบบตามข้อกำหนดของโครงงาน", s["slide_subtitle"]))
    story.append(Spacer(1, 3 * mm))

    deliv_rows = [
        ["สิ่งที่ต้องส่งตามเกณฑ์", "รายละเอียดและไฟล์ที่จัดเตรียม", "สถานะ"],
        ["1. URL ระบบบน Hosting", "ระบบออนไลน์บน Render: https://omg02.onrender.com พร้อมใช้งานจริง", "✅ เรียบร้อย"],
        ["2. บัญชีผู้ใช้ทดสอบระบบ", "ตาราง Username / Password สำหรับ Admin, Staff, Customer ครบ 3 บทบาท", "✅ เรียบร้อย"],
        ["3. GitHub Repository", "ซอร์สโค้ดฉบับสมบูรณ์ที่ https://github.com/omgx624-gif/OMg02", "✅ เรียบร้อย"],
        ["4. เล่มรายงานโครงงาน PDF", "รายงานโครงงานฉบับสมบูรณ์ 5 บท + ภาคผนวก ในโฟลเดอร์ docs/ (PDF 1 เล่ม)", "✅ เรียบร้อย"],
        ["5. ไฟล์นำเสนอ (Slide PDF)", "สไลด์นำเสนอฉบับทางการ 14 หน้า แนวนอน 16:9 ในโฟลเดอร์ docs/ (PDF 1 อัน)", "✅ เรียบร้อย"],
        ["6. การสาธิตระบบจริง", "เตรียมลำดับการสาธิต 8 ขั้นตอน พร้อมบัญชีทดสอบที่กำหนดค่าไว้ล่วงหน้า", "✅ พร้อมนำเสนอ"],
    ]
    t_del = Table([[Paragraph(c, s["th"]) for c in deliv_rows[0]]] +
                  [[Paragraph(r[0], s["cell_bold"]), Paragraph(r[1], s["cell"]), Paragraph(r[2], s["cell_center"])] for r in deliv_rows[1:]],
                  colWidths=[65 * mm, 155 * mm, 42 * mm])
    t_del.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PRIMARY_COLOR),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
        ("GRID", (0, 0), (-1, -1), 0.3, BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_del)
    story.append(PageBreak())

    # -------------------------------------------------------------
    # SLIDE 14: สรุปผลและช่วงถาม-ตอบ (Conclusion & Q&A)
    # -------------------------------------------------------------
    story.append(Spacer(1, 20 * mm))
    story.append(Paragraph("ขอขอบพระคุณคณะกรรมการและอาจารย์ผู้สอน", s["cover_sub"]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("จบการนำเสนอโครงงาน<br/>'อร่อยเกินเบอร์' (Aroy Gern Ber)", s["cover_main"]))
    story.append(Spacer(1, 5 * mm))
    story.append(Paragraph("ยินดีรับฟังข้อเสนอแนะและตอบคำถาม (Questions & Answers)", s["cover_sub"]))
    story.append(Spacer(1, 8 * mm))
    story.append(HRFlowable(width="40%", thickness=2, color=PRIMARY_COLOR, spaceAfter=8 * mm))

    concl_box = [
        [Paragraph("<b>จุดเด่นของระบบ:</b> ฟังก์ชันครบตามเกณฑ์ 10 ข้อ · คะแนน Bonus ครบทุกหมวด · Automated Tests 245 ข้อผ่าน 100% · รันบน Cloud จริง", s["cell_center"])],
        [Paragraph("<b>URL:</b> https://omg02.onrender.com | <b>GitHub:</b> https://github.com/omgx624-gif/OMg02", s["cell_center"])],
    ]
    t_cb = Table(concl_box, colWidths=[240 * mm])
    t_cb.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
        ("BOX", (0, 0), (-1, -1), 1, BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t_cb)

    return story


def main():
    styles = get_slide_styles()
    doc = SimpleDocTemplate(
        OUTPUT_PDF,
        pagesize=landscape(A4),
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title="สไลด์นำเสนอโครงงานระบบจัดการร้านอาหาร 'อร่อยเกินเบอร์'",
        author="omgx624-gif",
    )
    story = build_slides(styles)
    doc.build(story, onFirstPage=slide_decorator, onLaterPages=slide_decorator)
    print("SUCCESS: Presentation PDF generated at", OUTPUT_PDF)
    print("FILE SIZE:", os.path.getsize(OUTPUT_PDF), "bytes")


if __name__ == "__main__":
    main()

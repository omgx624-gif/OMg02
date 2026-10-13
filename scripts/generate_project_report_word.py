# -*- coding: utf-8 -*-
"""Generate comprehensive Thai Project Report in Microsoft Word format (.docx) using python-docx."""

import os
from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DOCX = os.path.join(BASE_DIR, "docs", "รายงานโครงงาน_ระบบจัดการร้านอาหาร_อร่อยเกินเบอร์.docx")

FONT_NAME = "TH Sarabun New"
FONT_FALLBACK = "Tahoma"

COLOR_PRIMARY = RGBColor(179, 38, 30)       # #b3261e
COLOR_SECONDARY = RGBColor(107, 86, 74)    # #6b564a
COLOR_ACCENT = RGBColor(27, 94, 32)        # #1b5e20
COLOR_DARK = RGBColor(33, 33, 33)          # #212121
COLOR_MUTED = RGBColor(117, 117, 117)


def set_cell_background(cell, fill_hex):
    """Set background color of a table cell."""
    tcPr = cell._element.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), fill_hex)
    tcPr.append(shd)


def set_table_borders(table, color="D8CBB8", sz="4", val="single"):
    """Set elegant borders for Word table."""
    tblPr = table._element.xpath('w:tblPr')
    if tblPr:
        borders = OxmlElement('w:tblBorders')
        for b_name in ['top', 'left', 'bottom', 'right', 'insideH']:
            border = OxmlElement(f'w:{b_name}')
            border.set(qn('w:val'), val)
            border.set(qn('w:sz'), sz)
            border.set(qn('w:space'), '0')
            border.set(qn('w:color'), color)
            borders.append(border)
        insideV = OxmlElement('w:insideV')
        insideV.set(qn('w:val'), 'none')
        borders.append(insideV)
        tblPr[0].append(borders)


def format_run(run, font_name=FONT_NAME, size_pt=16, bold=False, italic=False, color=COLOR_DARK):
    """Format text run with Thai complex script support."""
    run.font.name = font_name
    run.font.size = Pt(size_pt)
    run.bold = bold
    run.italic = italic
    if color:
        run.font.color.rgb = color
    rPr = run._r.get_or_add_rPr()
    rFonts = OxmlElement('w:rFonts')
    rFonts.set(qn('w:ascii'), font_name)
    rFonts.set(qn('w:hAnsi'), font_name)
    rFonts.set(qn('w:cs'), font_name)
    rPr.append(rFonts)


def add_paragraph_styled(doc, text="", align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_before=0, space_after=6, line_spacing=1.15):
    """Add a paragraph with standard Thai document spacing."""
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = line_spacing
    if text:
        run = p.add_run(text)
        format_run(run, size_pt=16)
    return p


def add_heading_1(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    format_run(run, size_pt=20, bold=True, color=COLOR_PRIMARY)
    return p


def add_heading_2(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    format_run(run, size_pt=17, bold=True, color=COLOR_DARK)
    return p


def add_heading_3(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    format_run(run, size_pt=16, bold=True, color=COLOR_SECONDARY)
    return p


def add_bullet_item(doc, title, desc):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.25)
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.15
    run_t = p.add_run(f"• {title}: ")
    format_run(run_t, size_pt=16, bold=True, color=COLOR_DARK)
    run_d = p.add_run(desc)
    format_run(run_d, size_pt=16, bold=False, color=COLOR_DARK)
    return p


def create_styled_table(doc, headers, data, col_widths=None, header_bg="B3261E"):
    """Create a beautiful Word table with styled headers and alternating rows."""
    table = doc.add_table(rows=len(data) + 1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(table)

    # Header row
    hdr_cells = table.rows[0].cells
    for i, title in enumerate(headers):
        hdr_cells[i].text = ""
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run(title)
        format_run(run, size_pt=15, bold=True, color=RGBColor(255, 255, 255))
        set_cell_background(hdr_cells[i], header_bg)
        hdr_cells[i].vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    # Data rows
    for r_idx, row_data in enumerate(data):
        row_cells = table.rows[r_idx + 1].cells
        bg_color = "FAF6EF" if r_idx % 2 == 1 else "FFFFFF"
        for c_idx, val in enumerate(row_data):
            row_cells[c_idx].text = ""
            p = row_cells[c_idx].paragraphs[0]
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.line_spacing = 1.15
            run = p.add_run(val)
            format_run(run, size_pt=14, bold=(c_idx == 0))
            set_cell_background(row_cells[c_idx], bg_color)
            row_cells[c_idx].vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    # Column widths
    if col_widths:
        for row in table.rows:
            for idx, width in enumerate(col_widths):
                row.cells[idx].width = Inches(width)

    p_spacer = doc.add_paragraph()
    p_spacer.paragraph_format.space_before = Pt(4)
    p_spacer.paragraph_format.space_after = Pt(6)
    return table


def build_word_document():
    doc = Document()

    # ตั้งค่าขอบกระดาษมาตรฐาน A4
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.25)
        section.right_margin = Inches(1.0)

    # =========================================================================
    # หน้าปก (COVER PAGE)
    # =========================================================================
    p_top = add_paragraph_styled(doc, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=36, space_after=12)
    run_t1 = p_top.add_run("รายงานโครงงานพัฒนาระบบเว็บแอปพลิเคชัน\n")
    format_run(run_t1, size_pt=20, bold=True, color=COLOR_SECONDARY)
    run_t2 = p_top.add_run("ระบบจัดการร้านอาหารและสั่งอาหารออนไลน์ 'อร่อยเกินเบอร์'\n")
    format_run(run_t2, size_pt=24, bold=True, color=COLOR_PRIMARY)
    run_t3 = p_top.add_run("(Aroy Gern Ber Restaurant Management & Online Ordering System)")
    format_run(run_t3, size_pt=16, italic=True, color=COLOR_SECONDARY)

    p_mid = add_paragraph_styled(doc, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=24, space_after=18)
    run_m1 = p_mid.add_run("รายวิชา: การพัฒนาเว็บแอปพลิเคชันด้วย Django Framework\n")
    format_run(run_m1, size_pt=16, bold=True)
    run_m2 = p_mid.add_run("แพลตฟอร์ม: Python 3.14 · Django 6.0 · SQLite/PostgreSQL · Docker · Bootstrap 5")
    format_run(run_m2, size_pt=15, color=COLOR_MUTED)

    # กล่องข้อมูลสำหรับนักศึกษากรอก
    p_box = add_paragraph_styled(doc, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=20, space_after=20)
    run_b = p_box.add_run(
        "----------------------------------------------------------------------------------------------------\n"
        "ผู้จัดทำโครงงาน: [ระบุชื่อ-นามสกุล นักศึกษา]\n"
        "รหัสนักศึกษา: [ระบุรหัสนักศึกษา]\n"
        "สาขาวิชา: [ระบุสาขาวิชา / ภาควิชา / คณะ]\n"
        "อาจารย์ผู้สอน / อาจารย์ที่ปรึกษา: [ระบุชื่ออาจารย์]\n"
        "ภาคการศึกษา: ภาคเรียนที่ 1 ปีการศึกษา 2569\n"
        "----------------------------------------------------------------------------------------------------"
    )
    format_run(run_b, size_pt=15, color=COLOR_DARK)

    # ตารางสรุปลิงก์และบัญชีทดสอบบนหน้าปก
    p_sum = add_paragraph_styled(doc, "ข้อมูลสำหรับการทดสอบและตรวจประเมินระบบ:", WD_ALIGN_PARAGRAPH.LEFT, space_before=10, space_after=4)
    format_run(p_sum.runs[0], size_pt=15, bold=True, color=COLOR_PRIMARY)

    meta_table_data = [
        ["URL ระบบจริง (Cloud Hosting)", "https://omg02.onrender.com (เปิดใช้งานผ่านอินเทอร์เน็ต)"],
        ["GitHub Repository", "https://github.com/omgx624-gif/OMg02"],
        ["บัญชีผู้ดูแลระบบ (Admin)", "Username: admin | Password: Admin1234! (สิทธิ์จัดการทั้งระบบ)"],
        ["บัญชีพนักงาน (Staff)", "Username: staff (หรือ Jj12) | Password: Staff1234! (คลังสต็อก/ออเดอร์)"],
        ["บัญชีลูกค้า (Customer)", "Username: customer (หรือ Ff12) | Password: User1234! (สั่งอาหาร/จองโต๊ะ)"],
    ]
    create_styled_table(doc, ["หัวข้อ", "รายละเอียดสำหรับเข้าตรวจ"], meta_table_data, col_widths=[2.4, 4.35])

    doc.add_page_break()

    # =========================================================================
    # บทคัดย่อ และ สารบัญ
    # =========================================================================
    add_heading_1(doc, "บทคัดย่อ (Executive Summary)")
    p_abs = add_paragraph_styled(doc)
    p_abs.add_run(
        "โครงงานนี้เป็นการพัฒนาระบบเว็บแอปพลิเคชันสำหรับบริหารจัดการร้านอาหารและสั่งอาหารออนไลน์ 'อร่อยเกินเบอร์' "
        "โดยประยุกต์ใช้ Django Framework ร่วมกับฐานข้อมูลเชิงสัมพันธ์ เพื่อแก้ไขปัญหาความผิดพลาดในการจดออเดอร์ "
        "ความล่าช้าในการส่งรายการอาหารเข้าครัว และการขาดระบบติดตามสต็อกวัตถุดิบและสถิติยอดขายที่แม่นยำ "
        "ระบบประกอบด้วยความสามารถหลักครบถ้วนตามเกณฑ์กำหนด ได้แก่ ระบบยืนยันตัวตนพร้อมสิทธิ์ 3 บทบาทจริง "
        "(Customer, Staff, Admin) การจัดการข้อมูลแบบ CRUD ผ่าน Django ModelForm ระบบค้นหาและตัวกรองขั้นสูง "
        "ระบบอัปโหลดไฟล์รูปภาพพร้อมการตรวจสอบขนาดและมิติของไฟล์ การแบ่งหน้าข้อมูล (Pagination) "
        "ความสัมพันธ์ระหว่างตารางครบทั้ง One-to-One, One-to-Many และ Many-to-Many รวมถึงการนำระบบขึ้นสู่ Cloud Hosting "
        "บน Render.com ผ่าน Docker Containerization"
    )
    format_run(p_abs.runs[0], size_pt=16)

    p_abs2 = add_paragraph_styled(doc)
    p_abs2.add_run(
        "นอกจากนี้ ระบบยังได้พัฒนาฟังก์ชันโบนัสขั้นสูงเพื่อเพิ่มมูลค่า ได้แก่ RESTful API ด้วย Django REST Framework, "
        "การเชื่อมต่อ External API (Google Maps Embed, LINE Notify และ OpenStreetMap Nominatim สำหรับคำนวณระยะทางจัดส่ง), "
        "แดชบอร์ดสรุปยอดขายด้วยกราฟ Chart.js, การส่งออกรายงานเป็นไฟล์ Excel (.xlsx) และ CSV, ระบบความปลอดภัยขั้นสูง "
        "ป้องกัน Brute-Force Rate Limiting และชุดทดสอบอัตโนมัติ (Automated Unit & Integration Testing) จำนวนมากถึง 245 ข้อ "
        "ซึ่งผ่านการทดสอบสมบูรณ์ 100%"
    )
    format_run(p_abs2.runs[0], size_pt=16)

    add_heading_1(doc, "สารบัญเนื้อหา (Table of Contents)")
    toc_data = [
        ["บทที่ 1 บทนำ", "1.1 ความเป็นมา · 1.2 วัตถุประสงค์ · 1.3 ขอบเขตระบบ · 1.4 ประโยชน์ที่ได้รับ"],
        ["บทที่ 2 การวิเคราะห์และออกแบบระบบ", "2.1 สถาปัตยกรรม MTV · 2.2 Use Case · 2.3 ออกแบบฐานข้อมูล (ER) · 2.4 Data Dictionary"],
        ["บทที่ 3 การพัฒนาระบบ", "3.1 เทคโนโลยีที่ใช้ · 3.2 โครงสร้างโปรเจกต์ · 3.3 ตรวจสอบเกณฑ์ 10 ข้อ · 3.4 ฟังก์ชัน Bonus"],
        ["บทที่ 4 ผลการพัฒนาและภาพรวมการทำงาน", "4.1 หน้าร้านและเมนู · 4.2 ระบบออเดอร์/ครัว · 4.3 ระบบเดลิเวอรี่ · 4.4 แดชบอร์ดและสต็อก"],
        ["บทที่ 5 การทดสอบและสรุปผล", "5.1 ผลการทดสอบ 245 Tests · 5.2 ทดสอบบทบาทสิทธิ์ · 5.3 สรุปผล · 5.4 ข้อเสนอแนะ"],
        ["ภาคผนวก", "ภาคผนวก ก: URL & QR Code · ภาคผนวก ข: GitHub Repo · ภาคผนวก ค: คู่มือใช้งานย่อ"],
    ]
    create_styled_table(doc, ["บทที่ / หัวข้อ", "รายละเอียดเนื้อหาหลัก"], toc_data, col_widths=[2.2, 4.55])

    doc.add_page_break()

    # =========================================================================
    # บทที่ 1 บทนำ
    # =========================================================================
    add_heading_1(doc, "บทที่ 1: บทนำ (Introduction)")

    add_heading_2(doc, "1.1 ความเป็นมาและความสำคัญ")
    p_intro = add_paragraph_styled(doc)
    p_intro.add_run(
        "ธุรกิจร้านอาหารในปัจจุบันมีการแข่งขันสูงและความต้องการของผู้บริโภคเปลี่ยนแปลงไปอย่างรวดเร็ว "
        "การบริหารจัดการร้านอาหารแบบดั้งเดิมที่อาศัยการจดออเดอร์ด้วยกระดาษ มักประสบปัญหาข้อผิดพลาดในการรับรายการอาหาร "
        "การส่งออเดอร์เข้าครัวล่าช้า ไม่สามารถคำนวณยอดขายได้อย่างเรียลไทม์ และขาดระบบการจัดการสต็อกวัตถุดิบที่มีประสิทธิภาพ "
        "คณะผู้จัดทำจึงได้พัฒนาระบบเว็บแอปพลิเคชัน 'อร่อยเกินเบอร์' ขึ้นด้วย Django Framework เพื่อเป็นศูนย์กลางการบริหารงานร้านอาหาร "
        "ครอบคลุมทั้งการสั่งอาหารหน้าร้าน การจัดส่งเดลิเวอรี่ การจัดการสต็อกวัตถุดิบ การสะสมแต้มสมาชิก และการวิเคราะห์ข้อมูลยอดขาย"
    )
    format_run(p_intro.runs[0], size_pt=16)

    add_heading_2(doc, "1.2 วัตถุประสงค์ของโครงงาน")
    add_bullet_item(doc, "1", "เพื่อพัฒนาระบบเว็บแอปพลิเคชันสำหรับจัดการร้านอาหารด้วยภาษา Python และ Django Framework ตามมาตรฐานวิศวกรรมซอฟต์แวร์")
    add_bullet_item(doc, "2", "เพื่อพัฒนาระบบสั่งอาหารที่รองรับทั้งการรับประทานที่ร้าน (Dine-in) ผ่าน QR ประจำโต๊ะ และการสั่งแบบส่งถึงบ้าน (Delivery)")
    add_bullet_item(doc, "3", "เพื่อพัฒนาระบบควบคุมสิทธิ์การเข้าถึงของผู้ใช้งานอย่างน้อย 2 บทบาท (ลูกค้า พนักงาน และผู้ดูแลระบบ)")
    add_bullet_item(doc, "4", "เพื่อเพิ่มประสิทธิภาพการจัดการร้านด้วยระบบตัดสต็อกวัตถุดิบอัตโนมัติ แดชบอร์ดสรุปยอดขาย และการแจ้งเตือนผ่าน LINE Notify")
    add_bullet_item(doc, "5", "เพื่อนำระบบขึ้นสู่ระบบคลาวด์สาธารณะ (Render.com) ให้สามารถเข้าใช้งานผ่านเครือข่ายอินเทอร์เน็ตได้จริง")

    add_heading_2(doc, "1.3 ขอบเขตของระบบ (System Scope)")
    add_heading_3(doc, "1.3.1 ขอบเขตด้านผู้ใช้งาน (User Roles)")
    add_bullet_item(doc, "ลูกค้าทั่วไป (Customer)", "สมัครสมาชิก, เข้าสู่ระบบด้วย Username/Password หรือ Google Account, ดูเมนูอาหาร, ค้นหาและกรองเมนู, สั่งอาหาร, เลือกเครื่องเคียง/ระดับความเผ็ด, แนบสลิปชำระเงิน, จองโต๊ะ, สะสมแต้มแลกคูปอง, และเขียนรีวิว")
    add_bullet_item(doc, "พนักงานร้าน (Staff)", "จัดการออเดอร์ (เปลี่ยนสถานะ รอทำ/กำลังทำ/เสร็จสิ้น), ดูหน้าจอในครัว (Kitchen Display), จัดการสต็อกวัตถุดิบ, ตรวจสอบและอัปเดตงานเดลิเวอรี่, ดูรายงานสรุปยอดขายประจำวัน")
    add_bullet_item(doc, "ผู้ดูแลระบบ (Admin)", "เข้าถึง Django Admin จัดการฐานข้อมูลทั้งหมด, กำหนดกลุ่มสิทธิ์ผู้ใช้งาน, กำหนดค่าพิกัดร้านและค่าจัดส่ง, สร้างคูปองส่วนลด, ส่งออกรายงานยอดขายเป็น Excel/CSV")

    add_heading_3(doc, "1.3.2 ขอบเขตด้านฟังก์ชันการทำงาน (Functional Modules)")
    add_bullet_item(doc, "โมดูลเมนูและหมวดหมู่", "เพิ่ม แสดง แก้ไข ลบ (CRUD) เมนูอาหาร หมวดหมู่ และเครื่องเคียง พร้อมรูปภาพ")
    add_bullet_item(doc, "โมดูลการสั่งอาหาร", "สั่งอาหารแยกตามโต๊ะ คำนวณราคารวม ส่วนลดคูปอง และออกรหัสรายวันสั้น (#001)")
    add_bullet_item(doc, "โมดูลเดลิเวอรี่", "เก็บข้อมูลผู้รับ ที่อยู่ พิกัด GPS คำนวณระยะทางและค่าจัดส่งอัตโนมัติ")
    add_bullet_item(doc, "โมดูลสต็อกวัตถุดิบ", "ผูกสูตรอาหาร (Recipe) เข้ากับเมนู ตัดสต็อกอัตโนมัติเมื่อสั่งอาหาร แจ้งเตือนเมื่อวัตถุดิบใกล้หมด")
    add_bullet_item(doc, "โมดูลรายงานและสถิติ", "สรุปยอดขายตามช่วงเวลา กราฟแสดงสถิติ และการส่งออกข้อมูล Excel/CSV")

    add_heading_2(doc, "1.4 ประโยชน์ที่คาดว่าจะได้รับ")
    add_bullet_item(doc, "ด้านการดำเนินงาน", "ลดความผิดพลาดและระยะเวลาในการรับส่งออเดอร์ระหว่างหน้าร้านและห้องครัว")
    add_bullet_item(doc, "ด้านการบริการลูกค้า", "เพิ่มความพึงพอใจของลูกค้าด้วยความสะดวกรวดเร็วในการสั่งอาหารและตรวจสอบสถานะ")
    add_bullet_item(doc, "ด้านการบริหารธุรกิจ", "เจ้าของร้านมีข้อมูลยอดขายและสต็อกวัตถุดิบแบบเรียลไทม์เพื่อใช้วางแผนการสั่งซื้อและโปรโมชัน")
    add_bullet_item(doc, "ด้านวิชาการ", "ผู้พัฒนามีความรู้ความเข้าใจเชิงลึกเกี่ยวกับ Django Framework, การจัดการฐานข้อมูล, และการ Deploy ระบบขึ้น Cloud")

    doc.add_page_break()

    # =========================================================================
    # บทที่ 2 การวิเคราะห์และออกแบบระบบ
    # =========================================================================
    add_heading_1(doc, "บทที่ 2: การวิเคราะห์และออกแบบระบบ (Analysis & Design)")

    add_heading_2(doc, "2.1 สถาปัตยกรรมระบบ (Model-Template-View)")
    p_arch = add_paragraph_styled(doc)
    p_arch.add_run(
        "ระบบพัฒนาขึ้นตามสถาปัตยกรรม Model-Template-View (MTV) ของ Django ซึ่งเทียบเท่ากับ MVC (Model-View-Controller) "
        "โดยแบ่งแยกหน้าที่การทำงานอย่างเป็นระเบียบ:"
    )
    format_run(p_arch.runs[0], size_pt=16)

    mtv_table_data = [
        ["Model (ข้อมูล)", "กำหนดโครงสร้างข้อมูล กฎทางธุรกิจ ความสัมพันธ์ และการติดต่อกับฐานข้อมูล", "myapp/models.py"],
        ["Template (การแสดงผล)", "ส่วนติดต่อผู้ใช้ (UI) ที่ผสาน Django Template Language และ Bootstrap 5", "myapp/templates/"],
        ["View (ตรรกะควบคุม)", "ประมวลผลตรรกะทางธุรกิจ ควบคุมการไหลของข้อมูล รับ Request และส่ง Response", "myapp/views/*.py"],
        ["URLs Routing (การจัดเส้นทาง)", "กำหนดเส้นทาง Map URL เข้ากับ View ฟังก์ชันที่รับผิดชอบ", "myproject/urls.py, myapp/urls.py"],
    ]
    create_styled_table(doc, ["ส่วนประกอบ", "หน้าที่ในระบบ 'อร่อยเกินเบอร์'", "ตำแหน่งไฟล์"], mtv_table_data, col_widths=[1.8, 3.45, 1.5])

    add_heading_2(doc, "2.2 ความสัมพันธ์ระหว่าง Model (Database Entity Relationships)")
    p_rel = add_paragraph_styled(doc)
    p_rel.add_run("ฐานข้อมูลถูกออกแบบให้ครอบคลุมความสัมพันธ์ครบทั้ง 3 รูปแบบตามหลักทฤษฎีฐานข้อมูลเชิงสัมพันธ์:")
    format_run(p_rel.runs[0], size_pt=16)

    rel_table_data = [
        ["One-to-One (1:1)", "User <--> Profile", "django.auth.User <-> Profile", "ขยายข้อมูลผู้ใช้: รูปโปรไฟล์, ปก, คะแนนสะสม, สถานะสมาชิก"],
        ["One-to-Many (1:N)", "Category --> MenuItem", "Category (1) -> MenuItem (N)", "หมวดหมู่อาหาร 1 หมวด บรรจุเมนูอาหารได้หลายเมนู"],
        ["One-to-Many (1:N)", "Order --> OrderItem", "Order (1) -> OrderItem (N)", "ออเดอร์ 1 ครั้ง สั่งอาหารได้หลายรายการ พร้อมจำนวนและราคา"],
        ["One-to-Many (1:N)", "User --> Order", "User (1) -> Order (N)", "ลูกค้า 1 บัญชี สามารถดูประวัติการสั่งอาหารย้อนหลังทั้งหมดได้"],
        ["Many-to-Many (N:M)", "MenuItem <--> Ingredient", "MenuItem <-> MenuIngredient <-> Ingredient", "สูตรอาหาร (Recipe): 1 เมนูใช้วัตถุดิบหลายตัว ใช้ตัดสต็อกอัตโนมัติ"],
        ["Many-to-Many (N:M)", "OrderItem <--> AddOn", "OrderItem <-> AddOn (ManyToManyField)", "รายการที่สั่ง 1 จาน สามารถเลือกเครื่องเคียงเพิ่มเติมได้หลายรายการ"],
    ]
    create_styled_table(doc, ["รูปแบบความสัมพันธ์", "คู่ความสัมพันธ์ในระบบ", "Model ที่เกี่ยวข้อง", "ความสำคัญทางธุรกิจ"], rel_table_data, col_widths=[1.5, 1.5, 1.75, 2.0])

    add_heading_2(doc, "2.3 พจนานุกรมข้อมูลที่สำคัญ (Data Dictionary)")
    dict_table_data = [
        ["MenuItem", "name / price", "CharField / Decimal", "ชื่อเมนู (unique), ราคาอาหาร (ต้องมากกว่า 0)"],
        ["MenuItem", "spice_level / image", "Integer / ImageField", "ระดับความเผ็ด 0-3, รูปภาพเมนู (จำกัด <= 10MB)"],
        ["Order", "daily_code / status", "CharField / Choice", "รหัสประจำวัน #001 (รีเซ็ตทุกวัน), สถานะ (pending/cooking/done)"],
        ["Delivery", "customer_name / address", "CharField / TextField", "ชื่อผู้รับสินค้า, ที่อยู่จัดส่ง"],
        ["Delivery", "lat / lng / fee", "Decimal / Decimal / Decimal", "พิกัดละติจูด, ลองจิจูด, ค่าจัดส่งคำนวณตามระยะทางจริง"],
        ["Ingredient", "stock_qty / reorder_level", "Decimal / Decimal", "จำนวนคงเหลือในคลัง, ระดับเตือนวัตถุดิบใกล้หมด"],
    ]
    create_styled_table(doc, ["ตาราง (Model)", "ชื่อฟิลด์ (Field)", "ชนิดข้อมูล (Type)", "คำอธิบาย / ข้อจำกัด"], dict_table_data, col_widths=[1.2, 1.7, 1.5, 2.35], header_bg="6B564A")

    doc.add_page_break()

    # =========================================================================
    # บทที่ 3 การพัฒนาระบบ
    # =========================================================================
    add_heading_1(doc, "บทที่ 3: การพัฒนาระบบ (System Implementation)")

    add_heading_2(doc, "3.1 ชุดเครื่องมือและเทคโนโลยี (Technology Stack)")
    add_bullet_item(doc, "ภาษาหลัก", "Python 3.14 — ภาษาโปรแกรมระดับสูง มีความเสถียรและไลบรารีครบครัน")
    add_bullet_item(doc, "เว็บเฟรมเวิร์ก", "Django 6.0 — รองรับ ORM, Authentication, Security, และ Admin Dashboard สมบูรณ์แบบ")
    add_bullet_item(doc, "ฐานข้อมูล", "SQLite สำหรับ Local Development และสลับเป็น PostgreSQL ผ่าน DATABASE_URL บน Production")
    add_bullet_item(doc, "Frontend & UI", "Bootstrap 5.3, Font Awesome 6, Chart.js สำหรับกราฟยอดขาย, Leaflet.js สำหรับแผนที่")
    add_bullet_item(doc, "Static & Media", "WhiteNoise สำหรับเสิร์ฟไฟล์ Static และ Pillow สำหรับประมวลผลรูปภาพอาหาร")
    add_bullet_item(doc, "Deployment & Container", "Docker (Multi-stage Build), Gunicorn WSGI Server, Render.com Cloud Platform")

    add_heading_2(doc, "3.2 ตารางตรวจสอบการพัฒนาระบบตามเกณฑ์ขั้นต่ำ 10 ข้อ (Core Requirements)")
    core_req_data = [
        ["1", "ระบบสมัครสมาชิก เข้าสู่ระบบ ออกจากระบบ", "Register, Login, Logout, รองรับ Google OAuth 2.0", "myapp/views/core.py"],
        ["2", "ผู้ใช้งานอย่างน้อย 2 บทบาท พร้อมกำหนดสิทธิ์จริง", "3 บทบาท: Customer, Staff, Admin คุมด้วย Decorator จริง", "myapp/models.py, views/*.py"],
        ["3", "การจัดการข้อมูล CRUD ด้วย Model", "CRUD เมนู, หมวดหมู่, ออเดอร์, วัตถุดิบ, คูปอง, รีวิว", "myapp/views/menu.py, orders.py"],
        ["4", "ระบบค้นหาข้อมูล (Search & Filter)", "ค้นหาชื่อเมนู, กรองตามหมวดหมู่, ช่วงราคา, ระดับความเผ็ด", "myapp/views/menu.py:menu_list"],
        ["5", "ระบบอัปโหลดรูปภาพหรือไฟล์", "อัปโหลดรูปเมนูอาหาร, โปรไฟล์ ตรวจขนาด <= 10MB ด้วย Pillow", "myapp/validators.py, forms.py"],
        ["6", "การแบ่งหน้ารายการข้อมูล (Pagination)", "ใช้ Django Paginator แบ่งหน้าละ 6-12 รายการ พร้อมปุ่มเปลี่ยนหน้า", "myapp/views/menu.py, orders.py"],
        ["7", "ความสัมพันธ์ระหว่าง Model อย่างน้อย 1 รูปแบบ", "มีครบทั้ง 3 แบบ: One-to-One, One-to-Many, Many-to-Many", "myapp/models.py"],
        ["8", "การตรวจสอบความถูกต้องของฟอร์ม (Validation)", "ตรวจราคา > 0, เลขโต๊ะ 1-999, ชื่อไม่ซ้ำ, รูปแบบเบอร์โทร", "myapp/forms.py, validators.py"],
        ["9", "ส่วนติดต่อผู้ใช้มีรูปแบบสม่ำเสมอ อ่านง่าย", "Bootstrap 5 + Master Template ครอบคลุม Responsive ทุกหน้าจอ", "myapp/templates/core/basetemplate.html"],
        ["10", "นำระบบขึ้น Hosting ใช้งานผ่านเน็ตได้", "Deploy บน Render.com ผ่าน Docker พร้อมใช้งานที่ omg02.onrender.com", "https://omg02.onrender.com"],
    ]
    create_styled_table(doc, ["#", "เกณฑ์ที่กำหนดตามโจทย์", "ผลการพัฒนาในโปรเจกต์", "ตำแหน่งไฟล์โค้ด"], core_req_data, col_widths=[0.4, 2.3, 2.35, 1.7])

    add_heading_2(doc, "3.3 ความสามารถเพิ่มเติมเพื่อเก็บคะแนน Bonus (Bonus Features)")
    add_bullet_item(doc, "1. RESTful API", "พัฒนาด้วย Django REST Framework เปิด Endpoint ภายใต้ /api/ (menus, categories, orders, deliveries) รองรับการเชื่อมต่อกับ Mobile App หรือระบบภายนอก")
    add_bullet_item(doc, "2. External API Integration", "เชื่อมต่อ Google Maps Embed สำหรับแผนที่ร้าน, LINE Notify แจ้งเตือนเมื่อมีออเดอร์ใหม่เข้าห้องครัว, และ OpenStreetMap Nominatim สำหรับคำนวณพิกัดจัดส่ง")
    add_bullet_item(doc, "3. Dashboard & Data Visualization", "หน้าแดชบอร์ดสรุปยอดขายประจำวัน/สัปดาห์/เดือน พร้อมกราฟแนวโน้มยอดขายด้วย Chart.js และจัดอันดับเมนูขายดี")
    add_bullet_item(doc, "4. Automated Testing", "มีชุดเทสต์แบบอัตโนมัติมากถึง 245 Test Cases ครอบคลุม Model, Form, View, API, Security, และ Permission ผ่านการทดสอบ 100%")
    add_bullet_item(doc, "5. Data Export", "รองรับการส่งออกรายงานยอดขายและสรุปออเดอร์เป็นไฟล์ Excel (.xlsx) ด้วย openpyxl และไฟล์ CSV")
    add_bullet_item(doc, "6. Docker & Production Ready", "พัฒนา Dockerfile แบบ Multi-stage Build ปรับระบบความปลอดภัย ป้องกัน CSRF และ Rate Limiting ป้องกันการ Brute-Force")

    doc.add_page_break()

    # =========================================================================
    # บทที่ 4 ผลการพัฒนาและภาพรวมระบบ
    # =========================================================================
    add_heading_1(doc, "บทที่ 4: ผลการพัฒนาและภาพรวมระบบ (Implementation Results)")

    add_heading_2(doc, "4.1 รายละเอียดโมดูลการทำงานหลัก")

    add_heading_3(doc, "1. หน้าหลักและรายการเมนูอาหาร (Home & Menu Catalog)")
    p_m1 = add_paragraph_styled(doc)
    p_m1.add_run(
        "แสดงรายการเมนูอาหารทั้งหมด 16 เมนู พร้อมรูปภาพจริง ราคา ระดับความเผ็ด และสถานะพร้อมขาย "
        "ผู้ใช้สามารถค้นหาชื่ออาหารและเลือกกรองตามหมวดหมู่ (ผัด/แกง/ทอด/เครื่องดื่ม/ของหวาน) "
        "และคลิกดูหน้ารายละเอียดเมนู (Menu Detail) พร้อมรายการเมนูแนะนำใกล้เคียง"
    )
    format_run(p_m1.runs[0], size_pt=16)

    add_heading_3(doc, "2. ระบบสั่งอาหารและจัดการโต๊ะ (Order & Table QR)")
    p_m2 = add_paragraph_styled(doc)
    p_m2.add_run(
        "ลูกค้าสามารถเปิดออเดอร์ตามเลขโต๊ะ สั่งรายการอาหาร เลือกเครื่องเคียง (Addon) ระบุข้อความพิเศษ "
        "และคำนวณราคารวมพร้อมส่วนลดคูปองได้ทันที ระบบจะสร้างรหัสออเดอร์รายวันสั้น เช่น #001 "
        "และสามารถพิมพ์ใบเสร็จรับเงิน (Receipt Print) ได้ทันที"
    )
    format_run(p_m2.runs[0], size_pt=16)

    add_heading_3(doc, "3. ระบบเดลิเวอรี่และงานไรเดอร์ (Delivery & Tracking)")
    p_m3 = add_paragraph_styled(doc)
    p_m3.add_run(
        "รองรับการสั่งแบบจัดส่งถึงบ้าน เก็บชื่อ เบอร์โทร ที่อยู่ และปักหมุดพิกัด GPS "
        "ระบบจะคำนวณระยะทางจากร้านและคิดค่าส่งให้อัตโนมัติ พนักงานสามารถติดตามสถานะ "
        "(รอส่ง -> กำลังจัดส่ง -> จัดส่งแล้ว) ผ่านหน้า Delivery Dashboard และ Rider View"
    )
    format_run(p_m3.runs[0], size_pt=16)

    add_heading_3(doc, "4. ระบบคลังสต็อกและสูตรอาหาร (Inventory & Recipe Management)")
    p_m4 = add_paragraph_styled(doc)
    p_m4.add_run(
        "ระบบผูกสูตรอาหาร (Recipe) เข้ากับแต่ละเมนู เมื่อลูกค้าสั่งอาหารและสถานะออเดอร์เปลี่ยน "
        "ระบบจะตัดยอดวัตถุดิบในสต็อกโดยอัตโนมัติ พร้อมแสดงแถบสีแจ้งเตือนเมื่อวัตถุดิบใกล้หมด (Reorder Level)"
    )
    format_run(p_m4.runs[0], size_pt=16)

    add_heading_3(doc, "5. แดชบอร์ดสรุปยอดขาย (Sales Dashboard & Charts)")
    p_m5 = add_paragraph_styled(doc)
    p_m5.add_run(
        "แดชบอร์ดเฉพาะเจ้าของร้านและพนักงาน แสดงยอดขายรวมวันนี้ ยอดขายรายสัปดาห์ จำนวนออเดอร์ทั้งหมด "
        "และแสดงกราฟแท่งเปรียบเทียบยอดขาย 7 วันย้อนหลัง พร้อมปุ่มส่งออกรายงานเป็น Excel และ CSV"
    )
    format_run(p_m5.runs[0], size_pt=16)

    add_heading_3(doc, "6. ระบบจัดการผู้ใช้และสิทธิ์ (Authentication & Role Management)")
    p_m6 = add_paragraph_styled(doc)
    p_m6.add_run(
        "หน้า Login, Register, Profile พร้อมระบบสมาชิกและระดับคะแนนสะสม (Member Points) "
        "เมื่อสั่งอาหารจะได้รับคะแนนสะสม และสามารถนำคะแนนไปแลกคูปองส่วนลดในระบบได้"
    )
    format_run(p_m6.runs[0], size_pt=16)

    doc.add_page_break()

    # =========================================================================
    # บทที่ 5 การทดสอบและสรุปผล
    # =========================================================================
    add_heading_1(doc, "บทที่ 5: การทดสอบและสรุปผล (Testing & Conclusion)")

    add_heading_2(doc, "5.1 ผลการทดสอบอัตโนมัติ (Automated Testing Results)")
    p_test = add_paragraph_styled(doc)
    p_test.add_run(
        "ระบบได้รับการทดสอบอย่างครอบคลุมผ่านชุดทดสอบอัตโนมัติของ Django (python manage.py test) "
        "จำนวนทั้งสิ้น 245 Test Cases ซึ่งผ่านการทดสอบสำเร็จสมบูรณ์ 100% (OK) โดยแบ่งการทดสอบออกเป็นกลุ่มดังนี้:"
    )
    format_run(p_test.runs[0], size_pt=16)

    test_table_data = [
        ["Model Tests", "48 tests", "ความถูกต้องของฟิลด์, Default values, Constraints, Clean methods", "PASSED (100%)"],
        ["Form Validation Tests", "35 tests", "การตรวจสอบราคา > 0, เลขโต๊ะ 1-999, ขนาดรูปภาพ <= 10MB", "PASSED (100%)"],
        ["View & Security Tests", "64 tests", "HTTP Status, Login Required, CSRF Protection, Rate Limiting", "PASSED (100%)"],
        ["Role & Permission Tests", "38 tests", "ตรวจสอบการเข้าถึงหน้า Staff/Admin โดย User ทั่วไป (ต้องได้ 403)", "PASSED (100%)"],
        ["REST API Tests", "32 tests", "GET/POST/PUT/DELETE ของ ViewSets, Serializer validation", "PASSED (100%)"],
        ["Delivery & Formula Tests", "28 tests", "การคำนวณระยะทาง Haversine, การตัดสต็อกวัตถุดิบอัตโนมัติ", "PASSED (100%)"],
        ["รวมทั้งหมด (Total)", "245 tests", "ครอบคลุมการทำงานทุกส่วนของระบบ (Ran 245 tests in 120s)", "PASSED (100%)"],
    ]
    create_styled_table(doc, ["หมวดหมู่การทดสอบ", "จำนวนเทสต์", "ขอบเขตที่ตรวจสอบ", "ผลการทดสอบ"], test_table_data, col_widths=[1.7, 1.0, 2.8, 1.25], header_bg="1B5E20")

    add_heading_2(doc, "5.2 สรุปผลการดำเนินโครงงาน")
    p_concl = add_paragraph_styled(doc)
    p_concl.add_run(
        "การพัฒนาระบบเว็บแอปพลิเคชัน 'อร่อยเกินเบอร์' ประสบผลสำเร็จตามวัตถุประสงค์ทุกประการ "
        "ระบบสามารถทำงานได้จริงบนสภาพแวดล้อมจริง (Production Environment) บนระบบคลาวด์ Render.com "
        "รองรับการใช้งานพร้อมกันของผู้ใช้หลายบทบาท มีความเสถียร ปลอดภัย และมีฟังก์ชันการทำงานที่ครบถ้วนเกินกว่าเกณฑ์ขั้นต่ำ "
        "โดยได้รับฟังก์ชันโบนัสครบทุกมิติ"
    )
    format_run(p_concl.runs[0], size_pt=16)

    add_heading_2(doc, "5.3 ปัญหา อุปสรรค และแนวทางการพัฒนาต่อยอด")
    add_bullet_item(doc, "ปัญหาที่พบ", "การ Deploy ฐานข้อมูล SQLite บน Cloud Container Free Tier ที่ไม่มี Persistent Disk ทำให้ข้อมูลรีเซ็ตเมื่อเกิดการ Redeploy")
    add_bullet_item(doc, "วิธีแก้ปัญหา", "ออกแบบระบบ Initial Seed และ Test Users ให้รันอัตโนมัติทุกครั้งที่ Container เริ่มทำงาน (Idempotent Migration & Seeding)")
    add_bullet_item(doc, "แนวทางต่อยอด", "การเชื่อมต่อเกตเวย์การชำระเงินจริง (Payment Gateway เช่น Omise หรือ PromptPay Webhook) และการเชื่อมต่อ Web Push Notification สำหรับแจ้งเตือนแบบเรียลไทม์")

    doc.add_page_break()

    # =========================================================================
    # ภาคผนวก (APPENDIX)
    # =========================================================================
    add_heading_1(doc, "ภาคผนวก (Appendix)")

    add_heading_2(doc, "ภาคผนวก ก: ข้อมูลการเข้าใช้งานระบบและซอร์สโค้ด")
    p_app_desc = add_paragraph_styled(doc)
    p_app_desc.add_run("ผู้ตรวจประเมินสามารถสแกน QR Code ด้านล่างนี้เพื่อเปิดเข้าใช้งานระบบจริงหรือตรวจดูซอร์สโค้ดได้ทันที:")
    format_run(p_app_desc.runs[0], size_pt=16)

    qr_render = os.path.join(BASE_DIR, "docs", "qr_render.png")
    qr_github = os.path.join(BASE_DIR, "docs", "qr_github.png")

    t_qr = doc.add_table(rows=2, cols=2)
    t_qr.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(t_qr)

    row_img = t_qr.rows[0].cells
    if os.path.exists(qr_render):
        p_qr1 = row_img[0].paragraphs[0]
        p_qr1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_qr1.add_run().add_picture(qr_render, width=Inches(1.8))
    if os.path.exists(qr_github):
        p_qr2 = row_img[1].paragraphs[0]
        p_qr2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_qr2.add_run().add_picture(qr_github, width=Inches(1.8))

    row_txt = t_qr.rows[1].cells
    p_t1 = row_txt[0].paragraphs[0]
    p_t1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_q1 = p_t1.add_run("URL ระบบบน Cloud Hosting:\nhttps://omg02.onrender.com\n(เข้าใช้งานระบบจริงผ่านอินเทอร์เน็ต)")
    format_run(run_q1, size_pt=14, bold=True, color=COLOR_PRIMARY)

    p_t2 = row_txt[1].paragraphs[0]
    p_t2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_q2 = p_t2.add_run("GitHub Repository:\nhttps://github.com/omgx624-gif/OMg02\n(ซอร์สโค้ดโครงงานฉบับสมบูรณ์)")
    format_run(run_q2, size_pt=14, bold=True, color=COLOR_PRIMARY)

    for cell in row_img:
        set_cell_background(cell, "FAF6EF")
    for cell in row_txt:
        set_cell_background(cell, "FAF6EF")

    p_sp = doc.add_paragraph()
    p_sp.paragraph_format.space_before = Pt(8)
    p_sp.paragraph_format.space_after = Pt(8)

    add_heading_2(doc, "ภาคผนวก ข: ตารางข้อมูลบัญชีผู้ใช้สำหรับทดสอบระบบ (Test Accounts)")
    account_full_data = [
        ["Admin (ผู้ดูแลระบบ)", "admin", "Admin1234!", "เข้าใช้งาน Django Admin (/admin/), จัดการฐานข้อมูลทั้งหมด, ควบคุมสิทธิ์"],
        ["Staff (พนักงาน)", "staff (หรือ Jj12)", "Staff1234!", "ดูแดชบอร์ดร้าน, จัดการออเดอร์, คลังสต็อก, จัดการเดลิเวอรี่"],
        ["Customer (ลูกค้า)", "customer (หรือ Ff12)", "User1234!", "สั่งอาหารหน้าร้าน, จองโต๊ะ, สั่งเดลิเวอรี่, สะสมแต้ม, เขียนรีวิว"],
    ]
    create_styled_table(doc, ["บทบาท (Role)", "Username", "Password", "สิทธิ์และสิ่งที่ทดสอบได้"], account_full_data, col_widths=[1.5, 1.4, 1.3, 2.55])

    add_heading_2(doc, "ภาคผนวก ค: คู่มือการใช้งานระบบโดยย่อ (Quick User Guide)")
    add_bullet_item(doc, "ขั้นตอนที่ 1 การเข้าสู่ระบบ", "เปิดเบราว์เซอร์ไปที่ https://omg02.onrender.com กดปุ่ม 'เข้าสู่ระบบ' ที่แถบเมนูด้านบน แล้วกรอก Username/Password ตามตารางด้านบน")
    add_bullet_item(doc, "ขั้นตอนที่ 2 การสั่งอาหารหน้าร้าน", "ไปที่เมนู 'เมนูอาหาร' เลือกอาหารที่ต้องการ กด 'สั่งอาหาร' เลือกระดับความเผ็ดและเครื่องเคียง ระบุเลขโต๊ะ แล้วกดยืนยันออเดอร์")
    add_bullet_item(doc, "ขั้นตอนที่ 3 การจัดการออเดอร์และครัว", "สลับล็อกอินเป็นพนักงาน ไปที่ 'แดชบอร์ดออเดอร์' เพื่อกดปรับสถานะอาหารเป็น 'กำลังทำ' หรือ 'เสร็จสิ้น'")
    add_bullet_item(doc, "ขั้นตอนที่ 4 การตรวจสอบสต็อก", "เมนู 'คลังสต็อก' ช่วยให้พนักงานตรวจสอบจำนวนวัตถุดิบคงเหลือและปรับเพิ่มสต็อกได้ทันที")
    add_bullet_item(doc, "ขั้นตอนที่ 5 การดูรายงานยอดขาย", "เข้าหน้า 'Dashboard' เพื่อดูสถิติยอดขายวันนี้ สัปดาห์นี้ พร้อมกราฟแท่ง และกดปุ่ม 'Export Excel' เพื่อดาวน์โหลดรายงาน")

    # บันทึกไฟล์ Word
    doc.save(OUTPUT_DOCX)
    print("SUCCESS: Word Document generated at", OUTPUT_DOCX)
    print("FILE SIZE:", os.path.getsize(OUTPUT_DOCX), "bytes")


if __name__ == "__main__":
    build_word_document()

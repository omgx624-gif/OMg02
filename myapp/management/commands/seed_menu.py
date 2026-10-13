import io
import os
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import Group, Permission

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from myapp.models import Category, Coupon, Ingredient, MenuIngredient, MenuItem, StoreLocation

# (ชื่อเมนู, หมวดหมู่, ราคา, ระดับความเผ็ด, คำอธิบาย, พร้อมขาย, ไฟล์รูปภาพ)
SEED_DATA = [
    ('ข้าวผัดกะเพราหมูสับ', 'rice', 50, 2,
     'ผัดกะเพราพริกสดโขลกเองทุกวัน หมูสับสไลซ์บาง หอมใบกะเพราฉีกขาด เสิร์ฟพร้อมไข่ดาว', True,
     'menu_images/2026/09/b36f3b07-ae2a-4061-a2ee-ac06cbf0110f.png'),
    ('ข้าวราดแกงเขียวหวานไก่', 'rice', 45, 1,
     'แกงเขียวหวานกะทิข้นหอมมะกรูด ไก่นุ่ม เพิ่มมะเขือเปราะและใบโหระพา', True,
     'menu_images/2026/09/90ff02f7-c049-42e2-81ed-ec58f1280545.png'),
    ('ผัดไทยกุ้งสด', 'rice', 70, 1,
     'เส้นจันทน์เจ้ายืดหยุ่น กุ้งสดตัวโต รสชาติกลมกล่อมตามสูตรดั้งเดิม พร้อมถั่วกลองและมะนาว', True,
     'menu_images/2026/09/Gemini_Generated_Image_nxifltnxifltnxif.jpg'),
    ('ต้มยำกุ้งน้ำข้น', 'soup', 120, 3,
     'น้ำซุปกะทิเข้มข้น กุ้งแม่น้ำสด ตะไคร้ ใบมะกรูด รสเปรี้ยวเผ็ดครบรสแบบต้นตำรับ', True,
     'menu_images/2026/09/0d3a6f15-ff11-426c-a42a-b49b5084d3f4.jpg'),
    ('แกงส้มชะอมไข่', 'soup', 60, 2,
     'แกงส้มรสจัดเต็ม อ่อมชะอมหอมๆ ผักสดตามฤดูกาล อุ่นๆ ชื่นใจ', False,
     'menu_images/2026/09/6a262ce4-7110-428c-8a34-6c36ea9a4110.jpg'),
    ('ไก่ทอดกรอบเจริญเมือง', 'fried', 55, 0,
     'ไก่หมักเครื่องเทศสูตรเด็ดทอดร้อนๆ กรอบนอกนุ่มใน ทานคู่ข้าวเหนียวร้อนๆ', True,
     'menu_images/2026/10/ไกทอดกรอบ_เจรญเมอง.png'),
    ('ปลาเสียบตะไคร้', 'fried', 150, 1,
     'ปลาสลิดตัวใหญ่เสียบตะไคร้ทอดกรอบทั้งตัว เหยาะน้ำพริกผักชีรสเด็ด', True,
     'menu_images/2026/10/ปลาเสยบตะไครกรอบหอม.png'),
    ('ชาไทยเย็น', 'drink', 25, 0,
     'ชารสเข้มข้นชงใหม่ทุกแก้ว เติมความหวานด้วยนมข้น แช่เย็นจัด', True,
     'menu_images/2026/09/Gemini_Generated_Image_2rxelg2rxelg2rxe.jpg'),
    ('มะนาวโซดา', 'drink', 30, 0,
     'มะนาวคั้นสด โซดาแช่เย็นก๊อกแก๊ก สดชื่นดับร้อนได้ทั้งวัน', True,
     'menu_images/2026/09/Gemini_Generated_Image_c7wulzc7wulzc7wu.jpg'),
    ('ข้าวเหนียวมะม่วง', 'dessert', 60, 0,
     'มะม่วงน้ำดอกไม้สุกหวานฉ่ำ เสิร์ฟกับข้าวเหนียวนึ่งราดกะทิ โรยถั่วทองกรอบ', True,
     'menu_images/2026/09/Gemini_Generated_Image_c4q70qc4q70qc4q7.jpg'),
    ('วุ้นกะทิเต้าหู้', 'dessert', 35, 0,
     'วุ้นเดือยทองเนื้อหยุ่น กะทิหวานมัน ทานเย็นๆ ละมุนลิ้น', True,
     'menu_images/2026/09/Gemini_Generated_Image_mdi18kmdi18kmdi1.jpg'),
    ('ขนมครกกะทิ', 'dessert', 40, 0,
     'ขนมครกแป้งหมี่กรอบนอก ไส้กะทิมะพร้าวอ่อน อบร้อนทุกชุด', False,
     'menu_images/2026/09/Gemini_Generated_Image_6uux7j6uux7j6uux.jpg'),
    ('กะเพราไก่', 'rice', 50, 2,
     'กะเพราไก่เนื้อนุ่ม รสเข้มข้น หอมใบกะเพราสด', True,
     'menu_images/2026/09/Gemini_Generated_Image_y5cxjvy5cxjvy5cx.jpg'),
    ('ทอดมันพันตะไคร้', 'fried', 150, 1,
     'ทอดมันเนื้อเด้งพันก้านตะไคร้หอมกรุ่น ทอดร้อนๆ เสิร์ฟคู่น้ำจิ้มอาจาด', True,
     'menu_images/2026/09/Gemini_Generated_Image_c9e4fxc9e4fxc9e4.jpg'),
    ('ไก่ทอดกรอบ', 'fried', 55, 0,
     'ไก่ทอดชิ้นโต คลุกเคล้าเครื่องปรุงสูตรพิเศษ กรอบอร่อยเคี้ยวเพลิน', True,
     'menu_images/2026/09/Gemini_Generated_Image_99hv3i99hv3i99hv.jpg'),
    ('ผัดกะเพราหมูกรอบ', 'rice', 60, 1,
     'ผัดกะเพราหมูกรอบชิ้นหนา หนังกรอบสะใจ ผัดพริกกระเทียมเข้มข้น', True,
     'menu_images/2026/09/978d2150-9167-4ecc-89c2-c163cd91e6f2.png'),
]

CATEGORY_COLORS = {
    'rice': (255, 213, 79),      # amber
    'soup': (255, 138, 101),     # coral
    'fried': (174, 213, 129),    # green
    'drink': (79, 195, 247),     # light blue
    'dessert': (244, 143, 177),  # pink
}

CATEGORY_LABELS = dict(MenuItem.CATEGORY_CHOICES)

# วัตถุดิบตัวอย่างสำหรับสต็อก (ชื่อ, หน่วย, คงเหลือ, ระดับเตือน)
INGREDIENT_SEED = [
    ('ข้าว', 'กรัม', 5000, 500),
    ('ใบกะเพรา', 'กรัม', 500, 50),
    ('หมูสับ', 'กรัม', 2000, 200),
    ('ไก่', 'กรัม', 3000, 300),
    ('กุ้ง', 'ตัว', 200, 20),
    ('กะทิ', 'มล', 3000, 300),
    ('มะเขือเปราะ', 'ลูก', 200, 20),
    ('เส้นจันทน์', 'กรัม', 1000, 100),
    ('ถั่วงอก', 'กรัม', 1000, 100),
    ('ตะไคร้', 'ต้น', 200, 20),
    ('ใบมะกรูด', 'ใบ', 500, 50),
    ('มะนาว', 'ลูก', 100, 10),
    ('ชะอม', 'กรัม', 500, 50),
    ('ไข่', 'ฟอง', 300, 30),
    ('แป้งทอด', 'กรัม', 2000, 200),
    ('น้ำมัน', 'มล', 2000, 200),
    ('ปลาสลิด', 'ตัว', 50, 5),
    ('ชาไทย', 'กรัม', 500, 50),
    ('นมข้น', 'กระป๋อง', 100, 10),
    ('น้ำตาล', 'กรัม', 1000, 100),
    ('โซดา', 'ขวด', 100, 10),
    ('ข้าวเหนียว', 'กรัม', 2000, 200),
    ('มะม่วง', 'ลูก', 100, 10),
    ('วุ้น/เดือยทอง', 'กรัม', 1000, 100),
    ('แป้งข้าวจ้าว', 'กรัม', 1000, 100),
    ('มะพร้าว', 'กรัม', 1000, 100),
    ('กระเทียม', 'กลีบ', 500, 50),
    ('ผักสด', 'กรัม', 1000, 100),
]

# สัดส่วนวัตถุดิบที่ใช้ (ingredient_name, quantity) ต่อ 1 จาน สำหรับแต่ละเมนู
MENU_RECIPES = {
    'ข้าวผัดกะเพราหมูสับ': [('ข้าว', 200), ('ใบกะเพรา', 10), ('หมูสับ', 80), ('กระเทียม', 5), ('น้ำมัน', 10)],
    'ข้าวราดแกงเขียวหวานไก่': [('ข้าว', 200), ('ไก่', 100), ('กะทิ', 100)],
    'ผัดไทยกุ้งสด': [('เส้นจันทน์', 100), ('กุ้ง', 3), ('ถั่วงอก', 50), ('มะนาว', 1)],
    'ต้มยำกุ้งน้ำข้น': [('กุ้ง', 4), ('ตะไคร้', 1), ('ใบมะกรูด', 3), ('มะนาว', 1), ('กะทิ', 100)],
    'แกงส้มชะอมไข่': [('ชะอม', 100), ('ไข่', 2), ('ผักสด', 100)],
    'ไก่ทอดกรอบเจริญเมือง': [('ไก่', 150), ('แป้งทอด', 50), ('น้ำมัน', 50)],
    'ปลาเสียบตะไคร้': [('ปลาสลิด', 1), ('ตะไคร้', 2), ('มะนาว', 1)],
    'ชาไทยเย็น': [('ชาไทย', 10), ('นมข้น', 1), ('น้ำตาล', 15)],
    'มะนาวโซดา': [('มะนาว', 1), ('โซดา', 1), ('น้ำตาล', 10)],
    'ข้าวเหนียวมะม่วง': [('ข้าวเหนียว', 150), ('มะม่วง', 1), ('กะทิ', 50), ('น้ำตาล', 20)],
    'วุ้นกะทิเต้าหู้': [('วุ้น/เดือยทอง', 100), ('กะทิ', 100), ('น้ำตาล', 20)],
    'ขนมครกกะทิ': [('แป้งข้าวจ้าว', 50), ('กะทิ', 50), ('มะพร้าว', 20)],
    'กะเพราไก่': [('ข้าว', 200), ('ใบกะเพรา', 10), ('ไก่', 80), ('กระเทียม', 5), ('น้ำมัน', 10)],
    'ทอดมันพันตะไคร้': [('ปลาสลิด', 1), ('ตะไคร้', 2)],
    'ไก่ทอดกรอบ': [('ไก่', 150), ('แป้งทอด', 50), ('น้ำมัน', 50)],
    'ผัดกะเพราหมูกรอบ': [('ข้าว', 200), ('หมูสับ', 80), ('ใบกะเพรา', 10)],
}

# คูปองส่วนลดตัวอย่าง
COUPON_SEED = [
    ('WELCOME10', 'percent', 10, 0, None),
    ('SAVE50', 'fixed', 50, 200, None),
    ('STUDENT15', 'percent', 15, 100, 100),
    ('NEWUSER30', 'fixed', 30, 150, 50),
]


def _load_font(size, bold=True):
    """โหลดฟอนต์ที่รองรับภาษาไทยจาก Windows พร้อม fallback"""
    candidates = [
        r'C:\Windows\Fonts\tahomabd.ttf' if bold else r'C:\Windows\Fonts\tahoma.ttf',
        r'C:\Windows\Fonts\arialbd.ttf' if bold else r'C:\Windows\Fonts\arial.ttf',
        r'C:\Windows\Fonts\leelauib.ttf',
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_placeholder_image(menu_name, category, price):
    """สร้างรูป placeholder ง่ายๆ ด้วย Pillow"""
    width, height = 640, 420
    bg = CATEGORY_COLORS.get(category, (200, 200, 200))
    img = Image.new('RGB', (width, height), bg)
    draw = ImageDraw.Draw(img)

    # กรอบขาวรอบรูป
    draw.rectangle([12, 12, width - 13, height - 13], outline='white', width=4)

    title_font = _load_font(38)
    price_font = _load_font(30)
    small_font = _load_font(22)

    # ชื่อเมนู (ตัดบรรทัดถ้ายาว)
    text_color = (62, 39, 35)
    lines = []
    line = ''
    for word in menu_name.split():
        trial = f'{line} {word}'.strip()
        if draw.textlength(trial, font=title_font) > width - 100:
            lines.append(line)
            line = word
        else:
            line = trial
    lines.append(line)
    if len(lines) > 2:
        lines = [lines[0], ' '.join(lines[1:])]

    y = height / 2 - len(lines) * 26
    for ln in lines:
        w = draw.textlength(ln, font=title_font)
        draw.text(((width - w) / 2, y), ln, fill=text_color, font=title_font)
        y += 52

    # ราคา
    price_text = f'฿{price:,.0f}'
    w = draw.textlength(price_text, font=price_font)
    draw.text(((width - w) / 2, y + 14), price_text, fill=(27, 94, 32), font=price_font)

    # หมวดหมู่ด้านบนซ้าย
    label = CATEGORY_LABELS.get(category, category)
    draw.rounded_rectangle([28, 28, 28 + draw.textlength(label, font=small_font) + 24, 68],
                           radius=20, fill='white')
    draw.text((40, 34), label, fill=text_color, font=small_font)

    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=88)
    return buf.getvalue()


class Command(BaseCommand):
    help = 'สร้างข้อมูลเมนูตัวอย่างพร้อมรูป placeholder สำหรับสาธิตระบบ'

    def handle(self, *args, **options):
        # สร้างหมวดหมู่เริ่มต้น
        categories_data = [
            ('rice', 'ผัด/ข้าวราดแกง', 1),
            ('soup', 'แกง/ต้มยำ', 2),
            ('fried', 'อาหารทอด', 3),
            ('drink', 'เครื่องดื่ม', 4),
            ('dessert', 'ของหวาน', 5),
        ]
        cat_created = 0
        for slug, name, order in categories_data:
            _, created = Category.objects.update_or_create(
                slug=slug,
                defaults={'name': name, 'sort_order': order, 'is_active': True},
            )
            if created:
                cat_created += 1

        self.stdout.write(self.style.SUCCESS(
            f'สร้างหมวดหมู่ใหม่ {cat_created} หมวดหมู่'
        ))

        # ตั้งค่า PromptPay ตัวอย่างถ้ายังไม่ได้ตั้ง (ทำให้ QR ใช้งานได้ทันที)
        store_setting = StoreLocation.get_setting()
        if not store_setting.promptpay_id:
            store_setting.promptpay_id = '0812345678'
            store_setting.save(update_fields=['promptpay_id'])

        # สร้างวัตถุดิบ (stock) สำหรับสต็อก
        ingredient_objects = {}
        ing_created = 0
        for ing_name, unit, stock_qty, reorder_level in INGREDIENT_SEED:
            ing, created = Ingredient.objects.update_or_create(
                name=ing_name,
                defaults={
                    'unit': unit,
                    'stock_qty': stock_qty,
                    'reorder_level': reorder_level,
                    'is_active': True,
                },
            )
            ingredient_objects[ing_name] = ing
            if created:
                ing_created += 1

        self.stdout.write(self.style.SUCCESS(
            f'สร้างวัตถุดิบใหม่ {ing_created} รายการ | รวม {len(ingredient_objects)} รายการ'
        ))

        created_count = 0
        updated_count = 0
        recipe_count = 0

        for i, (name, category, price, spice, description, available, image_path) in enumerate(SEED_DATA):
            menu, created = MenuItem.objects.update_or_create(
                name=name,
                defaults={
                    'category': category,
                    'price': price,
                    'spice_level': spice,
                    'description': description,
                    'available': available,
                    'date_added': timezone.localdate() - timedelta(days=i),
                },
            )

            # เชื่อมโยงรูปภาพที่มีอยู่จริง
            if image_path:
                full_image_path = os.path.join(settings.MEDIA_ROOT, image_path)
                if os.path.exists(full_image_path):
                    menu.image = image_path
                    menu.save(update_fields=['image'])

            # เชื่อมโยง category_fk กับ Category model
            cat_obj = Category.objects.filter(slug=category).first()
            if cat_obj and menu.category_fk != cat_obj:
                menu.category_fk = cat_obj
                menu.save(update_fields=['category_fk'])

            # เพิ่มสัดส่วนวัตถุดิบ (Recipe) ให้เมนูนี้ เพื่อให้มี stock ต่อเมนู
            for ing_name, qty in MENU_RECIPES.get(name, []):
                ing = ingredient_objects.get(ing_name)
                if ing is None:
                    continue
                MenuIngredient.objects.update_or_create(
                    menu=menu,
                    ingredient=ing,
                    defaults={'quantity': qty},
                )
                recipe_count += 1

            if created:
                created_count += 1
            else:
                updated_count += 1

        # ให้ทุกเมนูมีสัดส่วนวัตถุดิบอย่างน้อยหนึ่งรายการ (กันเมนูที่เพิ่มเองนอก seed)
        default_ing, _ = Ingredient.objects.get_or_create(
            name='วัตถุดิบหลัก',
            defaults={'unit': 'หน่วย', 'stock_qty': 1000, 'reorder_level': 100, 'is_active': True},
        )
        for menu in MenuItem.objects.all():
            if not menu.ingredients.exists():
                MenuIngredient.objects.get_or_create(
                    menu=menu,
                    ingredient=default_ing,
                    defaults={'quantity': 1},
                )

        # เติมรูปเมนูที่ยังไม่มีรูป (รวมเมนูที่เพิ่มเองนอกเหนือจาก SEED_DATA)
        backfilled = 0
        for menu in MenuItem.objects.all():
            if menu.image:
                continue
            filename = f'menu_{menu.pk}.jpg'
            content = make_placeholder_image(menu.name, menu.category, menu.price)
            menu.image.save(filename, ContentFile(content), save=True)
            backfilled += 1

        # สร้างกลุ่มสิทธิ์พนักงาน (Staff) สำหรับเข้าถึงโมดูลที่จำเป็น
        staff_group, _ = Group.objects.get_or_create(name='Staff')
        allowed_models = [
            'order', 'orderitem', 'coupon', 'ingredient', 'menuingredient',
            'menuitem', 'category', 'delivery', 'review', 'reservation',
        ]
        perms = Permission.objects.filter(
            content_type__app_label='myapp',
            codename__regex=r'^(add|change|delete|view)_(' + '|'.join(allowed_models) + r')$',
        )
        staff_group.permissions.set(perms)

        # สร้างคูปองส่วนลดตัวอย่าง
        coupon_created = 0
        for code, discount_type, value, min_order, max_uses in COUPON_SEED:
            _, created = Coupon.objects.update_or_create(
                code=code,
                defaults={
                    'discount_type': discount_type,
                    'value': value,
                    'min_order': min_order,
                    'max_uses': max_uses,
                    'is_active': True,
                },
            )
            if created:
                coupon_created += 1

        self.stdout.write(self.style.SUCCESS(
            f'สร้าง/อัปเดตคูปอง {len(COUPON_SEED)} รายการ (ใหม่ {coupon_created})'\
        ))

        self.stdout.write(self.style.SUCCESS(
            f'เสร็จสิ้น! สร้างใหม่ {created_count} เมนู | อัปเดต {updated_count} เมนู '
            f'| เติมรูปเพิ่ม {backfilled} เมนู '
            f'| สร้าง/อัปเดตสูตร {recipe_count} รายการ '
            f'| รวมในระบบ {MenuItem.objects.count()} เมนู'
        ))

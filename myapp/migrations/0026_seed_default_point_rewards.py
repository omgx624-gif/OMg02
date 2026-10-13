from django.db import migrations


def seed_default_rewards(apps, schema_editor):
    PointReward = apps.get_model('myapp', 'PointReward')
    defaults = [
        {
            'name': 'คูปองส่วนลด 50 บาท',
            'description': 'ส่วนลด 50 บาท สำหรับออเดอร์ขั้นต่ำ 300 บาท',
            'points_cost': 500,
            'discount_type': 'fixed',
            'value': '50.00',
            'min_order': '300.00',
        },
        {
            'name': 'คูปองส่วนลด 100 บาท',
            'description': 'ส่วนลด 100 บาท สำหรับออเดอร์ขั้นต่ำ 500 บาท',
            'points_cost': 900,
            'discount_type': 'fixed',
            'value': '100.00',
            'min_order': '500.00',
        },
        {
            'name': 'คูปองส่วนลด 10%',
            'description': 'ส่วนลด 10% สำหรับออเดอร์ขั้นต่ำ 400 บาท',
            'points_cost': 800,
            'discount_type': 'percent',
            'value': '10.00',
            'min_order': '400.00',
        },
        {
            'name': 'คูปองส่วนลด 20%',
            'description': 'ส่วนลด 20% สำหรับออเดอร์ขั้นต่ำ 800 บาท',
            'points_cost': 1500,
            'discount_type': 'percent',
            'value': '20.00',
            'min_order': '800.00',
        },
    ]
    for item in defaults:
        PointReward.objects.get_or_create(name=item['name'], defaults=item)


def reverse_default_rewards(apps, schema_editor):
    PointReward = apps.get_model('myapp', 'PointReward')
    names = [
        'คูปองส่วนลด 50 บาท',
        'คูปองส่วนลด 100 บาท',
        'คูปองส่วนลด 10%',
        'คูปองส่วนลด 20%',
    ]
    PointReward.objects.filter(name__in=names).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0025_pointreward_coupon_owner_pointtransaction'),
    ]

    operations = [
        migrations.RunPython(seed_default_rewards, reverse_default_rewards),
    ]
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from myapp.models import MenuItem


class StaticViewSitemap(Sitemap):
    """URL หน้าที่เป็นหน้าคงที่"""
    priority = 0.8
    changefreq = 'weekly'

    def items(self):
        return ['home', 'menu_list', 'order_list', 'contact', 'education', 'register', 'login']

    def location(self, item):
        return reverse(item)


class MenuSitemap(Sitemap):
    """URL รายละเอียดของเมนูแต่ละรายการ"""
    priority = 0.6
    changefreq = 'daily'

    def items(self):
        return MenuItem.objects.filter(available=True)

    def lastmod(self, obj):
        return obj.date_added

    def location(self, obj):
        return reverse('menu_detail', args=[obj.pk])
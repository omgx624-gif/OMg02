from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from myapp import views

from .sitemaps import MenuSitemap, StaticViewSitemap

sitemaps = {
    'static': StaticViewSitemap,
    'menus': MenuSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', include('myapp.urls')),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', views.robots_txt, name='robots_txt'),
]

# Custom error handlers
handler404 = 'myapp.views.custom_404'
handler500 = 'myapp.views.custom_500'
handler403 = 'myapp.views.custom_403'

# ให้เสิร์ฟไฟล์รูปภาพที่อัปโหลด
# - Debug: django.views.static.serve ตรงๆ
# - Production: เสิร์ฟผ่าน view เดียวกัน เพื่อให้ Docker ที่ไม่มี nginx ใช้งานได้
#   (งานขนาดใหญ่/scale สูงควรให้ nginx หรือ object storage เสิร์ฟ media แทน)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    from django.views.static import serve as static_serve

    urlpatterns += [
        path(
            f'{settings.MEDIA_URL.strip("/")}/<path:path>',
            static_serve,
            {'document_root': settings.MEDIA_ROOT},
            name='media_serve',
        ),
    ]

"""แพ็กเกจ views (แยกจากไฟล์ views.py เดิม — เนื้อหาไม่เปลี่ยน)

export ทุกชื่อเหมือนเดิมเพื่อให้ `from . import views` / `myapp.views.x`
และ handler404 = "myapp.views.custom_404" ใช้งานได้ต่อเนื่อง
"""

from ._common import *  # noqa: F401,F403

# helpers ที่ขึ้นต้น _ — export เผื่อโค้ดฝั่งอื่นเรียกผ่าน myapp.views._x
from ._common import (  # noqa: F401
    _dev_google_user,
    _google_configured,
    _google_login_active,
    _make_captcha,
    _promptpay_qr_for,
    _rider_status_counts,
    _sale_rows,
    _user_can_access_order,
)
from .core import *  # noqa: F401,F403
from .coupons import *  # noqa: F401,F403
from .dashboard import *  # noqa: F401,F403
from .delivery import *  # noqa: F401,F403
from .inventory import *  # noqa: F401,F403
from .menu import *  # noqa: F401,F403
from .orders import *  # noqa: F401,F403
from .reservations import *  # noqa: F401,F403
from .reviews import *  # noqa: F401,F403
from .users import *  # noqa: F401,F403


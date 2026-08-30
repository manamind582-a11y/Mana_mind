# -*- coding: utf-8 -*-
"""
ربات بله «کافه روانشناسی مانا مایند | دکتر ماندانا داودی»
نسخه ۴:
  - پنل ادمین کاملاً با دکمه‌های معمولی کیبورد (نه دکمه شیشه‌ای)
  - ۲ ادمین
  - جوین اجباری روی کانال تنظیم‌شده در متغیر محیطی CHANNEL_USERNAME از قبل فعاله
  - طراحی آزمون سریع‌تر: اول گزینه‌ها، بعد امتیازدهی تک‌تک با دکمه عددی

اجرا:
    pip install -r requirements.txt
    (متغیرهای محیطی لازم رو تنظیم کن — لیست کامل توی README.md)
    python mana_mind_bot.py
"""

import os
import json
import re
import time
import uuid
import requests
from datetime import datetime

# ====================================================================
# تنظیمات کلی — همه‌ی مقادیر محرمانه/اختصاصی از متغیرهای محیطی (Environment Variables) خونده می‌شن
# تا هیچ توکن یا آیدی حساسی مستقیم داخل کد نباشه. لیست کامل و نحوه‌ی تنظیمشون در README.md هست.
# ====================================================================
def _require_env(name):
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(
            f"❌ متغیر محیطی «{name}» تنظیم نشده! این متغیر برای اجرای ربات ضروریه — "
            f"توی پنل Railway (بخش Variables) اضافه‌اش کن و دوباره دیپلوی کن."
        )
    return val

TOKEN = _require_env("BALE_TOKEN")
API_URL = f"https://tapi.bale.ai/bot{TOKEN}/"
PAYMENT_PROVIDER_TOKEN = _require_env("BALE_PAYMENT_TOKEN")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_DB_PATH = os.path.join(BASE_DIR, "users_db.json")
TESTS_DB_PATH = os.path.join(BASE_DIR, "tests_db.json")
SETTINGS_PATH = os.path.join(BASE_DIR, "settings.json")
CONTENT_PATH = os.path.join(BASE_DIR, "edu_content.json")
CONSULT_PATH = os.path.join(BASE_DIR, "consultations.json")
SUPPORT_PATH = os.path.join(BASE_DIR, "support_tickets.json")
EXERCISES_PATH = os.path.join(BASE_DIR, "exercises.json")
GIFTS_PATH = os.path.join(BASE_DIR, "gifts.json")
BOOKINGS_PATH = os.path.join(BASE_DIR, "bookings.json")
PRODUCTS_PATH = os.path.join(BASE_DIR, "products.json")
ORDERS_PATH = os.path.join(BASE_DIR, "orders.json")

# همه‌ی فایل‌های JSON دیتابیس — برای بخش «اطلاعات محرمانه» توی پنل ادمین استفاده می‌شه تا لحظه‌ای ارسال بشن
ALL_DB_PATHS = [
    USERS_DB_PATH, TESTS_DB_PATH, SETTINGS_PATH, CONTENT_PATH, CONSULT_PATH,
    SUPPORT_PATH, EXERCISES_PATH, GIFTS_PATH, BOOKINGS_PATH, PRODUCTS_PATH, ORDERS_PATH,
]

# لیست آیدی عددی ادمین‌ها با کاما جدا می‌شن، مثلاً: ADMIN_IDS=324157864,532608792
ADMIN_IDS = [int(x.strip()) for x in _require_env("ADMIN_IDS").split(",") if x.strip()]
ADMIN_NAME = os.environ.get("ADMIN_NAME", "دکتر ماندانا داودی")
ADMIN_SECRET_PASSWORD = _require_env("ADMIN_SECRET_PASSWORD")  # پسورد بخش «اطلاعات محرمانه» توی پنل ادمین

CATEGORIES = {
    "personality": "🧠 شخصیت‌شناسی",
    "anxiety": "😟 اضطراب",
    "depression": "😔 افسردگی",
    "self_esteem": "💪 عزت‌نفس",
    "romantic": "❤️ روابط عاطفی",
    "family": "👨‍👩‍👧 روابط خانوادگی",
    "social": "👥 روابط اجتماعی",
    "anger": "😡 کنترل خشم",
    "sleep": "💤 خواب و آرامش",
    "students": "🎓 دانش‌آموزان و دانشجویان",
    "child_teen": "👶 کودک و نوجوان",
    "marriage": "💍 ازدواج و رابطه",
    "self_knowledge": "🧩 خودشناسی",
    "growth": "🌱 رشد فردی",
    "stress_burnout": "🔥 استرس و فرسودگی",
    "focus": "🧠 تمرکز و توجه",
}
LABEL_TO_CATEGORY = {v: k for k, v in CATEGORIES.items()}

CHANNEL_USERNAME = _require_env("CHANNEL_USERNAME").lstrip("@")   # بدون @ ذخیره می‌شه، خودمون جاهای لازم @ رو اضافه می‌کنیم
CHANNEL_LINK = _require_env("CHANNEL_LINK")
CHANNEL_TITLE = os.environ.get("CHANNEL_TITLE", "کافه روانشناسی مانا‌مایند")
CHANNEL_NUMERIC_ID_HINT = os.environ.get("CHANNEL_NUMERIC_ID", "")  # آیدی عددی خام کانال؛ چون بله معمولاً برای کانال/سوپرگروه با پیشوند -100 جواب می‌ده، چند فرمت ازش امتحان می‌شه

DEFAULT_SETTINGS = {
    "force_join": True,
    "channels": [
        {
            "id": "default1",
            "username": f"@{CHANNEL_USERNAME}",
            "chat_id": None,
            "title": CHANNEL_TITLE,
            "link": CHANNEL_LINK,
        }
    ],
    "services_text": (
        "🎁 خدمات و مزایای کافه روانشناسی مانا مایند\n\n"
        "این بخش هنوز توسط تیم مانا مایند تکمیل نشده. به‌زودی اطلاعات کامل خدمات و مزایا اینجا قرار می‌گیرد."
    ),
    "next_user_code": 1000,
    "daily_reminder_hour": 20,
    "last_reminder_date": None,
}

TERMS_TEXT = (
    "📜 قوانین و شرایط استفاده\n\n"
    "با استفاده از ربات مانا مایند، شما با موارد زیر موافقت می‌کنید:\n\n"
    "🔹 آزمون‌های این ربات صرفاً ابزار خودآگاهی و خودارزیابی هستند و جایگزین تشخیص، درمان یا "
    "مشاوره‌ی تخصصی روان‌شناسی نمی‌شوند.\n"
    "🔹 نتایج آزمون‌ها باید با دید باز و کنار توضیحات تکمیلی بررسی شوند، نه به‌عنوان حکم قطعی.\n"
    "🔹 در صورت داشتن نگرانی جدی درباره‌ی سلامت روان خود یا دیگران، حتماً با یک متخصص یا مراکز "
    "اورژانس تماس بگیرید.\n"
    "🔹 اطلاعاتی که وارد می‌کنید (مثل شماره تلفن) صرفاً برای ارتباط بهتر با شما و ارائه‌ی خدمات "
    "استفاده می‌شود.\n"
    "🔹 تیم مانا مایند حق به‌روزرسانی محتوا، آزمون‌ها و قوانین را در هر زمان دارد.\n\n"
    "برای اطلاعات بیشتر درباره‌ی نحوه‌ی استفاده از داده‌هایتان، به بخش «حریم خصوصی» مراجعه کنید."
)

PRIVACY_TEXT = (
    "🔐 حریم خصوصی\n\n"
    "📌 چه اطلاعاتی ذخیره می‌شود؟\n"
    "نام، یوزرنیم، آیدی عددی حساب شما در بله، شماره تلفن (فقط در صورت شرکت در آزمون)، و "
    "نتایج آزمون‌هایی که انجام می‌دهید.\n\n"
    "📌 این اطلاعات برای چه استفاده می‌شود؟\n"
    "فقط برای ارائه‌ی خدمات ربات (نمایش نتایج به خودتان، پیگیری درخواست مشاوره/پشتیبانی) و "
    "ارتباط تیم مانا مایند با شما در صورت نیاز.\n\n"
    "📌 اطلاعات شما با هیچ شخص یا سازمان ثالثی به اشتراک گذاشته نمی‌شود.\n\n"
    "📌 شما هر زمان می‌توانید از بخش «👤 پروفایل من» درخواست حذف کامل اطلاعات خود را ثبت کنید.\n\n"
    "📌 ما تلاش می‌کنیم فقط حداقل اطلاعات لازم را ذخیره کنیم و از نگه‌داری اطلاعات حساس غیرضروری خودداری می‌کنیم."
)

CRISIS_KEYWORDS = [
    "خودکشی", "خودکشى", "خودآسیب", "خود آسیب", "به خودم آسیب", "میخوام بمیرم", "می‌خوام بمیرم",
    "دیگه نمیخوام زندگی کنم", "دیگه نمی‌خوام زندگی کنم", "دلم میخواد بمیرم", "دلم می‌خواد بمیرم",
    "خودزنی", "دیگه نمیتونم ادامه بدم", "دیگه نمی‌تونم ادامه بدم", "میخوام به زندگیم پایان بدم",
    "خودمو بکشم", "خودمو نابود کنم",
]

CRISIS_RESOURCE_TEXT = (
    "🚨 این پیام رو با دقت خوندم و می‌خوام بدونی که تنها نیستی.\n\n"
    "اگه الان تو شرایط سختی هستی، لطفاً همین حالا با یکی از این شماره‌ها تماس بگیر:\n\n"
    "☎️ اورژانس اجتماعی: 123\n"
    "☎️ خط مشاوره سازمان بهزیستی: 1480\n"
    "☎️ اورژانس کشوری: 115\n\n"
    "صحبت با یه متخصص یا حتی یه فرد قابل‌اعتماد در اطرافت می‌تونه در همین لحظه کمک‌کننده باشه. "
    "تیم مانا مایند هم درخواستت رو دیده و در اسرع وقت پیگیری می‌کنه."
)

def contains_crisis_language(text):
    t = (text or "").lower()
    return any(kw in t for kw in CRISIS_KEYWORDS)

# ====================================================================
# ذخیره‌سازی JSON
# ====================================================================
def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_users():
    return load_json(USERS_DB_PATH, {})

def save_users(users):
    save_json(USERS_DB_PATH, users)

def load_tests():
    return load_json(TESTS_DB_PATH, {})

def save_tests(tests):
    save_json(TESTS_DB_PATH, tests)

def load_settings():
    s = load_json(SETTINGS_PATH, None)
    if s is None:
        s = json.loads(json.dumps(DEFAULT_SETTINGS))
        save_json(SETTINGS_PATH, s)
    else:
        changed = False
        for k, v in DEFAULT_SETTINGS.items():
            if k not in s:
                s[k] = v
                changed = True
        # مهاجرت: عنوان قدیمی پیش‌فرض رو به عنوان جدید تغییر می‌ده (فقط اگه ادمین خودش دستی عوضش نکرده باشه)
        for ch in s.get("channels", []):
            if ch.get("title") in ("کانال مانا مایند", "", None):
                ch["title"] = CHANNEL_TITLE
                changed = True
            # مهاجرت: لینک عضویت کانال اصلی رو با مقدار تنظیم‌شده در متغیر محیطی CHANNEL_LINK هماهنگ می‌کنه
            # (اگه قبلاً یه لینک قدیمی/اشتباه توی settings.json ذخیره شده باشه)
            username = (ch.get("username") or "").lstrip("@").lower()
            if username == CHANNEL_USERNAME.lower() and ch.get("link") != CHANNEL_LINK:
                ch["link"] = CHANNEL_LINK
                changed = True
        if changed:
            save_json(SETTINGS_PATH, s)
    return s

def save_settings(s):
    save_json(SETTINGS_PATH, s)

def load_content():
    return load_json(CONTENT_PATH, {})

def save_content(c):
    save_json(CONTENT_PATH, c)

def load_consultations():
    return load_json(CONSULT_PATH, {})

def save_consultations(c):
    save_json(CONSULT_PATH, c)

def load_support():
    return load_json(SUPPORT_PATH, {})

def save_support(s):
    save_json(SUPPORT_PATH, s)

def load_exercises():
    return load_json(EXERCISES_PATH, {})

def save_exercises(e):
    save_json(EXERCISES_PATH, e)

def load_gifts():
    return load_json(GIFTS_PATH, {})

def save_gifts(g):
    save_json(GIFTS_PATH, g)

def load_bookings():
    return load_json(BOOKINGS_PATH, {})

def save_bookings(b):
    save_json(BOOKINGS_PATH, b)

def load_products():
    products = load_json(PRODUCTS_PATH, {})
    changed = False
    for p in products.values():
        if "price_toman" not in p:
            # مهاجرت از فرمت قدیمی که قیمت متن آزاد بود (مثلاً "۱۵۰,۰۰۰ تومان")
            old_price = p.pop("price", "")
            digits = "".join(ch for ch in str(old_price) if ch.isdigit())
            p["price_toman"] = int(digits) if digits else 0
            changed = True
        if "delivery_content" not in p:
            p["delivery_content"] = p.get("description", "")
            changed = True
        if "photo" not in p:
            p["photo"] = None
            changed = True
    if changed:
        save_json(PRODUCTS_PATH, products)
    return products

def save_products(p):
    save_json(PRODUCTS_PATH, p)

def load_orders():
    orders = load_json(ORDERS_PATH, {})
    changed = False
    for o in orders.values():
        if "price_toman" not in o:
            old_price = o.pop("price", "")
            digits = "".join(ch for ch in str(old_price) if ch.isdigit())
            o["price_toman"] = int(digits) if digits else 0
            changed = True
    if changed:
        save_json(ORDERS_PATH, orders)
    return orders

def save_orders(o):
    save_json(ORDERS_PATH, o)

DEFAULT_USER_FIELDS = {
    "results": [],
    "saved_tests": [],
    "in_progress": {},
    "phone": None,
    "user_code": None,
    "mood_log": {},
    "daily_reminder": False,
    "exercise_log": {},
    "last_seen": None,
    "join_gate_passed": False,
    "state": {"mode": None, "data": {}},
    "admin_state": {"mode": None, "menu": None, "data": {}},
}

def next_user_code():
    settings = load_settings()
    code = settings.get("next_user_code", 1000)
    settings["next_user_code"] = code + 1
    save_settings(settings)
    return f"MM-{code}"

def get_or_create_user(user):
    users = load_users()
    uid = str(user.get("id"))
    if uid not in users:
        users[uid] = {
            "id": uid,
            "first_name": user.get("first_name", ""),
            "last_name": user.get("last_name", ""),
            "username": user.get("username", ""),
            "joined_at": now_str(),
        }
        for k, v in DEFAULT_USER_FIELDS.items():
            users[uid][k] = json.loads(json.dumps(v))
        users[uid]["user_code"] = next_user_code()
        save_users(users)
    else:
        changed = False
        for k, v in DEFAULT_USER_FIELDS.items():
            if k not in users[uid]:
                users[uid][k] = json.loads(json.dumps(v))
                changed = True
        if "admin_state" in users[uid] and "menu" not in users[uid]["admin_state"]:
            users[uid]["admin_state"]["menu"] = None
            changed = True
        if not users[uid].get("user_code"):
            users[uid]["user_code"] = next_user_code()
            changed = True
        if user.get("first_name") and users[uid].get("first_name") != user.get("first_name"):
            users[uid]["first_name"] = user.get("first_name")
            changed = True
        if changed:
            save_users(users)
    return users[uid]

def update_user(uid, user_obj):
    users = load_users()
    users[str(uid)] = user_obj
    save_users(users)

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M")

# ====================================================================
# ارتباط با API بله
# ====================================================================
def api_call(method, payload=None, timeout=20):
    try:
        resp = requests.post(API_URL + method, json=payload, timeout=timeout)
        return resp.json()
    except Exception as e:
        print(f"[api_call error] {method}: {e}")
        return None

def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return api_call("sendMessage", payload)

def copy_message(to_chat_id, from_chat_id, message_id, reply_markup=None):
    payload = {"chat_id": to_chat_id, "from_chat_id": from_chat_id, "message_id": message_id}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return api_call("copyMessage", payload)

def send_photo(chat_id, photo, caption=None, reply_markup=None):
    payload = {"chat_id": chat_id, "photo": photo}
    if caption:
        payload["caption"] = caption
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return api_call("sendPhoto", payload)

def send_document(chat_id, file_path, caption=None):
    """یه فایل رو مستقیم از روی دیسک به‌عنوان سند (Document) آپلود و ارسال می‌کنه (برخلاف بقیه‌ی api_call ها
    که JSON می‌فرستن، اینجا باید multipart/form-data باشه چون بایت‌های فایل رو آپلود می‌کنیم)."""
    try:
        with open(file_path, "rb") as f:
            data = {"chat_id": chat_id}
            if caption:
                data["caption"] = caption
            files = {"document": (os.path.basename(file_path), f)}
            resp = requests.post(API_URL + "sendDocument", data=data, files=files, timeout=60)
            return resp.json()
    except Exception as e:
        print(f"[send_document error] {file_path}: {e}")
        return None

def send_all_json_backups(chat_id):
    """همه‌ی فایل‌های JSON دیتابیس رو که همین الان (لحظه‌ای) روی دیسک هستن، فقط برای همون چت (ادمینی که
    پسورد رو درست وارد کرده) می‌فرسته — نه برای بقیه‌ی ادمین‌ها."""
    sent, missing = 0, 0
    for path in ALL_DB_PATHS:
        if not os.path.exists(path):
            missing += 1
            continue
        result = send_document(chat_id, path)
        if result and result.get("ok"):
            sent += 1
        else:
            print(f"[confidential-backup] ارسال {path} ناموفق بود: {result}")
    send_message(
        chat_id,
        f"✅ {sent} فایل دیتابیس (لحظه‌ای) ارسال شد." if sent else "⚠️ هیچ فایل دیتابیسی روی سرور پیدا نشد.",
    )

def send_invoice(chat_id, title, description, payload, price_toman, photo_url=None):
    """صورتحساب پرداخت واقعی از طریق کیف پول بله می‌فرسته. قیمت‌ها باید به ریال باشن (تومان × ۱۰)."""
    price_rial = int(price_toman) * 10
    body = {
        "chat_id": chat_id,
        "title": title,
        "description": description,
        "payload": payload,
        "provider_token": PAYMENT_PROVIDER_TOKEN,
        "prices": [{"label": title, "amount": price_rial}],
    }
    if photo_url:
        body["photo_url"] = photo_url
    return api_call("sendInvoice", body)

def handle_pre_checkout_query(pcq):
    """قبل از تکمیل پرداخت باید تأیید بدیم، وگرنه پرداخت ناموفق می‌مونه."""
    api_call("answerPreCheckoutQuery", {"pre_checkout_query_id": pcq["id"], "ok": True})

MEDIA_KEYS = ("photo", "voice", "document", "video", "audio", "animation", "sticker")

def message_has_media(message):
    return any(k in message for k in MEDIA_KEYS)

def relay_content(to_chat_id, message, text_prefix=None):
    """پیام (متنی یا رسانه‌ای از هر نوع) رو به یه چت دیگه منتقل می‌کنه."""
    if message_has_media(message):
        if text_prefix:
            send_message(to_chat_id, text_prefix)
        return copy_message(to_chat_id, message["chat"]["id"], message["message_id"])
    text = message.get("text", "")
    full = f"{text_prefix}\n{text}" if text_prefix else text
    return send_message(to_chat_id, full)

def edit_message(chat_id, message_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    result = api_call("editMessageText", payload)
    if not result or not result.get("ok"):
        send_message(chat_id, text, reply_markup)

def answer_callback(callback_id, text=None, show_alert=False):
    payload = {"callback_query_id": callback_id}
    if text:
        payload["text"] = text
        payload["show_alert"] = show_alert
    api_call("answerCallbackQuery", payload)

def get_chat_member(chat_id, user_id):
    return api_call("getChatMember", {"chat_id": chat_id, "user_id": user_id})

def get_chat(chat_id):
    return api_call("getChat", {"chat_id": chat_id})

def get_updates(offset=None, timeout=25):
    payload = {"timeout": timeout}
    if offset is not None:
        payload["offset"] = offset
    result = api_call("getUpdates", payload, timeout=timeout + 15)
    if result and result.get("ok"):
        return result.get("result", [])
    return []

# ====================================================================
# جوین اجباری
# ====================================================================
def is_admin(uid):
    try:
        if int(uid) in ADMIN_IDS:
            return True
    except (TypeError, ValueError):
        pass
    return str(uid) in [str(a) for a in ADMIN_IDS]

def channel_identifier(ch):
    """بله گاهی نمی‌تونه کانال رو با یوزرنیم @ پیدا کنه؛ اگه آیدی عددی واقعی کانال رو قبلاً گرفته باشیم، همونو ترجیح می‌دیم."""
    return ch.get("chat_id") or ch["username"]

def capture_channel_numeric_id(chat):
    """وقتی یه پست از کانال می‌رسه یا کاربری پیامی از کانال فوروارد می‌کنه، آیدی عددی واقعی کانال رو می‌گیریم و ذخیره
    می‌کنیم — چون گاهی چک کردن با یوزرنیم @ با خطای 404 مواجه می‌شه ولی با آیدی عددی درست کار می‌کنه.
    خروجی: دیکشنری کانالی که پیدا و به‌روزرسانی شد، یا None."""
    username = chat.get("username")
    chat_id = chat.get("id")
    if not username or not chat_id:
        return None
    settings = load_settings()
    matched = None
    for ch in settings.get("channels", []):
        stored = ch.get("username", "").lstrip("@").lower()
        if stored == username.lower():
            matched = ch
            if ch.get("chat_id") != chat_id:
                ch["chat_id"] = chat_id
                print(f"[join-gate] آیدی عددی کانال @{username} پیدا شد: {chat_id}")
                save_settings(settings)
    return matched

def _candidate_identifiers(ch):
    """چند فرمت مختلف برای شناسه‌ی یک کانال می‌سازه تا امتحان بشه: اول آیدی عددی کش‌شده (سریع‌ترین حالت)،
    بعد (اگه این همون کانال اصلیه) فرمت‌های مختلف آیدی عددی خام، و در آخر یوزرنیم."""
    seen = set()
    out = []
    def add(x):
        if x not in (None, "") and str(x) not in seen:
            seen.add(str(x))
            out.append(x)

    add(ch.get("chat_id"))

    username = (ch.get("username") or "").lstrip("@").lower()
    if username == CHANNEL_USERNAME.lower() and CHANNEL_NUMERIC_ID_HINT:
        raw = CHANNEL_NUMERIC_ID_HINT
        add(f"-100{raw}")   # فرمت رایج بله/تلگرام برای کانال و سوپرگروه
        add(f"-{raw}")
        add(raw)

    add(ch.get("username"))
    return out

def probe_channel_membership(ch, uid):
    """عضویت کاربر رو با امتحان کردن فرمت‌های مختلف شناسه‌ی کانال چک می‌کنه.
    خروجی: (is_member, determined, working_identifier)
    - determined=False یعنی هیچ‌کدوم از شناسه‌ها جواب ندادن (مثلاً ربات ادمین کانال نیست)."""
    for identifier in _candidate_identifiers(ch):
        result = get_chat_member(identifier, uid)
        if result and result.get("ok"):
            status = result.get("result", {}).get("status", "")
            is_member = status in ("member", "administrator", "creator")
            return is_member, True, identifier
        err = (result or {}).get("description", "بدون پاسخ") if result else "بدون پاسخ"
        print(f"[join-gate] getChatMember با identifier={identifier} برای uid={uid} ناموفق بود: {err}")
    return False, False, None

def user_is_member_everywhere(uid):
    """درست مثل منطق کد فروش ممبر: فقط عضو/ادمین/سازنده = عضو حساب می‌شه؛ هر وضعیت دیگه یا هر خطایی
    یعنی کاربر رد نمی‌شه (به جای رد شدن پیش‌فرض قبلی که وقتی چک با خطا مواجه می‌شد، عبور می‌داد)."""
    settings = load_settings()
    if not settings.get("force_join") or not settings.get("channels"):
        return True

    changed = False
    all_member = True
    for ch in settings["channels"]:
        is_member, determined, working_identifier = probe_channel_membership(ch, uid)
        if working_identifier is not None and working_identifier != ch.get("chat_id"):
            ch["chat_id"] = working_identifier
            changed = True
        if not determined or not is_member:
            all_member = False
            break

    if changed:
        save_settings(settings)
    return all_member

def diagnose_join_channels(admin_uid):
    """برای هر کانال تنظیم‌شده، هم با یوزرنیم و هم با آیدی عددی (اگه داشته باشه) تست می‌کنه تا دقیقاً مشخص بشه مشکل کجاست."""
    settings = load_settings()
    channels = settings.get("channels", [])
    if not channels:
        return "⚠️ هیچ کانالی برای جوین اجباری تنظیم نشده."
    lines = ["🧪 نتیجه تست اتصال به کانال‌ها:\n"]
    for ch in channels:
        lines.append(f"📌 {ch['title']}")

        # تست با getChat (مستقل از عضویت کاربر - فقط می‌گه آیا ربات اصلاً این چت رو می‌شناسه)
        for label, identifier in [("یوزرنیم " + ch["username"], ch["username"])] + (
            [("آیدی عددی " + str(ch["chat_id"]), ch["chat_id"])] if ch.get("chat_id") else []
        ):
            chat_result = get_chat(identifier)
            if chat_result and chat_result.get("ok"):
                lines.append(f"  ✅ getChat با {label}: موفق — ربات این چت رو می‌شناسه.")
            else:
                err = (chat_result or {}).get("description", "بدون پاسخ")
                lines.append(f"  ❌ getChat با {label}: ناموفق — {err}")

            member_result = get_chat_member(identifier, admin_uid)
            if member_result and member_result.get("ok"):
                status = member_result.get("result", {}).get("status", "نامشخص")
                lines.append(f"  ✅ getChatMember با {label}: موفق — وضعیت شما: {status}")
            else:
                err = (member_result or {}).get("description", "بدون پاسخ")
                lines.append(f"  ❌ getChatMember با {label}: ناموفق — {err}")
        lines.append("")

    lines.append(
        "ℹ️ اگه همه‌ی موارد بالا ❌ هستن، مطمئن‌ترین راه‌حل اینه: یه پیام از همون کانال رو "
        "مستقیم برای همین ربات فوروارد کن (نه کپی، فوروارد واقعی) — ربات خودش آیدی درست رو پیدا و جایگزین می‌کنه."
    )
    return "\n".join(lines)

def send_join_gate(chat_id):
    settings = load_settings()
    text = (
        "🔒 برای استفاده از ربات مانا مایند، ابتدا باید عضو کانال زیر بشید:\n\n"
        "بعد از عضویت، دکمه‌ی «✅ عضو شدم» رو بزنید تا عضویتتون تأیید بشه."
    )
    kb = {"inline_keyboard": []}
    for ch in settings.get("channels", []):
        kb["inline_keyboard"].append([{"text": ch["title"], "url": ch["link"]}])
    kb["inline_keyboard"].append([{"text": "✅ عضو شدم", "callback_data": "check_join"}])
    send_message(chat_id, text, kb)

def ensure_joined_or_gate(uid, chat_id, user):
    """اگه ادمینه یا عضو کانال‌هاست، اجازه میده و پرچم عبور از گیت رو ثبت می‌کنه؛ وگرنه گیت رو نشون میده و False برمی‌گردونه."""
    if is_admin(uid):
        return True
    if user_is_member_everywhere(uid):
        if not user.get("join_gate_passed"):
            user["join_gate_passed"] = True
            update_user(uid, user)
        return True
    send_join_gate(chat_id)
    return False

# ====================================================================
# کیبوردهای عمومی
# ====================================================================
MAIN_MENU_BUTTONS = [
    ["🧠 آزمون‌های روان‌شناسی", "📋 آزمون‌های من"],
    ["📊 نتایج و نمرات من", "👤 پروفایل من"],
    ["💬 درخواست مشاوره", "🎁 خدمات و مزایا"],
    ["📚 محتوای آموزشی", "🆘 پشتیبانی"],
    ["ℹ️ درباره دکتر ماندانا داودی", "📢 ورود به کانال مانا مایند"],
    ["🌱 حال من امروز چطوره؟", "📜 قوانین و حریم خصوصی"],
    ["💭 مشکل من چیست؟", "📝 تمرین‌های روان‌شناختی"],
]

def main_menu_keyboard():
    return {"keyboard": MAIN_MENU_BUTTONS, "resize_keyboard": True, "one_time_keyboard": False}

def inline_kb(rows):
    return {"inline_keyboard": [[{"text": t, "callback_data": d} for t, d in row] for row in rows]}

def inline_kb_urlaware(rows):
    """مثل inline_kb ولی هر آیتم می‌تونه (text, callback_data) یا (text, url, 'url') باشه."""
    out_rows = []
    for row in rows:
        out_row = []
        for item in row:
            if len(item) == 3 and item[2] == "url":
                out_row.append({"text": item[0], "url": item[1]})
            else:
                out_row.append({"text": item[0], "callback_data": item[1]})
        out_rows.append(out_row)
    return {"inline_keyboard": out_rows}

def reply_kb(rows):
    return {"keyboard": rows, "resize_keyboard": True, "one_time_keyboard": False}

def back_kb():
    return reply_kb([["↩️ بازگشت"]])

def remove_kb():
    return {"remove_keyboard": True}

def contact_request_kb():
    return {
        "keyboard": [
            [{"text": "📱 ارسال شماره تلفن من", "request_contact": True}],
            [{"text": "↩️ بازگشت"}],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True,
    }

def is_main_menu_button_text(text):
    """چک می‌کنه که آیا این متن دقیقاً یکی از دکمه‌های کیبورد اصلیه (یعنی کاربر داشته دکمه می‌زده، نه پیام آزاد می‌نوشته)."""
    return any(text == label for row in MAIN_MENU_BUTTONS for label in row)

def end_chat_kb():
    return reply_kb([["🔚 پایان گفتگو"]])

def star_rating_kb(kind, rec_id):
    return inline_kb([[
        (f"⭐{i}", f"rate:{kind}:{rec_id}:{i}") for i in range(1, 6)
    ]])

# ====================================================================
# متن‌های ثابت
# ====================================================================
WELCOME_TEXT = (
    "🌿 سلام {name} عزیز!\n\n"
    "به «کافه روانشناسی مانا مایند» خوش اومدی 🌸\n"
    "اینجا می‌تونی آزمون‌های روان‌شناسی بدی، نتایج و پیشرفتت رو ببینی، "
    "درخواست مشاوره ثبت کنی و به محتوای آموزشی دسترسی داشته باشی.\n\n"
    "یکی از گزینه‌های زیر رو انتخاب کن 👇"
)
ABOUT_TEXT = (
    "👩‍⚕️ درباره دکتر ماندانا داودی\n\n"
    "دکتر ماندانا داودی، دکترای روان‌شناسی، روان‌درمانگر و مدرس دانشگاه است که در حوزه‌های "
    "روان‌شناسی، خانواده، کودک و آسیب‌های اجتماعی فعالیت حرفه‌ای دارد.\n\n"
    "🔹 همکاری با سازمان بهزیستی و اورژانس اجتماعی و ارائه خدمات مددکاری به گروه‌های مختلف، "
    "از جمله افراد دارای معلولیت جسمی و حرکتی و زنان خودسرپرست.\n\n"
    "🔹 فعالیت به‌عنوان معتمد در پرونده‌های بررسی و حل اختلاف زوجین و همچنین پرونده‌های مربوط "
    "به ملاقات کودکان طلاق در شهرستان.\n\n"
    "🔹 مدرس و برگزارکننده کارگاه‌های آموزشی برای دانشگاه‌ها، ادارات و سازمان‌های مختلف از جمله "
    "آموزش‌وپرورش، اداره برق، آبفا، تأمین اجتماعی، بهزیستی، دانشگاه علوم دریایی، بسیج و سایر مجموعه‌ها.\n\n"
    "🔹 مدرس وبینارهای تخصصی و آموزشی در زمینه خانواده، کودک و موضوعات مرتبط با سلامت روان.\n\n"
    "هدف دکتر ماندانا داودی، ارائه دانش و تجربه تخصصی در فضایی علمی، قابل اعتماد و کاربردی و کمک "
    "به افراد برای شناخت بهتر خود، بهبود روابط و ارتقای کیفیت زندگی است.\n\n"
    "🌱 مانا مایند نیز با تکیه بر همین تجربه و دانش شکل گرفته تا بستری برای آموزش، خودشناسی، "
    "آگاهی و ارتباط با دکتر ماندانا داودی باشد.\n\n"
    "📱 کانال مانا مایند: @{channel}"
).replace("{channel}", CHANNEL_USERNAME)
TESTS_HOME_TEXT = (
    "🧠 به بخش آزمون‌های روان‌شناسی مانا مایند خوش آمدید.\n"
    "در این بخش می‌توانید در آزمون‌های مختلف شرکت کنید و پس از پایان، "
    "نتیجه و تحلیل آزمون خود را دریافت کنید."
)
DISCLAIMER = "⚠️ نتیجه آزمون صرفاً برای خودارزیابی است و جایگزین ارزیابی تخصصی توسط روان‌شناس نیست."

def channel_entry_text():
    settings = load_settings()
    if settings.get("channels"):
        return settings["channels"][0]["link"]
    return "لینک کانال هنوز توسط ادمین تنظیم نشده است."

def option_number_label(n):
    keycaps = {1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣", 7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟"}
    return keycaps.get(n, str(n) + "⃣" if n < 100 else str(n))

NEUTRAL_SCORE_NOTE = (
    "📌 نکته: نمره بالا لزوماً به معنای «عملکرد خوب» نیست و نمره پایین هم لزوماً به معنای «عملکرد بد» نیست — "
    "این کاملاً به نوع و هدف آزمون بستگی دارد. بر اساس متن نتیجه و تحلیلی که در ادامه آمده، می‌توانید عملکرد "
    "خودتان را به‌درستی ارزیابی کنید."
)

def compute_display_score(test, raw_total, raw_max):
    """نمره همیشه خام و بر اساس مجموع امتیازهای گزینه‌های انتخاب‌شده است (بدون تبدیل به درصد)."""
    label = f"{raw_total} از {raw_max}"
    return label, raw_total, raw_total

def result_score_label(r):
    return r.get("display_label") or f"{r.get('score', 0)} از {r.get('max_score', 0)}"

def find_range_text(test, display_value):
    for r in test.get("ranges", []):
        try:
            if r["min"] <= display_value <= r["max"]:
                return r["text"]
        except (TypeError, KeyError):
            continue
    return None

def show_legal_home(chat_id, message_id=None):
    text = "📜 قوانین و حریم خصوصی\n\nیکی از گزینه‌های زیر را انتخاب کنید:"
    kb = inline_kb([
        [("📜 قوانین و شرایط استفاده", "show_terms")],
        [("🔐 حریم خصوصی", "show_privacy")],
        [("🏠 بازگشت به منوی اصلی", "back_main_menu")],
    ])
    if message_id:
        edit_message(chat_id, message_id, text, kb)
    else:
        send_message(chat_id, text, kb)

MOOD_MESSAGES = {
    range(1, 4): "🤍 می‌دونم روزهای سختی مثل امروز واقعاً سنگینن. یادت باشه حالت گفتنش خودش یه قدم مهمه. اگه دوست داری، می‌تونی از منوی «💬 درخواست مشاوره» با تیم مانا مایند در ارتباط باشی.",
    range(4, 7): "🌿 روز متعادلی داشتی. گاهی همینم کافیه. مراقب خودت باش.",
    range(7, 11): "🌞 خوشحالیم که امروز حالت خوب بوده! این حس رو با خودت نگه دار.",
}

def mood_feedback(score):
    for rng, msg in MOOD_MESSAGES.items():
        if score in rng:
            return msg
    return "ممنون که حالت رو ثبت کردی."

def show_mood_checkin(chat_id, user):
    today = datetime.now().strftime("%Y-%m-%d")
    existing = user.get("mood_log", {}).get(today)
    if existing is not None:
        text = f"🌱 امروز حالت رو قبلاً {existing} از ۱۰ ثبت کردی.\n\n{mood_feedback(existing)}"
        kb = inline_kb([
            [("📈 روند حال من", "mood_trend")],
            [("🔔 یادآوری روزانه: " + ("فعال ✅" if user.get("daily_reminder") else "غیرفعال ❌"),
              "mood_reminder_off" if user.get("daily_reminder") else "mood_reminder_on")],
        ])
        send_message(chat_id, text, kb)
        return
    rows = [[(str(n), f"mood:{n}") for n in range(start, start + 5)] for start in (1, 6)]
    send_message(chat_id, "🌱 امروز حالت رو از ۱ (خیلی بد) تا ۱۰ (خیلی خوب) چند می‌دی؟", inline_kb(rows))

def handle_mood_selection(uid, chat_id, message_id, data_cb):
    score = int(data_cb.split(":", 1)[1])
    today = datetime.now().strftime("%Y-%m-%d")
    users = load_users()
    user = users[str(uid)]
    user.setdefault("mood_log", {})[today] = score
    save_users(users)
    text = f"✅ ثبت شد: امروز {score} از ۱۰\n\n{mood_feedback(score)}"
    kb = inline_kb([
        [("📈 روند حال من", "mood_trend")],
        [("🔔 یادآوری روزانه: " + ("فعال ✅" if user.get("daily_reminder") else "غیرفعال ❌"),
          "mood_reminder_off" if user.get("daily_reminder") else "mood_reminder_on")],
    ])
    if score <= 3:
        send_message(chat_id, CRISIS_RESOURCE_TEXT)
    edit_message(chat_id, message_id, text, kb)

def show_mood_trend(chat_id, message_id, user):
    log = user.get("mood_log", {})
    if not log:
        edit_message(chat_id, message_id, "هنوز حالی ثبت نکردی.", inline_kb([[("🏠 بازگشت", "back_main_menu")]]))
        return
    last_days = sorted(log.items())[-10:]
    lines = ["📈 روند حال شما در روزهای اخیر:\n"]
    for date, score in last_days:
        bar = "🟩" * score + "⬜" * (10 - score)
        lines.append(f"{date}: {bar} ({score}/10)")
    edit_message(chat_id, message_id, "\n".join(lines), inline_kb([[("🏠 بازگشت به منوی اصلی", "back_main_menu")]]))

def build_profile_text(user):
    results = user.get("results", [])
    tests_count = len(results)
    exercises_done = sum(len(v) for v in user.get("exercise_log", {}).values())
    phone = user.get("phone") or "ثبت نشده ❗️"
    text = (
        "👤 ✨ پروفایل من ✨\n"
        "━━━━━━━━━━━━━━\n"
        f"🙍 نام: {user.get('first_name', '')} {user.get('last_name', '')}\n"
        f"🌐 یوزرنیم: {('@' + user.get('username')) if user.get('username') else 'ثبت نشده'}\n"
        f"🆔 کد کاربری: {user.get('user_code') or '-'}\n"
        f"📱 شماره تلفن: {phone}\n"
        f"📅 تاریخ عضویت: {user.get('joined_at', '')}\n"
        "━━━━━━━━━━━━━━\n"
        f"📝 تعداد آزمون‌های تکمیل‌شده: {tests_count}\n"
        f"🔥 تعداد تمرین‌های انجام‌شده: {exercises_done}\n"
        f"⭐ آزمون‌های ذخیره‌شده: {len(user.get('saved_tests', []))}\n"
        f"🏅 امتیاز مشارکت: {tests_count * 10}\n"
    )
    return text

# ====================================================================
# بخش «آزمون‌های روان‌شناسی» (کاربر عادی - دکمه شیشه‌ای، بدون تغییر)
# ====================================================================
def show_tests_home(chat_id, message_id=None):
    kb = inline_kb([
        [("📋 همه آزمون‌ها", "tests_all")],
        [("📁 دسته‌بندی‌ها", "tests_categories")],
        [("⭐ آزمون‌های ذخیره‌شده", "tests_saved"), ("🔍 جستجوی آزمون", "tests_search")],
        [("↩️ بازگشت به منوی اصلی", "back_main_menu")],
    ])
    if message_id:
        edit_message(chat_id, message_id, TESTS_HOME_TEXT, kb)
    else:
        send_message(chat_id, TESTS_HOME_TEXT, kb)

def render_test_list(chat_id, message_id, tests_list, title, back_cb="tests_all"):
    if not tests_list:
        edit_message(chat_id, message_id, "چیزی برای نمایش پیدا نشد.", inline_kb([[("↩️ بازگشت", back_cb)]]))
        return
    rows = [[(t["title"], f"test:{t['id']}")] for t in tests_list]
    rows.append([("↩️ بازگشت", back_cb)])
    edit_message(chat_id, message_id, title, inline_kb(rows))

def show_categories(chat_id, message_id):
    items = list(CATEGORIES.items())
    rows = []
    for i in range(0, len(items), 2):
        row = [(items[i][1], f"cat:{items[i][0]}")]
        if i + 1 < len(items):
            row.append((items[i + 1][1], f"cat:{items[i + 1][0]}"))
        rows.append(row)
    rows.append([("↩️ بازگشت", "tests_home")])
    edit_message(chat_id, message_id, "📋 لطفاً یک دسته‌بندی را انتخاب کنید:", inline_kb(rows))

def user_has_taken(user, test_id):
    return any(r["test_id"] == test_id for r in user.get("results", []))

def show_test_detail(chat_id, message_id, test_id, user=None):
    tests = load_tests()
    test = tests.get(test_id)
    if not test:
        edit_message(chat_id, message_id, "این آزمون دیگر موجود نیست.", inline_kb([[("↩️ بازگشت", "tests_home")]]))
        return
    already_done = user is not None and user_has_taken(user, test_id)
    text = (
        f"🧠 {test['title']}\n\n"
        f"{test['description']}\n\n"
        f"📝 تعداد سؤالات: {len(test['questions'])}\n"
        f"⏱ زمان تقریبی: {test.get('time_minutes', '-')} دقیقه\n"
        f"🎯 نوع: خودارزیابی\n\n"
        f"{DISCLAIMER}"
    )
    if already_done:
        text += "\n\n✅ شما قبلاً این آزمون را انجام داده‌اید. امکان تکرار این آزمون وجود ندارد."
        rows = [[("📊 مشاهده نتیجه قبلی", "tests_results")]]
        if test.get("related_post_link"):
            rows.append([("📖 مطالعه بیشتر", test["related_post_link"], "url")])
        rows.append([("↩️ بازگشت", "tests_home")])
    else:
        rows = [
            [("▶️ شروع آزمون", f"start_test:{test_id}")],
            [("ℹ️ راهنمای آزمون", f"guide:{test_id}"), ("⭐ ذخیره", f"save_test:{test_id}")],
        ]
        if test.get("related_post_link"):
            rows.append([("📖 مطالعه بیشتر", test["related_post_link"], "url")])
        rows.append([("↩️ بازگشت", "tests_home")])
    edit_message(chat_id, message_id, text, inline_kb_urlaware(rows))

def send_question(chat_id, uid, test_id, message_id=None):
    users = load_users()
    user = users[str(uid)]
    tests = load_tests()
    test = tests.get(test_id)
    if not test:
        return
    progress = user["in_progress"].get(test_id)
    if not progress:
        return
    idx = progress["index"]
    questions = test["questions"]
    if idx >= len(questions):
        show_finish_confirm(chat_id, uid, test_id, message_id)
        return
    q = questions[idx]
    text = f"سؤال {idx + 1} از {len(questions)}\n\n{q['text']}\n\n"
    for oi, opt in enumerate(q["options"]):
        text += f"{option_number_label(oi + 1)} {opt['text']}\n"

    answered_idx = progress["answers"].get(str(idx))
    if answered_idx is not None:
        text += f"\n✅ پاسخ فعلی شما: گزینه {int(answered_idx) + 1}"

    option_buttons = [(option_number_label(oi + 1), f"answer:{test_id}:{idx}:{oi}") for oi in range(len(q["options"]))]
    rows = [option_buttons[i:i + 4] for i in range(0, len(option_buttons), 4)]

    nav_row = []
    if idx > 0:
        nav_row.append(("⬅️ سؤال قبلی", f"prevq:{test_id}"))
    if str(idx) in progress["answers"]:
        nav_row.append(("سؤال بعدی ➡️", f"nextq:{test_id}"))
    if nav_row:
        rows.append(nav_row)
    rows.append([("❌ لغو آزمون", f"canceltest:{test_id}")])
    if message_id:
        edit_message(chat_id, message_id, text, inline_kb(rows))
    else:
        send_message(chat_id, text, inline_kb(rows))

def show_finish_confirm(chat_id, uid, test_id, message_id=None):
    users = load_users()
    user = users[str(uid)]
    tests = load_tests()
    test = tests.get(test_id)
    progress = user["in_progress"].get(test_id)
    if not test or not progress:
        return
    total_q = len(test["questions"])
    answered = len(progress["answers"])
    empty = total_q - answered
    text = f"📝 وضعیت پاسخ‌های شما در «{test['title']}»:\n\n✅ پاسخ داده‌شده: {answered}\n❌ بدون پاسخ: {empty}\n"
    rows = []
    if empty > 0:
        text += "\n⚠️ سؤال‌های بدون پاسخ، امتیاز صفر می‌گیرند. مطمئنید می‌خواهید همینطور ثبت کنید؟"
        rows.append([("🔁 بازگشت و تکمیل پاسخ‌ها", f"gotoempty:{test_id}")])
    else:
        text += "\n🎉 همه سؤالات پاسخ داده شده."
    rows.append([("✅ ثبت نهایی نتیجه", f"submit_test:{test_id}")])
    rows.append([("⬅️ سؤال قبلی", f"prevq:{test_id}")])
    if message_id:
        edit_message(chat_id, message_id, text, inline_kb(rows))
    else:
        send_message(chat_id, text, inline_kb(rows))

def goto_first_empty_question(chat_id, uid, test_id, message_id=None):
    users = load_users()
    user = users[str(uid)]
    tests = load_tests()
    test = tests.get(test_id)
    progress = user["in_progress"].get(test_id)
    if not test or not progress:
        return
    for qi in range(len(test["questions"])):
        if str(qi) not in progress["answers"]:
            progress["index"] = qi
            update_user(uid, user)
            break
    else:
        progress["index"] = 0
        update_user(uid, user)
    send_question(chat_id, uid, test_id, message_id)

def finish_test(chat_id, uid, test_id, message_id=None):
    users = load_users()
    user = users[str(uid)]
    tests = load_tests()
    test = tests.get(test_id)
    progress = user["in_progress"].get(test_id)
    if not test or not progress:
        return
    questions = test["questions"]
    total = 0
    max_score = 0
    subscale_totals = {}  # name -> {"score": x, "max": y}
    for qi, q in enumerate(questions):
        opts = q["options"]
        q_max = max(o["score"] for o in opts)
        max_score += q_max
        ans = progress["answers"].get(str(qi))
        q_score = opts[int(ans)]["score"] if ans is not None else 0
        if ans is not None:
            total += q_score
        subscale = q.get("subscale")
        if subscale:
            st = subscale_totals.setdefault(subscale, {"score": 0, "max": 0})
            st["score"] += q_score
            st["max"] += q_max
    display_label, display_value, _ = compute_display_score(test, total, max_score)

    subscales_result = {}
    for name, st in subscale_totals.items():
        subscales_result[name] = {"score": st["score"], "max": st["max"], "label": f"{st['score']} از {st['max']}"}

    result = {
        "id": str(uuid.uuid4())[:8],
        "test_id": test_id,
        "test_title": test["title"],
        "score": total,
        "max_score": max_score,
        "display_label": display_label,
        "display_value": display_value,
        "answers": progress["answers"],
        "subscales": subscales_result,
        "date": now_str(),
    }
    user["results"].append(result)
    del user["in_progress"][test_id]
    update_user(uid, user)

    test["participation_count"] = test.get("participation_count", 0) + 1
    tests[test_id] = test
    save_tests(tests)

    range_text = find_range_text(test, display_value)
    range_block = f"\n\n📝 {range_text}" if range_text else ""

    subscale_block = ""
    if subscales_result:
        lines = [f"  • {name}: {info['label']}" for name, info in subscales_result.items()]
        subscale_block = "\n\n🧩 نتیجه به تفکیک خرده‌مقیاس:\n" + "\n".join(lines)

    text = (
        "🎉 آزمون شما با موفقیت ثبت شد.\n\n"
        f"📊 نتیجه آزمون «{test['title']}»\n\n"
        f"نمره: {display_label}\n"
        f"تاریخ انجام: {result['date']}\n\n"
        f"{NEUTRAL_SCORE_NOTE}\n\n"
        f"{DISCLAIMER}"
        f"{range_block}"
        f"{subscale_block}"
    )
    kb_rows = [
        [("📊 مشاهده تحلیل کامل", f"view_analysis:{result['id']}")],
        [("📋 مشاهده پاسخ‌های من", f"view_answers:{result['id']}")],
    ]
    if test.get("related_post_link"):
        kb_rows.append([("📖 مطالعه بیشتر", test["related_post_link"], "url")])
    kb_rows.append([("💬 درخواست مشاوره", "request_consult")])
    kb_rows.append([("🏠 بازگشت به منوی اصلی", "back_main_menu")])
    kb = inline_kb_urlaware(kb_rows)
    if message_id:
        edit_message(chat_id, message_id, text, kb)
    else:
        send_message(chat_id, text, kb)

def show_result_analysis(chat_id, message_id, uid, result_id):
    users = load_users()
    user = users[str(uid)]
    result = next((r for r in user["results"] if r["id"] == result_id), None)
    if not result:
        edit_message(chat_id, message_id, "نتیجه پیدا نشد.", inline_kb([[("↩️ بازگشت", "tests_home")]]))
        return
    tests = load_tests()
    test = tests.get(result["test_id"], {})
    range_text = find_range_text(test, result.get("display_value", result.get("score", 0)))
    range_block = f"\n\n📝 {range_text}" if range_text else ""

    subscale_block = ""
    if result.get("subscales"):
        lines = [f"  • {name}: {info['label']}" for name, info in result["subscales"].items()]
        subscale_block = "\n\n🧩 نتیجه به تفکیک خرده‌مقیاس:\n" + "\n".join(lines)

    score_fallback = result_score_label(result)
    text = (
        f"📊 تحلیل کامل «{result['test_title']}»\n\n"
        f"نمره: {result.get('display_label', score_fallback)}\n"
        f"تاریخ: {result.get('date', '')}\n\n"
        f"{NEUTRAL_SCORE_NOTE}\n\n"
        f"{DISCLAIMER}"
        f"{range_block}"
        f"{subscale_block}"
    )
    rows = []
    if test.get("related_post_link"):
        rows.append([("📖 مطالعه بیشتر", test["related_post_link"], "url")])
    rows.append([("🗑 حذف این نتیجه", f"delresult:{result_id}")])
    rows.append([("↩️ بازگشت", "tests_home")])
    edit_message(chat_id, message_id, text, inline_kb_urlaware(rows))

def show_result_answers(chat_id, message_id, uid, result_id):
    users = load_users()
    user = users[str(uid)]
    result = next((r for r in user["results"] if r["id"] == result_id), None)
    if not result:
        edit_message(chat_id, message_id, "نتیجه پیدا نشد.", inline_kb([[("↩️ بازگشت", "tests_home")]]))
        return
    tests = load_tests()
    test = tests.get(result["test_id"])
    lines = [f"📋 پاسخ‌های شما در «{result['test_title']}»\n"]
    if test:
        for qi, q in enumerate(test["questions"]):
            ans = result["answers"].get(str(qi))
            ans_text = q["options"][int(ans)]["text"] if ans is not None else "بدون پاسخ"
            lines.append(f"{qi + 1}. {q['text']}\n   ✅ {ans_text}")
    edit_message(chat_id, message_id, "\n".join(lines)[:4000], inline_kb([[("↩️ بازگشت", "tests_home")]]))

def show_my_tests_dashboard(chat_id, uid):
    users = load_users()
    user = users[str(uid)]
    text = (
        "📋 آزمون‌های من\n\n"
        f"⏳ در حال انجام: {len(user['in_progress'])}\n"
        f"✅ انجام‌شده: {len(user['results'])}\n"
        f"⭐ ذخیره‌شده: {len(user['saved_tests'])}\n"
    )
    kb = inline_kb([
        [("⏳ آزمون‌های در حال انجام", "tests_inprogress")],
        [("📊 نتایج و نمرات من", "tests_results")],
        [("⭐ آزمون‌های ذخیره‌شده", "tests_saved")],
        [("🧠 رفتن به لیست آزمون‌ها", "tests_home")],
        [("🏠 بازگشت به منوی اصلی", "back_main_menu")],
    ])
    send_message(chat_id, text, kb)

def show_edu_list(chat_id, message_id=None):
    content = load_content()
    if not content:
        text = "📚 هنوز محتوای آموزشی اضافه نشده. به‌زودی اینجا مطالب مفیدی قرار می‌گیرد."
        kb = inline_kb([[("🏠 بازگشت به منوی اصلی", "back_main_menu")]])
    else:
        rows = [[(c["title"], f"edu_view:{cid}")] for cid, c in content.items()]
        rows.append([("🏠 بازگشت به منوی اصلی", "back_main_menu")])
        text = "📚 محتوای آموزشی مانا مایند:"
        kb = inline_kb(rows)
    if message_id:
        edit_message(chat_id, message_id, text, kb)
    else:
        send_message(chat_id, text, kb)

def show_edu_item(chat_id, message_id, cid):
    content = load_content()
    item = content.get(cid)
    if not item:
        edit_message(chat_id, message_id, "این محتوا پیدا نشد.", inline_kb([[("↩️ بازگشت", "edu_list")]]))
        return
    text = f"📚 {item['title']}\n\n{item['body']}"
    edit_message(chat_id, message_id, text, inline_kb([[("↩️ بازگشت", "edu_list")]]))

# ====================================================================
# تمرین‌های روان‌شناختی
# ====================================================================
def show_exercise_list(chat_id, message_id=None):
    exercises = load_exercises()
    if not exercises:
        text = "📝 هنوز تمرینی اضافه نشده. به‌زودی تمرین‌های مفیدی اینجا قرار می‌گیرد."
        kb = inline_kb([[("🏠 بازگشت به منوی اصلی", "back_main_menu")]])
    else:
        rows = [[(e["title"], f"ex_view:{eid}")] for eid, e in exercises.items()]
        rows.append([("🏠 بازگشت به منوی اصلی", "back_main_menu")])
        text = "📝 تمرین‌های روان‌شناختی مانا مایند:"
        kb = inline_kb(rows)
    if message_id:
        edit_message(chat_id, message_id, text, kb)
    else:
        send_message(chat_id, text, kb)

def show_exercise_item(chat_id, message_id, uid, eid):
    exercises = load_exercises()
    ex = exercises.get(eid)
    if not ex:
        edit_message(chat_id, message_id, "این تمرین پیدا نشد.", inline_kb([[("↩️ بازگشت", "exercise_list")]]))
        return
    users = load_users()
    user = users[str(uid)]
    done_count = len(user.get("exercise_log", {}).get(eid, []))
    text = f"📝 {ex['title']}\n\n{ex['instructions']}\n\n🔥 تعداد دفعاتی که این تمرین رو انجام دادی: {done_count}"
    kb = inline_kb([
        [("✅ انجام دادم", f"ex_done:{eid}")],
        [("↩️ بازگشت", "exercise_list")],
    ])
    edit_message(chat_id, message_id, text, kb)

def mark_exercise_done(uid, chat_id, message_id, eid):
    exercises = load_exercises()
    ex = exercises.get(eid)
    if not ex:
        edit_message(chat_id, message_id, "این تمرین پیدا نشد.", inline_kb([[("↩️ بازگشت", "exercise_list")]]))
        return
    users = load_users()
    user = users[str(uid)]
    today = datetime.now().strftime("%Y-%m-%d")
    log = user.setdefault("exercise_log", {}).setdefault(eid, [])
    if today not in log:
        log.append(today)
    save_users(users)
    total_done = sum(len(v) for v in user.get("exercise_log", {}).values())
    text = f"🎉 آفرین! ثبت شد.\n\n🔥 تعداد کل تمرین‌هایی که انجام دادی: {total_done}"
    new_gifts = check_and_list_new_gifts(user)
    if new_gifts:
        text += "\n\n🎁 هدیه‌ی جدید برات باز شد! از «🎁 خدمات و مزایا → 🎁 هدایای من» ببینش."
    edit_message(chat_id, message_id, text, inline_kb([[("📝 تمرین‌های دیگر", "exercise_list")], [("🏠 بازگشت به منوی اصلی", "back_main_menu")]]))

# ====================================================================
# «مشکل من چیست؟»
# ====================================================================
PROBLEM_AUDIENCES = [
    ("🧑 خودم (بزرگسال)", "adult"),
    ("🧑‍🎓 نوجوان هستم", "teen"),
    ("👶 برای فرزندم", "child"),
]

BOOKING_TYPES = [
    ("👤 مشاوره فردی", "individual"),
    ("💑 مشاوره زوجین", "couple"),
    ("💍 مشاوره پیش از ازدواج", "premarital"),
    ("💔 مشاوره شکست عاطفی", "breakup"),
    ("👨‍👩‍👧 مشاوره فرزندپروری", "parenting"),
]
BOOKING_TYPE_LABELS = {key: label for label, key in BOOKING_TYPES}

TIME_PREF_OPTIONS = ["🌅 صبح", "🌇 عصر", "🌙 شب", "📝 هر زمانی که آزاد باشه"]

def show_consult_type_menu(chat_id):
    text = "💬 چه نوع مشاوره‌ای می‌خوای رزرو کنی؟"
    rows = [[(label, f"book_type:{key}")] for label, key in BOOKING_TYPES]
    rows.append([("✍️ فقط می‌خوام یه پیام بنویسم", "consult_freeform")])
    send_message(chat_id, text, inline_kb(rows))

def require_phone_or_ask(uid, chat_id, user, pending_consult):
    """قبل از ثبت درخواست مشاوره، اگه شماره تلفن کاربر ثبت نشده باشه، اول ازش با دکمه‌ی اختصاصی بله می‌خواد
    که شمارش رو بفرسته (تا تیم مانا مایند بتونه باهاش تماس بگیره)، و کاری که در انتظاره رو ذخیره می‌کنه.
    خروجی: True یعنی شماره از قبل ثبت شده و می‌تونی همون لحظه ادامه بدی؛ False یعنی منتظر دریافت شماره‌ایم."""
    if user.get("phone"):
        return True
    user["state"] = {"mode": "awaiting_phone", "data": {"pending_consult": pending_consult}}
    update_user(uid, user)
    send_message(
        chat_id,
        "📱 برای درخواست مشاوره، لطفاً اول شماره تلفنتون رو با دکمه‌ی زیر بفرستید تا تیم مانا مایند بتونه باهاتون تماس بگیره:",
        contact_request_kb(),
    )
    return False

def start_booking_time(uid, chat_id, user, type_key):
    user["state"] = {"mode": "booking_time_wait", "data": {"type": type_key}}
    update_user(uid, user)
    send_message(chat_id, "⏰ چه زمانی برات مناسب‌تره؟", reply_kb([TIME_PREF_OPTIONS[:2], TIME_PREF_OPTIONS[2:], ["↩️ بازگشت"]]))

def handle_booking_time(uid, chat_id, text, user):
    if text not in TIME_PREF_OPTIONS:
        send_message(chat_id, "لطفاً یکی از دکمه‌ها رو انتخاب کن:", reply_kb([TIME_PREF_OPTIONS[:2], TIME_PREF_OPTIONS[2:], ["↩️ بازگشت"]]))
        return
    user["state"]["data"]["time_pref"] = text
    user["state"]["mode"] = "booking_note_wait"
    update_user(uid, user)
    send_message(chat_id, "✏️ اگه توضیح مختصری هم داری بنویس، وگرنه بنویس «ندارم»:", back_kb())

def finalize_booking(uid, chat_id, user, note):
    info = user["state"]["data"]
    type_key = info.get("type")
    time_pref = info.get("time_pref")
    is_crisis = contains_crisis_language(note)
    bookings = load_bookings()
    bid = str(uuid.uuid4())[:8]
    bookings[bid] = {
        "id": bid, "uid": str(uid),
        "name": f"{user.get('first_name','')} {user.get('last_name','')}".strip(),
        "username": user.get("username", ""),
        "phone": user.get("phone"),
        "type": type_key, "type_label": BOOKING_TYPE_LABELS.get(type_key, type_key),
        "time_pref": time_pref, "note": note,
        "status": "pending", "date": now_str(), "is_crisis": is_crisis,
    }
    save_bookings(bookings)
    user["state"] = {"mode": None, "data": {}}
    update_user(uid, user)
    send_message(
        chat_id,
        f"✅ درخواست رزرو «{bookings[bid]['type_label']}» ثبت شد.\nزمان ترجیحی: {time_pref}\n\n"
        "به‌محض تأیید یا هماهنگی، بهت خبر می‌دیم.",
        main_menu_keyboard(),
    )
    if is_crisis:
        send_message(chat_id, CRISIS_RESOURCE_TEXT)
    kb = inline_kb([
        [("✅ تأیید رزرو", f"approve_booking:{bid}"), ("❌ رد رزرو", f"reject_booking:{bid}")],
    ])
    crisis_prefix = "🚨 هشدار بحران!\n\n" if is_crisis else ""
    for admin_id in ADMIN_IDS:
        send_message(
            admin_id,
            f"{crisis_prefix}📅 درخواست رزرو مشاوره جدید\n\n"
            f"نوع: {bookings[bid]['type_label']}\nنام: {bookings[bid]['name']}\n"
            f"یوزرنیم: @{bookings[bid]['username']}\nآیدی: {uid}\nتلفن: {bookings[bid]['phone'] or 'ثبت نشده'}\n"
            f"زمان ترجیحی: {time_pref}\nتوضیح: {note}",
            kb,
        )

def handle_booking_decision(uid, chat_id, message_id, data_cb):
    approve = data_cb.startswith("approve_booking:")
    bid = data_cb.split(":", 1)[1]
    bookings = load_bookings()
    b = bookings.get(bid)
    if not b:
        edit_message(chat_id, message_id, "این رزرو پیدا نشد.")
        return
    b["status"] = "approved" if approve else "rejected"
    save_bookings(bookings)
    edit_message(chat_id, message_id, f"{'✅ تأیید شد' if approve else '❌ رد شد'}: {b['type_label']} برای {b['name']}")
    if approve:
        send_message(b["uid"], f"✅ رزرو «{b['type_label']}» شما تأیید شد. تیم مانا مایند به‌زودی برای هماهنگی زمان دقیق باهات تماس می‌گیره.")
    else:
        send_message(b["uid"], f"متأسفانه رزرو «{b['type_label']}» با زمان پیشنهادی شما امکان‌پذیر نبود. می‌تونی دوباره با زمان دیگه‌ای درخواست بدی یا از بخش پشتیبانی باهامون هماهنگ کنی.")

def show_problem_audience(chat_id, message_id=None):
    text = "💭 مشکل من چیست؟\n\nاول بگو این موضوع برای کیه، تا بهترین محتوا رو پیشنهاد بدم:"
    kb = inline_kb([[(label, f"problem_aud:{key}")] for label, key in PROBLEM_AUDIENCES] + [[("🏠 بازگشت به منوی اصلی", "back_main_menu")]])
    if message_id:
        edit_message(chat_id, message_id, text, kb)
    else:
        send_message(chat_id, text, kb)

def show_problem_topics(chat_id, message_id, audience):
    intro = {
        "adult": "خب، بگو کدوم موضوع بیشتر ذهنتو درگیر کرده:",
        "teen": "بگو کدوم موضوع این روزها بیشتر اذیتت می‌کنه:",
        "child": "کدوم حوزه رو می‌خوای درباره‌ی فرزندت بدونی؟",
    }.get(audience, "یکی رو انتخاب کن:")
    items = list(CATEGORIES.items())
    rows = []
    for i in range(0, len(items), 2):
        row = [(items[i][1], f"problem_topic:{audience}:{items[i][0]}")]
        if i + 1 < len(items):
            row.append((items[i + 1][1], f"problem_topic:{audience}:{items[i + 1][0]}"))
        rows.append(row)
    rows.append([("↩️ بازگشت", "problem_home")])
    edit_message(chat_id, message_id, intro, inline_kb(rows))

PROBLEM_SUPPORT_TEXT = (
    "این یه موضوع رایجه و خیلی‌ها باهاش دست‌وپنجه نرم می‌کنن. اینجا چند مسیر برات آماده کردیم — "
    "لازم نیست همه رو امتحان کنی، از هرکدوم که بیشتر بهت کمک می‌کنه شروع کن."
)

def track_problem_topic_click(cat_key):
    settings = load_settings()
    clicks = settings.setdefault("problem_topic_clicks", {})
    clicks[cat_key] = clicks.get(cat_key, 0) + 1
    save_settings(settings)

def show_problem_topic_detail(chat_id, message_id, audience, cat_key):
    track_problem_topic_click(cat_key)
    cat_label = CATEGORIES.get(cat_key, cat_key)
    text = f"{cat_label}\n\n{PROBLEM_SUPPORT_TEXT}"
    exercises = load_exercises()
    matched_ex = [(eid, e) for eid, e in exercises.items() if e.get("category") == cat_key]
    rows = [[("🧠 آزمون‌های این حوزه", f"cat:{cat_key}")]]
    if matched_ex:
        rows.append([("📝 تمرین پیشنهادی این حوزه", f"ex_view:{matched_ex[0][0]}")])
    rows.append([("💬 درخواست مشاوره", "request_consult")])
    rows.append([("↩️ بازگشت", f"problem_aud:{audience}")])
    edit_message(chat_id, message_id, text, inline_kb(rows))

# ====================================================================
# سیستم هدیه
# ====================================================================
def user_progress_counts(user):
    tests_done = len(user.get("results", []))
    exercises_done = sum(len(v) for v in user.get("exercise_log", {}).values())
    return tests_done, exercises_done

def gift_is_unlocked(gift, user):
    tests_done, exercises_done = user_progress_counts(user)
    if gift.get("unlock_type") == "tests":
        return tests_done >= gift.get("unlock_count", 0)
    return exercises_done >= gift.get("unlock_count", 0)

def check_and_list_new_gifts(user):
    """فقط برای اطلاع سریع بعد از ثبت تمرین/آزمون - آیا هدیه‌ی تازه‌ای باز شده؟"""
    gifts = load_gifts()
    return [g for g in gifts.values() if gift_is_unlocked(g, user)]

def show_my_gifts(chat_id, message_id, user):
    gifts = load_gifts()
    if not gifts:
        edit_message(chat_id, message_id, "هنوز هدیه‌ای تعریف نشده.", inline_kb([[("↩️ بازگشت", "services_home")]]))
        return
    tests_done, exercises_done = user_progress_counts(user)
    lines = [f"🎁 هدایای من\n\n📝 آزمون‌های انجام‌شده: {tests_done}  |  🔥 تمرین‌های انجام‌شده: {exercises_done}\n"]
    rows = []
    for gid, g in gifts.items():
        unlocked = gift_is_unlocked(g, user)
        status = "🔓 باز شده" if unlocked else f"🔒 نیاز به {g.get('unlock_count')} {'آزمون' if g.get('unlock_type')=='tests' else 'تمرین'}"
        lines.append(f"• {g['title']} — {status}")
        if unlocked:
            rows.append([(f"🎁 دریافت «{g['title']}»", f"gift_claim:{gid}")])
    rows.append([("↩️ بازگشت", "services_home")])
    edit_message(chat_id, message_id, "\n".join(lines), inline_kb(rows))

def claim_gift(chat_id, message_id, user, gid):
    gifts = load_gifts()
    g = gifts.get(gid)
    if not g or not gift_is_unlocked(g, user):
        edit_message(chat_id, message_id, "این هدیه هنوز برات باز نشده.", inline_kb([[("↩️ بازگشت", "gifts_home")]]))
        return
    edit_message(chat_id, message_id, f"🎁 {g['title']}\n\n{g['content']}", inline_kb([[("↩️ بازگشت", "gifts_home")]]))

# ====================================================================
# فروشگاه (محصولات) — پرداخت واقعی از طریق کیف پول بله
# ====================================================================
def show_store_home(chat_id, message_id=None):
    products = load_products()
    if not products:
        text = "🛍 هنوز محصولی برای فروش ثبت نشده. به‌زودی محصولات آموزشی اینجا قرار می‌گیرند."
        kb = inline_kb([[("↩️ بازگشت", "back_main_menu")]])
    else:
        rows = [[(f"{p['title']} — {p['price_toman']:,} تومان", f"product_view:{pid}")] for pid, p in products.items()]
        rows.append([("↩️ بازگشت", "back_main_menu")])
        text = "🛍 فروشگاه مانا مایند:"
        kb = inline_kb(rows)
    if message_id:
        edit_message(chat_id, message_id, text, kb)
    else:
        send_message(chat_id, text, kb)

def show_store_product(chat_id, message_id, pid):
    products = load_products()
    p = products.get(pid)
    if not p:
        edit_message(chat_id, message_id, "این محصول پیدا نشد.", inline_kb([[("↩️ بازگشت", "store_home")]]))
        return
    text = f"🛍 {p['title']}\n\n{p['description']}\n\n💰 قیمت: {p['price_toman']:,} تومان"
    kb = inline_kb([
        [("💳 خرید و پرداخت", f"product_buy:{pid}")],
        [("↩️ بازگشت", "store_home")],
    ])
    if p.get("photo"):
        send_photo(chat_id, p["photo"], caption=text, reply_markup=kb)
    else:
        edit_message(chat_id, message_id, text, kb)

def place_order(uid, chat_id, message_id, user, pid):
    products = load_products()
    p = products.get(pid)
    if not p:
        edit_message(chat_id, message_id, "این محصول پیدا نشد.", inline_kb([[("↩️ بازگشت", "store_home")]]))
        return
    orders = load_orders()
    oid = str(uuid.uuid4())[:8]
    orders[oid] = {
        "id": oid, "uid": str(uid), "product_id": pid, "product_title": p["title"],
        "price_toman": p["price_toman"],
        "name": f"{user.get('first_name','')} {user.get('last_name','')}".strip(),
        "username": user.get("username", ""), "phone": user.get("phone"),
        "status": "awaiting_payment", "date": now_str(),
    }
    save_orders(orders)
    result = send_invoice(
        chat_id=chat_id,
        title=p["title"][:32],
        description=p["description"][:255] or p["title"][:255],
        payload=oid,
        price_toman=p["price_toman"],
        photo_url=p.get("photo") if (p.get("photo") or "").startswith("http") else None,
    )
    if not result or not result.get("ok"):
        orders[oid]["status"] = "failed_to_create_invoice"
        save_orders(orders)
        send_message(chat_id, "❌ متأسفانه در ایجاد صورتحساب پرداخت مشکلی پیش اومد. لطفاً بعداً دوباره امتحان کن یا با پشتیبانی تماس بگیر.")
        return
    send_message(chat_id, "💳 صورتحساب پرداخت برات ارسال شد. روی پیام بالا بزن و پرداخت رو تکمیل کن.")

def deliver_paid_order(uid, oid):
    orders = load_orders()
    o = orders.get(oid)
    if not o:
        return
    products = load_products()
    p = products.get(o["product_id"], {})
    o["status"] = "paid"
    save_orders(orders)
    send_message(
        uid,
        f"✅ پرداخت شما برای «{o['product_title']}» با موفقیت انجام شد!\n\n"
        f"📦 محتوای محصول:\n{p.get('delivery_content', 'برای دریافت محتوا با پشتیبانی تماس بگیرید.')}",
    )
    for admin_id in ADMIN_IDS:
        send_message(admin_id, f"💰 پرداخت موفق!\n\nمحصول: {o['product_title']}\nقیمت: {o['price_toman']:,} تومان\nخریدار: {o['name']} (آیدی: {uid})")


def handle_message(message):
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    chat_type = chat.get("type", "private")
    if chat_type != "private":
        capture_channel_numeric_id(chat)
        return  # پیام‌های کانال/گروه رو نادیده می‌گیریم؛ ربات فقط تو چت خصوصی کار می‌کنه
    text = message.get("text") or message.get("caption") or ""
    from_user = message.get("from", {})
    uid = from_user.get("id")
    if not uid:
        return

    # ---------- فوروارد پیام از کانال برای گرفتن آیدی عددی واقعی ----------
    forward_chat = message.get("forward_from_chat")
    if forward_chat and forward_chat.get("type") in ("channel", "group", "supergroup"):
        matched = capture_channel_numeric_id(forward_chat)
        if matched:
            send_message(
                chat_id,
                f"✅ آیدی عددی کانال «{matched['title']}» پیدا و ذخیره شد ({forward_chat.get('id')}).\n"
                "جوین اجباری از الان باید درست کار کنه!",
            )
            return

    user = get_or_create_user(from_user)
    today_str = datetime.now().strftime("%Y-%m-%d")
    if user.get("last_seen") != today_str:
        user["last_seen"] = today_str
        update_user(uid, user)

    # ---------- پرداخت موفق ----------
    successful_payment = message.get("successful_payment")
    if successful_payment:
        oid = successful_payment.get("invoice_payload")
        if oid:
            deliver_paid_order(uid, oid)
        return

    # ---------- دریافت شماره تلفن (بعد از درخواست برای شروع آزمون یا ثبت درخواست مشاوره) ----------
    contact = message.get("contact")
    if contact and user["state"].get("mode") == "awaiting_phone":
        phone = contact.get("phone_number", "")
        user["phone"] = phone
        pending_data = user["state"]["data"]
        pending_tid = pending_data.get("pending_test_id")
        pending_consult = pending_data.get("pending_consult")
        user["state"] = {"mode": None, "data": {}}
        update_user(uid, user)
        send_message(chat_id, "✅ شماره تلفن شما ثبت شد.", remove_kb())
        if pending_tid and not user_has_taken(user, pending_tid):
            user["in_progress"][pending_tid] = {"index": 0, "answers": {}}
            update_user(uid, user)
            send_question(chat_id, uid, pending_tid)
        elif pending_consult == "menu":
            show_consult_type_menu(chat_id)
        elif pending_consult == "freeform":
            user["state"] = {"mode": "consult_request", "data": {}}
            update_user(uid, user)
            send_message(chat_id, "💬 لطفاً موضوع و توضیح مختصری از درخواست مشاوره خود را بنویسید و ارسال کنید:", back_kb())
        elif isinstance(pending_consult, dict) and pending_consult.get("kind") == "booking":
            start_booking_time(uid, chat_id, user, pending_consult["type_key"])
        else:
            send_message(chat_id, "🏠 منوی اصلی", main_menu_keyboard())
        return

    # ---------- گفتگوی فعال کاربر با ادمین (مشاوره/پشتیبانی) ----------
    if user["state"].get("mode") == "chatting_with_admin":
        handle_user_chat_message(uid, chat_id, text, user, message)
        return

    # ---------- گفتگوی فعال ادمین با کاربر ----------
    if is_admin(uid) and user["admin_state"].get("mode") == "chat_active":
        handle_admin_chat_message(uid, chat_id, text, user, message)
        return

    # ---------- اگر ادمین داخل پنل ادمین است (ویزارد یا منو) ----------
    if is_admin(uid) and (user["admin_state"].get("mode") or user["admin_state"].get("menu")):
        admin_route(uid, chat_id, text, user, message)
        return

    if text == "/start":
        user["state"] = {"mode": None, "data": {}}
        update_user(uid, user)
        if not ensure_joined_or_gate(uid, chat_id, user):
            return
        name = user.get("first_name") or "دوست عزیز"
        send_message(chat_id, WELCOME_TEXT.format(name=name), main_menu_keyboard())
        return

    if text == "/whoami":
        send_message(chat_id, f"🆔 آیدی عددی شما: {uid}\n👑 ادمین هستید: {'بله ✅' if is_admin(uid) else 'خیر ❌'}")
        return

    if text == "/manamind":
        if is_admin(uid):
            user["admin_state"] = {"mode": None, "menu": "admin_main", "data": {}}
            update_user(uid, user)
            send_message(chat_id, admin_menu_text(), admin_main_kb())
        else:
            send_message(chat_id, f"⛔️ شما به این بخش دسترسی ندارید.\nآیدی عددی شما: {uid}\n(اگه فکر می‌کنی باید ادمین باشی، همین عدد رو به مدیر اصلی بده تا اضافه‌ات کنه)")
        return

    if not ensure_joined_or_gate(uid, chat_id, user):
        return

    mode = user["state"]["mode"]

    # ---------- لغو/خروج از فلوهای متنی (مشاوره، پشتیبانی، رزرو، شماره تلفن) ----------
    CANCELLABLE_MODES = {"consult_request", "support_request", "booking_time_wait", "booking_note_wait", "awaiting_phone"}
    if mode in CANCELLABLE_MODES:
        if text == "↩️ بازگشت":
            user["state"] = {"mode": None, "data": {}}
            update_user(uid, user)
            send_message(chat_id, "لغو شد. 🏠 منوی اصلی", main_menu_keyboard())
            return
        if is_main_menu_button_text(text):
            # کاربر وسط فلو روی یکی از دکمه‌های منوی اصلی زده — یعنی نمی‌خواسته این متن به‌عنوان پیام
            # مشاوره/پشتیبانی ثبت بشه، پس فلو رو لغو می‌کنیم و می‌ذاریم پایین‌تر به‌عنوان دستور منو پردازش بشه.
            user["state"] = {"mode": None, "data": {}}
            update_user(uid, user)
            mode = None

    if mode == "booking_time_wait":
        handle_booking_time(uid, chat_id, text, user)
        return

    if mode == "booking_note_wait":
        note = "" if text.strip() == "ندارم" else text.strip()
        finalize_booking(uid, chat_id, user, note)
        return

    if mode == "search_test":
        user["state"] = {"mode": None, "data": {}}
        update_user(uid, user)
        tests = load_tests()
        q = text.strip().lower()
        results = [
            t for t in tests.values()
            if q in t["title"].lower() or q in CATEGORIES.get(t["category"], "").lower()
        ]
        if not results:
            send_message(chat_id, "چیزی با این عنوان پیدا نشد. 🔎", main_menu_keyboard())
        else:
            rows = [[(t["title"], f"test:{t['id']}")] for t in results]
            rows.append([("↩️ بازگشت", "tests_home")])
            send_message(chat_id, f"نتایج جستجو برای «{text}»:", inline_kb(rows))
        return

    if mode == "consult_request":
        is_crisis = contains_crisis_language(text)
        has_media = message_has_media(message)
        consults = load_consultations()
        cid = str(uuid.uuid4())[:8]
        consults[cid] = {
            "id": cid, "uid": str(uid),
            "name": f"{user.get('first_name','')} {user.get('last_name','')}".strip(),
            "username": user.get("username", ""),
            "text": text or ("[فایل/عکس/صدا ارسال شد]" if has_media else ""),
            "date": now_str(), "status": "pending",
            "admin_id": None, "rating": None, "is_crisis": is_crisis,
        }
        save_consultations(consults)
        user["state"] = {"mode": None, "data": {}}
        update_user(uid, user)
        send_message(chat_id, "✅ درخواست مشاوره شما ثبت شد. به‌زودی تیم مانا مایند با شما تماس می‌گیرد.", main_menu_keyboard())
        if is_crisis:
            send_message(chat_id, CRISIS_RESOURCE_TEXT)
        kb = inline_kb([[("✉️ پاسخ به کاربر", f"claim_consult:{cid}")]])
        crisis_prefix = "🚨 هشدار: این پیام حاوی عبارات مرتبط با بحران/خودآسیب‌رسانیه — لطفاً در اولویت بررسی کن!\n\n" if is_crisis else ""
        header = f"{crisis_prefix}💬 درخواست مشاوره جدید\n\nنام: {consults[cid]['name']}\nیوزرنیم: @{consults[cid]['username']}\nآیدی: {uid}\n\nمتن:"
        for admin_id in ADMIN_IDS:
            send_message(admin_id, header, kb)
            relay_content(admin_id, message)
        return

    if mode == "support_request":
        is_crisis = contains_crisis_language(text)
        has_media = message_has_media(message)
        tickets = load_support()
        tid = str(uuid.uuid4())[:8]
        tickets[tid] = {
            "id": tid, "uid": str(uid),
            "name": f"{user.get('first_name','')} {user.get('last_name','')}".strip(),
            "username": user.get("username", ""),
            "text": text or ("[فایل/عکس/صدا ارسال شد]" if has_media else ""),
            "date": now_str(), "status": "pending",
            "admin_id": None, "rating": None, "is_crisis": is_crisis,
        }
        save_support(tickets)
        user["state"] = {"mode": None, "data": {}}
        update_user(uid, user)
        send_message(chat_id, "✅ پیام شما برای پشتیبانی ثبت شد. به‌زودی پاسخ داده می‌شود.", main_menu_keyboard())
        if is_crisis:
            send_message(chat_id, CRISIS_RESOURCE_TEXT)
        kb = inline_kb([[("✉️ پاسخ به کاربر", f"claim_support:{tid}")]])
        crisis_prefix = "🚨 هشدار: این پیام حاوی عبارات مرتبط با بحران/خودآسیب‌رسانیه — لطفاً در اولویت بررسی کن!\n\n" if is_crisis else ""
        header = f"{crisis_prefix}🆘 تیکت پشتیبانی جدید\n\nنام: {tickets[tid]['name']}\nیوزرنیم: @{tickets[tid]['username']}\nآیدی: {uid}\n\nمتن:"
        for admin_id in ADMIN_IDS:
            send_message(admin_id, header, kb)
            relay_content(admin_id, message)
        return

    if text == "👤 پروفایل من":
        send_message(chat_id, build_profile_text(user), main_menu_keyboard())
        send_message(chat_id, "برای حذف کامل اطلاعاتتون از ربات:", inline_kb([[("🗑 حذف اطلاعات من", "delete_my_data")]]))

    elif text == "ℹ️ درباره دکتر ماندانا داودی":
        send_message(chat_id, ABOUT_TEXT, main_menu_keyboard())

    elif text == "📢 ورود به کانال مانا مایند":
        send_message(chat_id, f"برای عضویت در کانال روی لینک زیر بزن:\n{channel_entry_text()}", main_menu_keyboard())

    elif text == "🌱 حال من امروز چطوره؟":
        show_mood_checkin(chat_id, user)

    elif text == "📜 قوانین و حریم خصوصی":
        show_legal_home(chat_id)

    elif text == "🧠 آزمون‌های روان‌شناسی":
        show_tests_home(chat_id)

    elif text == "📋 آزمون‌های من":
        show_my_tests_dashboard(chat_id, uid)

    elif text == "📊 نتایج و نمرات من":
        if not user["results"]:
            send_message(chat_id, "هنوز هیچ آزمونی انجام نداده‌اید. از منوی «🧠 آزمون‌های روان‌شناسی» شروع کنید.", main_menu_keyboard())
        else:
            rows = [
                [(f"{r['test_title']} - {result_score_label(r)} ({r['date']})", f"view_analysis:{r['id']}")]
                for r in reversed(user["results"])
            ]
            rows.append([("🏠 بازگشت به منوی اصلی", "back_main_menu")])
            send_message(chat_id, "📊 نتایج آزمون‌های شما:", inline_kb(rows))

    elif text == "💬 درخواست مشاوره":
        if require_phone_or_ask(uid, chat_id, user, "menu"):
            show_consult_type_menu(chat_id)

    elif text == "🎁 خدمات و مزایا":
        send_message(chat_id, "🎁 خدمات و مزایا", inline_kb([
            [("🎁 معرفی خدمات", "services_home")],
            [("🎁 هدایای من", "gifts_home")],
            [("🛍 فروشگاه", "store_home")],
        ]))

    elif text == "📚 محتوای آموزشی":
        show_edu_list(chat_id)

    elif text == "💭 مشکل من چیست؟":
        show_problem_audience(chat_id)

    elif text == "📝 تمرین‌های روان‌شناختی":
        show_exercise_list(chat_id)

    elif text == "🆘 پشتیبانی":
        user["state"] = {"mode": "support_request", "data": {}}
        update_user(uid, user)
        send_message(chat_id, "🆘 لطفاً مشکل یا سؤال خود را بنویسید تا برای تیم پشتیبانی ارسال شود:", back_kb())

    else:
        send_message(chat_id, "لطفاً یکی از گزینه‌های منو رو انتخاب کن 👇", main_menu_keyboard())

# ====================================================================
# پردازش کلیک روی دکمه‌های شیشه‌ای (فقط بخش آزمون‌ها و جوین اجباری)
# ====================================================================
def handle_callback_query(cq):
    cq_id = cq["id"]
    from_user = cq.get("from", {})
    uid = from_user.get("id")
    message = cq.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")
    data_cb = cq.get("data", "")

    if uid is None or chat_id is None:
        answer_callback(cq_id)
        return

    user = get_or_create_user(from_user)

    if data_cb == "check_join":
        # مستقیم چک می‌کنیم (بدون ارسال دوباره‌ی پیام گیت) تا فقط یه پاپ‌آپ نتیجه رو نشون بده
        if is_admin(uid) or user_is_member_everywhere(uid):
            if not user.get("join_gate_passed"):
                user["join_gate_passed"] = True
                update_user(uid, user)
            answer_callback(cq_id, "✅ عضویت شما تأیید شد!")
            name = user.get("first_name") or "دوست عزیز"
            send_message(chat_id, f"✅ عضویت شما تأیید شد!\n\n{WELCOME_TEXT.format(name=name)}", main_menu_keyboard())
        else:
            answer_callback(cq_id, "❗️هنوز عضو کانال نشدید. لطفاً اول عضو بشید، بعد دوباره امتحان کنید.", show_alert=True)
        return

    answer_callback(cq_id)

    if not ensure_joined_or_gate(uid, chat_id, user):
        return

    if data_cb == "edu_list":
        show_edu_list(chat_id, message_id)
        return
    if data_cb.startswith("edu_view:"):
        show_edu_item(chat_id, message_id, data_cb.split(":", 1)[1])
        return

    if data_cb == "services_home":
        settings = load_settings()
        edit_message(chat_id, message_id, settings.get("services_text", ""), inline_kb([[("↩️ بازگشت", "back_main_menu")]]))
        return
    if data_cb == "gifts_home":
        show_my_gifts(chat_id, message_id, user)
        return
    if data_cb.startswith("gift_claim:"):
        claim_gift(chat_id, message_id, user, data_cb.split(":", 1)[1])
        return
    if data_cb == "store_home":
        show_store_home(chat_id, message_id)
        return
    if data_cb.startswith("product_view:"):
        show_store_product(chat_id, message_id, data_cb.split(":", 1)[1])
        return
    if data_cb.startswith("product_buy:"):
        place_order(uid, chat_id, message_id, user, data_cb.split(":", 1)[1])
        return

    if data_cb == "exercise_list":
        show_exercise_list(chat_id, message_id)
        return
    if data_cb.startswith("ex_view:"):
        show_exercise_item(chat_id, message_id, uid, data_cb.split(":", 1)[1])
        return
    if data_cb.startswith("ex_done:"):
        mark_exercise_done(uid, chat_id, message_id, data_cb.split(":", 1)[1])
        return

    if data_cb == "problem_home":
        show_problem_audience(chat_id, message_id)
        return
    if data_cb.startswith("problem_aud:"):
        show_problem_topics(chat_id, message_id, data_cb.split(":", 1)[1])
        return
    if data_cb.startswith("problem_topic:"):
        _, audience, cat_key = data_cb.split(":")
        show_problem_topic_detail(chat_id, message_id, audience, cat_key)
        return

    if data_cb == "tests_home":
        show_tests_home(chat_id, message_id)

    elif data_cb == "back_main_menu":
        send_message(chat_id, "🏠 منوی اصلی", main_menu_keyboard())

    elif data_cb == "tests_new":
        tests = load_tests()
        new_tests = sorted([t for t in tests.values() if t.get("is_new")], key=lambda t: t["created_at"], reverse=True)
        render_test_list(chat_id, message_id, new_tests, "🆕 آزمون‌های جدید:", "tests_home")

    elif data_cb == "tests_popular":
        tests = load_tests()
        popular = sorted(tests.values(), key=lambda t: t.get("participation_count", 0), reverse=True)[:10]
        render_test_list(chat_id, message_id, popular, "🔥 آزمون‌های محبوب:", "tests_home")

    elif data_cb == "tests_suggested":
        tests = load_tests()
        taken_ids = {r["test_id"] for r in user["results"]}
        taken_cats = {tests[t]["category"] for t in taken_ids if t in tests}
        suggested = [t for t in tests.values() if t["category"] in taken_cats and t["id"] not in taken_ids]
        if not suggested:
            suggested = [t for t in tests.values() if t["id"] not in taken_ids][:10]
        render_test_list(chat_id, message_id, suggested, "🎯 آزمون‌های پیشنهادی برای شما:", "tests_home")

    elif data_cb == "tests_categories":
        show_categories(chat_id, message_id)

    elif data_cb == "tests_all":
        tests = load_tests()
        all_tests = sorted(tests.values(), key=lambda t: t.get("created_at", ""), reverse=True)
        render_test_list(chat_id, message_id, all_tests, "📋 همه آزمون‌ها:", "tests_home")

    elif data_cb.startswith("cat:"):
        cat_key = data_cb.split(":", 1)[1]
        tests = load_tests()
        cat_tests = [t for t in tests.values() if t["category"] == cat_key]
        render_test_list(chat_id, message_id, cat_tests, f"{CATEGORIES.get(cat_key, cat_key)}:", "tests_categories")

    elif data_cb == "tests_inprogress":
        tests = load_tests()
        items = [tests[tid] for tid in user["in_progress"].keys() if tid in tests]
        render_test_list(chat_id, message_id, items, "⏳ آزمون‌های در حال انجام:", "tests_home")

    elif data_cb == "tests_results":
        if not user["results"]:
            edit_message(chat_id, message_id, "هنوز آزمونی انجام نداده‌اید.", inline_kb([[("↩️ بازگشت", "tests_home")]]))
        else:
            rows = [
                [(f"{r['test_title']} - {result_score_label(r)} ({r['date']})", f"view_analysis:{r['id']}")]
                for r in reversed(user["results"])
            ]
            rows.append([("↩️ بازگشت", "tests_home")])
            edit_message(chat_id, message_id, "📊 نتایج آزمون‌های شما:", inline_kb(rows))

    elif data_cb == "tests_saved":
        tests = load_tests()
        items = [tests[tid] for tid in user.get("saved_tests", []) if tid in tests]
        render_test_list(chat_id, message_id, items, "⭐ آزمون‌های ذخیره‌شده:", "tests_home")

    elif data_cb == "tests_search":
        user["state"] = {"mode": "search_test", "data": {}}
        update_user(uid, user)
        edit_message(chat_id, message_id, "🔍 نام یا موضوع آزمون مورد نظر را تایپ و ارسال کنید:")

    elif data_cb.startswith("test:"):
        show_test_detail(chat_id, message_id, data_cb.split(":", 1)[1], user)

    elif data_cb.startswith("guide:"):
        tid = data_cb.split(":", 1)[1]
        tests = load_tests()
        t = tests.get(tid, {})
        guide = t.get("guide") or (
            f"این آزمون شامل {len(t.get('questions', []))} سؤال است و حدود "
            f"{t.get('time_minutes', '-')} دقیقه زمان می‌برد.\n"
            "لطفاً سؤالات را با دقت و صادقانه پاسخ دهید. پاسخ «درست» یا «غلط» وجود ندارد."
        )
        edit_message(chat_id, message_id, f"ℹ️ راهنمای آزمون\n\n{guide}", inline_kb([[("↩️ بازگشت", f"test:{tid}")]]))

    elif data_cb.startswith("save_test:"):
        tid = data_cb.split(":", 1)[1]
        if tid not in user["saved_tests"]:
            user["saved_tests"].append(tid)
            update_user(uid, user)
        answer_callback(cq_id, "⭐ آزمون ذخیره شد.")

    elif data_cb.startswith("start_test:"):
        tid = data_cb.split(":", 1)[1]
        if user_has_taken(user, tid):
            answer_callback(cq_id, "❗️ شما قبلاً این آزمون را انجام داده‌اید.", show_alert=True)
            return
        if not user.get("phone"):
            user["state"] = {"mode": "awaiting_phone", "data": {"pending_test_id": tid}}
            update_user(uid, user)
            send_message(
                chat_id,
                "📱 برای شرکت در آزمون، لطفاً ابتدا شماره تلفن خود را با دکمه زیر ارسال کنید:",
                contact_request_kb(),
            )
            return
        user["in_progress"][tid] = {"index": 0, "answers": {}}
        update_user(uid, user)
        send_question(chat_id, uid, tid, message_id)

    elif data_cb.startswith("answer:"):
        _, tid, qidx, oidx = data_cb.split(":")
        progress = user["in_progress"].get(tid)
        if progress:
            progress["answers"][qidx] = oidx
            progress["index"] = int(qidx) + 1
            update_user(uid, user)
            send_question(chat_id, uid, tid, message_id)

    elif data_cb.startswith("prevq:"):
        tid = data_cb.split(":", 1)[1]
        progress = user["in_progress"].get(tid)
        if progress and progress["index"] > 0:
            progress["index"] -= 1
            update_user(uid, user)
        send_question(chat_id, uid, tid, message_id)

    elif data_cb.startswith("nextq:"):
        tid = data_cb.split(":", 1)[1]
        progress = user["in_progress"].get(tid)
        tests = load_tests()
        total_q = len(tests.get(tid, {}).get("questions", []))
        if progress and progress["index"] < total_q:
            progress["index"] += 1
            update_user(uid, user)
        send_question(chat_id, uid, tid, message_id)

    elif data_cb.startswith("gotoempty:"):
        tid = data_cb.split(":", 1)[1]
        goto_first_empty_question(chat_id, uid, tid, message_id)

    elif data_cb.startswith("submit_test:"):
        tid = data_cb.split(":", 1)[1]
        finish_test(chat_id, uid, tid, message_id)

    elif data_cb.startswith("view_analysis:"):
        show_result_analysis(chat_id, message_id, uid, data_cb.split(":", 1)[1])

    elif data_cb.startswith("view_answers:"):
        show_result_answers(chat_id, message_id, uid, data_cb.split(":", 1)[1])

    elif data_cb in ("request_consult", "consult_freeform"):
        if require_phone_or_ask(uid, chat_id, user, "freeform"):
            user["state"] = {"mode": "consult_request", "data": {}}
            update_user(uid, user)
            send_message(chat_id, "💬 لطفاً موضوع و توضیح مختصری از درخواست مشاوره خود را بنویسید و ارسال کنید:", back_kb())

    elif data_cb.startswith("book_type:"):
        type_key = data_cb.split(":", 1)[1]
        answer_callback(cq_id)
        start_booking_time(uid, chat_id, user, type_key)

    elif data_cb.startswith("approve_booking:") or data_cb.startswith("reject_booking:"):
        if is_admin(uid):
            handle_booking_decision(uid, chat_id, message_id, data_cb)

    elif data_cb.startswith("claim_consult:") or data_cb.startswith("claim_support:"):
        handle_claim(uid, chat_id, message_id, data_cb, user)

    elif data_cb.startswith("rate:"):
        handle_rating(uid, chat_id, message_id, data_cb)

    elif data_cb == "delete_my_data":
        send_message(chat_id, "⚠️ مطمئنی می‌خوای همه‌ی اطلاعاتت (پروفایل، نتایج آزمون‌ها، شماره تلفن) از ربات کامل پاک بشه؟ این کار غیرقابل بازگشته.", inline_kb([
            [("✅ بله، همه چیز رو پاک کن", "delete_my_data_confirm")],
            [("❌ نه، بی‌خیال", "delete_my_data_cancel")],
        ]))

    elif data_cb == "delete_my_data_confirm":
        users = load_users()
        users.pop(str(uid), None)
        save_users(users)
        send_message(chat_id, "🗑 همه‌ی اطلاعات شما پاک شد. هر وقت خواستید، با /start می‌تونید دوباره شروع کنید.")

    elif data_cb == "delete_my_data_cancel":
        edit_message(chat_id, message_id, "لغو شد. اطلاعات شما دست‌نخورده باقی موند. ✅")

    elif data_cb.startswith("canceltest:"):
        tid = data_cb.split(":", 1)[1]
        edit_message(chat_id, message_id, "⚠️ مطمئنی می‌خوای این آزمون رو لغو کنی؟ پاسخ‌هایی که تا الان دادی از بین می‌رن.", inline_kb([
            [("✅ بله، لغو کن", f"canceltest_confirm:{tid}")],
            [("↩️ نه، ادامه بده", f"test:{tid}")],
        ]))

    elif data_cb.startswith("canceltest_confirm:"):
        tid = data_cb.split(":", 1)[1]
        user["in_progress"].pop(tid, None)
        update_user(uid, user)
        edit_message(chat_id, message_id, "❌ آزمون لغو شد.", inline_kb([[("↩️ بازگشت", "tests_home")]]))

    elif data_cb.startswith("delresult:"):
        rid = data_cb.split(":", 1)[1]
        edit_message(chat_id, message_id, "⚠️ مطمئنی می‌خوای این نتیجه رو حذف کنی؟", inline_kb([
            [("✅ بله، حذف کن", f"delresult_confirm:{rid}")],
            [("↩️ نه", f"view_analysis:{rid}")],
        ]))

    elif data_cb.startswith("delresult_confirm:"):
        rid = data_cb.split(":", 1)[1]
        user["results"] = [r for r in user["results"] if r["id"] != rid]
        update_user(uid, user)
        edit_message(chat_id, message_id, "🗑 نتیجه حذف شد.", inline_kb([[("↩️ بازگشت", "tests_home")]]))

    elif data_cb.startswith("mood:"):
        handle_mood_selection(uid, chat_id, message_id, data_cb)

    elif data_cb == "mood_trend":
        show_mood_trend(chat_id, message_id, user)

    elif data_cb == "mood_reminder_on":
        user["daily_reminder"] = True
        update_user(uid, user)
        answer_callback(cq_id, "🔔 یادآوری روزانه فعال شد.")

    elif data_cb == "mood_reminder_off":
        user["daily_reminder"] = False
        update_user(uid, user)
        answer_callback(cq_id, "🔕 یادآوری روزانه غیرفعال شد.")

    elif data_cb == "show_terms":
        edit_message(chat_id, message_id, TERMS_TEXT, inline_kb([[("↩️ بازگشت", "legal_home")]]))

    elif data_cb == "show_privacy":
        edit_message(chat_id, message_id, PRIVACY_TEXT, inline_kb([[("↩️ بازگشت", "legal_home")]]))

    elif data_cb == "mood_open":
        show_mood_checkin(chat_id, user)

    elif data_cb == "legal_home":
        show_legal_home(chat_id, message_id)

# ====================================================================
# گفتگوی دوطرفه ادمین ↔ کاربر (برای درخواست مشاوره و تیکت پشتیبانی)
# ====================================================================
def kind_store(kind):
    if kind == "consult":
        return load_consultations, save_consultations
    return load_support, save_support

def handle_claim(uid, chat_id, message_id, data_cb, user):
    kind = "consult" if data_cb.startswith("claim_consult:") else "support"
    rec_id = data_cb.split(":", 1)[1]
    load_fn, save_fn = kind_store(kind)
    records = load_fn()
    rec = records.get(rec_id)
    if not rec:
        send_message(chat_id, "این درخواست دیگر موجود نیست.")
        return
    if rec.get("status") == "closed":
        send_message(chat_id, "این گفتگو قبلاً بسته شده است.")
        return
    if rec.get("status") == "in_progress" and str(rec.get("admin_id")) != str(uid):
        send_message(chat_id, f"⛔️ این درخواست در حال حاضر توسط ادمین دیگری در حال پاسخگویی است.")
        return

    rec["status"] = "in_progress"
    rec["admin_id"] = str(uid)
    save_fn(records)

    target_uid = rec["uid"]
    user["admin_state"] = {
        "mode": "chat_active", "menu": user["admin_state"].get("menu"),
        "data": {"kind": kind, "id": rec_id, "target_uid": target_uid},
    }
    update_user(uid, user)
    send_message(
        chat_id,
        f"💬 گفتگو با {rec['name']} شروع شد. هر پیامی که بفرستی مستقیم براش ارسال می‌شه.\n"
        "برای پایان گفتگو، دکمه زیر رو بزن.",
        end_chat_kb(),
    )

    target_users = load_users()
    target_user = target_users.get(target_uid)
    if target_user:
        target_user["state"] = {"mode": "chatting_with_admin", "data": {"kind": kind, "id": rec_id, "admin_id": str(uid)}}
        save_users(target_users)
    kind_label = "مشاوره" if kind == "consult" else "پشتیبانی"
    send_message(
        target_uid,
        f"💬 تیم مانا مایند گفتگوی {kind_label} شما رو شروع کرد. هر پیامی بفرستی مستقیم دریافت می‌کنه.\n"
        "هر وقت خواستی، با دکمه زیر گفتگو رو تموم کن.",
        end_chat_kb(),
    )

def handle_user_chat_message(uid, chat_id, text, user, message):
    info = user["state"].get("data", {})
    kind = info.get("kind")
    rec_id = info.get("id")
    admin_id = info.get("admin_id")

    if text == "🔚 پایان گفتگو":
        end_chat(kind, rec_id, ended_by="user")
        return

    if contains_crisis_language(text):
        send_message(chat_id, CRISIS_RESOURCE_TEXT)

    if admin_id:
        name = f"{user.get('first_name','')} {user.get('last_name','')}".strip()
        flag = "🚨 " if contains_crisis_language(text) else ""
        relay_content(admin_id, message, text_prefix=f"{flag}👤 {name}:")
    else:
        send_message(chat_id, "این گفتگو دیگر فعال نیست.", main_menu_keyboard())
        user["state"] = {"mode": None, "data": {}}
        update_user(uid, user)

def handle_admin_chat_message(uid, chat_id, text, user, message):
    info = user["admin_state"].get("data", {})
    kind = info.get("kind")
    rec_id = info.get("id")
    target_uid = info.get("target_uid")

    if text == "🔚 پایان گفتگو":
        end_chat(kind, rec_id, ended_by="admin")
        return

    if target_uid:
        relay_content(target_uid, message, text_prefix="👩‍⚕️ تیم مانا مایند:")
    else:
        send_message(chat_id, "این گفتگو دیگر فعال نیست.")
        user["admin_state"] = {"mode": None, "menu": "admin_main", "data": {}}
        update_user(uid, user)

def end_chat(kind, rec_id, ended_by):
    load_fn, save_fn = kind_store(kind)
    records = load_fn()
    rec = records.get(rec_id)
    if not rec:
        return
    rec["status"] = "closed"
    save_fn(records)

    admin_id = rec.get("admin_id")
    target_uid = rec.get("uid")

    users = load_users()
    if admin_id and admin_id in users:
        users[admin_id]["admin_state"] = {"mode": None, "menu": "admin_main", "data": {}}
    if target_uid and target_uid in users:
        users[target_uid]["state"] = {"mode": None, "data": {}}
    save_users(users)

    if admin_id:
        send_message(admin_id, "🔚 گفتگو پایان یافت.", admin_main_kb())
    if target_uid:
        kind_label = "مشاوره" if kind == "consult" else "پشتیبانی"
        send_message(
            target_uid,
            f"🔚 گفتگوی {kind_label} به پایان رسید.\n\n⭐ لطفاً به کیفیت پاسخ‌ها امتیاز بدید:",
            star_rating_kb(kind, rec_id),
        )

def handle_rating(uid, chat_id, message_id, data_cb):
    _, kind, rec_id, score = data_cb.split(":")
    load_fn, save_fn = kind_store(kind)
    records = load_fn()
    rec = records.get(rec_id)
    if not rec:
        edit_message(chat_id, message_id, "این مورد پیدا نشد.")
        return
    rec["rating"] = int(score)
    save_fn(records)
    edit_message(chat_id, message_id, f"🙏 ممنون از امتیازی که دادید: {'⭐' * int(score)}")
    send_message(chat_id, "🏠 منوی اصلی", main_menu_keyboard())
    if rec.get("admin_id"):
        send_message(rec["admin_id"], f"📩 کاربر {rec['name']} به گفتگو امتیاز {score} ستاره داد.")

# ====================================================================
# پنل ادمین — تماماً دکمه‌ای (Reply Keyboard)
# ====================================================================
ADMIN_BACK_MAP = {
    "admin_manage_tests_list": "admin_main",
    "admin_test_detail": "admin_manage_tests_list",
    "admin_edu_menu": "admin_main",
    "admin_edu_list": "admin_edu_menu",
    "admin_edu_detail": "admin_edu_list",
    "admin_consult_list": "admin_main",
    "admin_consult_detail": "admin_consult_list",
    "admin_consult_clear_confirm": "admin_consult_list",
    "admin_support_list": "admin_main",
    "admin_support_detail": "admin_support_list",
    "admin_support_clear_confirm": "admin_support_list",
    "admin_join_menu": "admin_main",
    "admin_join_list": "admin_join_menu",
    "admin_join_detail": "admin_join_list",
    "admin_exercise_menu": "admin_main",
    "admin_exercise_list": "admin_exercise_menu",
    "admin_exercise_detail": "admin_exercise_list",
    "admin_gift_menu": "admin_main",
    "admin_gift_list": "admin_gift_menu",
    "admin_gift_detail": "admin_gift_list",
    "admin_booking_list": "admin_main",
    "admin_booking_detail": "admin_booking_list",
    "admin_booking_clear_confirm": "admin_booking_list",
    "admin_product_menu": "admin_main",
    "admin_product_list": "admin_product_menu",
    "admin_product_detail": "admin_product_list",
    "admin_order_list": "admin_main",
    "admin_order_detail": "admin_order_list",
    "admin_order_clear_confirm": "admin_order_list",
}

SCORE_KB = reply_kb([["0", "1", "2"], ["3", "4", "5"], ["↩️ لغو و بازگشت به منو"]])
TIME_KB = reply_kb([["3", "5", "10"], ["15", "20", "30"], ["↩️ لغو و بازگشت به منو"]])

def admin_menu_text():
    settings = load_settings()
    join_status = "فعال ✅" if settings.get("force_join") else "غیرفعال ❌"
    tests_all = load_tests()
    users_all = load_users()
    pending_consult = sum(1 for c in load_consultations().values() if c.get("status") == "pending")
    pending_support = sum(1 for t in load_support().values() if t.get("status") == "pending")
    return (
        "🛠 ✨ پنل مدیریت مانا مایند ✨\n"
        "━━━━━━━━━━━━━━━━━\n"
        f"👥 کاربران: {len(users_all)}   🧠 آزمون‌ها: {len(tests_all)}\n"
        f"🔗 جوین اجباری: {join_status}\n"
        f"📥 مشاوره در انتظار: {pending_consult}   🎫 تیکت باز: {pending_support}\n"
        "━━━━━━━━━━━━━━━━━\n"
        "یکی از گزینه‌های زیر رو انتخاب کن 👇"
    )

def admin_main_kb():
    return reply_kb([
        ["➕ افزودن آزمون جدید", "📋 مدیریت آزمون‌ها"],
        ["📚 مدیریت محتوای آموزشی", "✏️ ویرایش متن خدمات"],
        ["🧘 مدیریت تمرین‌ها", "🎁 مدیریت هدایا"],
        ["📥 درخواست‌های مشاوره", "🎫 تیکت‌های پشتیبانی"],
        ["📅 رزروهای مشاوره", "🛍 مدیریت محصولات"],
        ["📦 سفارش‌ها", "🔗 تنظیم جوین اجباری"],
        ["📊 آمار کلی", "👥 مدیریت کاربران"],
        ["📢 ارسال پیام همگانی"],
        ["🔒 اطلاعات محرمانه"],
        ["↩️ خروج از پنل ادمین"],
    ])

def go_admin_menu(chat_id, uid, user, menu):
    user["admin_state"]["menu"] = menu
    user["admin_state"]["mode"] = None
    user["admin_state"]["data"] = {}
    update_user(uid, user)
    render_admin_menu_screen(chat_id, menu)

def render_admin_menu_screen(chat_id, menu):
    if menu == "admin_main":
        send_message(chat_id, admin_menu_text(), admin_main_kb())

    elif menu == "admin_manage_tests_list":
        tests = load_tests()
        if not tests:
            send_message(chat_id, "هنوز آزمونی ثبت نشده.", back_kb())
        else:
            rows = [[t["title"]] for t in tests.values()] + [["↩️ بازگشت"]]
            send_message(chat_id, "📋 روی یک آزمون بزن تا مدیریتش کنی:", reply_kb(rows))

    elif menu == "admin_edu_menu":
        send_message(chat_id, "📚 مدیریت محتوای آموزشی", reply_kb([["➕ افزودن محتوا", "📋 لیست / حذف محتوا"], ["↩️ بازگشت"]]))

    elif menu == "admin_edu_list":
        content = load_content()
        if not content:
            send_message(chat_id, "هنوز محتوایی ثبت نشده.", back_kb())
        else:
            rows = [[c["title"]] for c in content.values()] + [["↩️ بازگشت"]]
            send_message(chat_id, "📋 روی یک محتوا بزن:", reply_kb(rows))

    elif menu == "admin_exercise_menu":
        send_message(chat_id, "🧘 مدیریت تمرین‌ها", reply_kb([["➕ افزودن تمرین", "📋 لیست / حذف تمرین‌ها"], ["↩️ بازگشت"]]))

    elif menu == "admin_exercise_list":
        exercises = load_exercises()
        if not exercises:
            send_message(chat_id, "هنوز تمرینی ثبت نشده.", back_kb())
        else:
            rows = [[e["title"]] for e in exercises.values()] + [["↩️ بازگشت"]]
            send_message(chat_id, "📋 روی یک تمرین بزن:", reply_kb(rows))

    elif menu == "admin_gift_menu":
        send_message(chat_id, "🎁 مدیریت هدایا", reply_kb([["➕ افزودن هدیه", "📋 لیست / حذف هدایا"], ["↩️ بازگشت"]]))

    elif menu == "admin_gift_list":
        gifts = load_gifts()
        if not gifts:
            send_message(chat_id, "هنوز هدیه‌ای ثبت نشده.", back_kb())
        else:
            rows = [[g["title"]] for g in gifts.values()] + [["↩️ بازگشت"]]
            send_message(chat_id, "📋 روی یک هدیه بزن:", reply_kb(rows))

    elif menu == "admin_booking_list":
        bookings = load_bookings()
        if not bookings:
            send_message(chat_id, "هیچ رزروی ثبت نشده.", back_kb())
        else:
            rows = [[record_label(b)] for b in reversed(list(bookings.values()))]
            rows.append(["🗑 پاک کردن کل تاریخچه رزروها"])
            rows.append(["↩️ بازگشت"])
            send_message(chat_id, f"📅 رزروهای مشاوره ({len(bookings)} مورد) — روی یکی بزن:", reply_kb(rows))

    elif menu == "admin_booking_clear_confirm":
        send_message(
            chat_id,
            f"⚠️ مطمئنی می‌خوای کل تاریخچه‌ی {len(load_bookings())} رزرو رو پاک کنی؟ این کار غیرقابل بازگشته.",
            reply_kb([["✅ بله، پاک کن"], ["❌ نه، بی‌خیال"]]),
        )

    elif menu == "admin_product_menu":
        send_message(chat_id, "🛍 مدیریت محصولات", reply_kb([["➕ افزودن محصول", "📋 لیست / حذف محصولات"], ["↩️ بازگشت"]]))

    elif menu == "admin_product_list":
        products = load_products()
        if not products:
            send_message(chat_id, "هنوز محصولی ثبت نشده.", back_kb())
        else:
            rows = [[p["title"]] for p in products.values()] + [["↩️ بازگشت"]]
            send_message(chat_id, "📋 روی یک محصول بزن:", reply_kb(rows))

    elif menu == "admin_order_list":
        orders = load_orders()
        if not orders:
            send_message(chat_id, "هنوز سفارشی ثبت نشده.", back_kb())
        else:
            rows = [[f"{o['product_title']} - {o['name']} ({o['date']})"] for o in reversed(list(orders.values()))]
            rows.append(["🗑 پاک کردن کل تاریخچه سفارش‌ها"])
            rows.append(["↩️ بازگشت"])
            send_message(chat_id, f"📦 سفارش‌ها ({len(orders)} مورد) — روی یکی بزن:", reply_kb(rows))

    elif menu == "admin_order_clear_confirm":
        send_message(
            chat_id,
            f"⚠️ مطمئنی می‌خوای کل تاریخچه‌ی {len(load_orders())} سفارش رو پاک کنی؟ این کار غیرقابل بازگشته.",
            reply_kb([["✅ بله، پاک کن"], ["❌ نه، بی‌خیال"]]),
        )

    elif menu == "admin_consult_list":
        consults = load_consultations()
        if not consults:
            send_message(chat_id, "هیچ درخواست مشاوره‌ای ثبت نشده.", back_kb())
        else:
            rows = [[record_label(c)] for c in reversed(list(consults.values()))]
            rows.append(["🗑 پاک کردن کل تاریخچه مشاوره"])
            rows.append(["↩️ بازگشت"])
            send_message(chat_id, f"📥 درخواست‌های مشاوره ({len(consults)} مورد) — روی یکی بزن:", reply_kb(rows))

    elif menu == "admin_support_list":
        tickets = load_support()
        if not tickets:
            send_message(chat_id, "هیچ تیکتی ثبت نشده.", back_kb())
        else:
            rows = [[record_label(t)] for t in reversed(list(tickets.values()))]
            rows.append(["🗑 پاک کردن کل تاریخچه پشتیبانی"])
            rows.append(["↩️ بازگشت"])
            send_message(chat_id, f"🎫 تیکت‌های پشتیبانی ({len(tickets)} مورد) — روی یکی بزن:", reply_kb(rows))

    elif menu == "admin_consult_clear_confirm":
        send_message(
            chat_id,
            f"⚠️ مطمئنی می‌خوای کل تاریخچه‌ی {len(load_consultations())} درخواست مشاوره رو پاک کنی؟ این کار غیرقابل بازگشته.",
            reply_kb([["✅ بله، پاک کن"], ["❌ نه، بی‌خیال"]]),
        )

    elif menu == "admin_support_clear_confirm":
        send_message(
            chat_id,
            f"⚠️ مطمئنی می‌خوای کل تاریخچه‌ی {len(load_support())} تیکت پشتیبانی رو پاک کنی؟ این کار غیرقابل بازگشته.",
            reply_kb([["✅ بله، پاک کن"], ["❌ نه، بی‌خیال"]]),
        )

    elif menu == "admin_join_menu":
        settings = load_settings()
        status = "فعال ✅" if settings.get("force_join") else "غیرفعال ❌"
        channels = settings.get("channels", [])
        ch_list = "\n".join(f"  • {c['title']} ({c['username']})" for c in channels) or "  (کانالی تنظیم نشده)"
        text = (
            "🔗 تنظیم جوین اجباری\n"
            "━━━━━━━━━━━━━━\n"
            f"وضعیت: {status}\n\n"
            f"📋 کانال‌های فعلی:\n{ch_list}"
        )
        send_message(chat_id, text, reply_kb([
            ["⚡️ فعال / غیرفعال‌سازی"],
            ["➕ افزودن کانال", "📋 لیست / حذف کانال‌ها"],
            ["🧪 تست اتصال به کانال‌ها"],
            ["↩️ بازگشت"],
        ]))

    elif menu == "admin_join_list":
        settings = load_settings()
        channels = settings.get("channels", [])
        if not channels:
            send_message(chat_id, "هنوز کانالی اضافه نشده.", back_kb())
        else:
            rows = [[c["title"]] for c in channels] + [["↩️ بازگشت"]]
            send_message(chat_id, "📋 روی کانالی بزن که می‌خوای حذفش کنی:", reply_kb(rows))

    else:
        send_message(chat_id, admin_menu_text(), admin_main_kb())

# ---------------- lookup helpers ----------------
def find_test_by_title(title):
    for t in load_tests().values():
        if t["title"] == title:
            return t
    return None

def find_content_by_title(title):
    for c in load_content().values():
        if c["title"] == title:
            return c
    return None

def find_exercise_by_title(title):
    for e in load_exercises().values():
        if e["title"] == title:
            return e
    return None

def find_gift_by_title(title):
    for g in load_gifts().values():
        if g["title"] == title:
            return g
    return None

def find_booking_by_label(label):
    for bid, b in load_bookings().items():
        if record_label(b) == label:
            return bid, b
    return None, None

def find_product_by_title(title):
    for p in load_products().values():
        if p["title"] == title:
            return p
    return None

def find_order_by_label(label):
    for oid, o in load_orders().items():
        if f"{o['product_title']} - {o['name']} ({o['date']})" == label:
            return oid, o
    return None, None

def find_channel_by_title(title):
    for c in load_settings().get("channels", []):
        if c["title"] == title:
            return c
    return None

def record_label(rec):
    prefix = "🚨 " if rec.get("is_crisis") else ""
    return f"{prefix}{rec['name']} ({rec['date']})"

def find_consult_by_label(label):
    for cid, c in load_consultations().items():
        if record_label(c) == label:
            return cid, c
    return None, None

def find_support_by_label(label):
    for tid, t in load_support().items():
        if record_label(t) == label:
            return tid, t
    return None, None

# ---------------- افزودن آزمون: عنوان/توضیح/دسته/زمان ----------------
def start_admin_add_test(uid, chat_id, user):
    user["admin_state"] = {"mode": "admin_new_title", "menu": "admin_main", "data": {"questions": []}}
    update_user(uid, user)
    send_message(chat_id, "✏️ عنوان آزمون جدید را وارد کنید:", remove_kb())

def admin_category_kb():
    items = list(CATEGORIES.items())
    rows = []
    for i in range(0, len(items), 2):
        row = [items[i][1]]
        if i + 1 < len(items):
            row.append(items[i + 1][1])
        rows.append(row)
    rows.append(["↩️ لغو و بازگشت به منو"])
    return reply_kb(rows)

def admin_category_kb_with_skip():
    items = list(CATEGORIES.items())
    rows = [["⏭ بدون دسته‌بندی"]]
    for i in range(0, len(items), 2):
        row = [items[i][1]]
        if i + 1 < len(items):
            row.append(items[i + 1][1])
        rows.append(row)
    rows.append(["↩️ لغو و بازگشت به منو"])
    return reply_kb(rows)

def ask_related_link(uid, chat_id, user):
    user["admin_state"]["mode"] = "admin_related_link_wait"
    update_user(uid, user)
    send_message(
        chat_id,
        "🔗 اگه پست یا محتوای مرتبطی تو کانال داری، لینکش رو بفرست تا دکمه «📖 مطالعه بیشتر» زیر این آزمون نشون داده بشه.\n"
        "اگه نداری، رد کن.",
        reply_kb([["⏭ رد کردن"], ["↩️ لغو و بازگشت به منو"]]),
    )

def admin_finalize_test(uid, chat_id, user):
    data = user["admin_state"]["data"]
    test_id = str(uuid.uuid4())[:8]
    raw_max = sum(max(o["score"] for o in q["options"]) for q in data["questions"])
    test = {
        "id": test_id,
        "title": data["title"],
        "description": data["description"],
        "category": data["category"],
        "time_minutes": data.get("time_minutes", 5),
        "questions": data["questions"],
        "created_at": now_str(),
        "created_by": uid,
        "is_new": True,
        "participation_count": 0,
        "ranges": data.get("ranges", []),
        "related_post_link": data.get("related_post_link"),
    }
    tests = load_tests()
    tests[test_id] = test
    save_tests(tests)

    ranges_summary = ""
    if test.get("ranges"):
        lines = [f"  • {r['min']} تا {r['max']}: {r['text'][:40]}{'...' if len(r['text']) > 40 else ''}" for r in test["ranges"]]
        ranges_summary = "\n\n📝 متن‌های نتیجه بر اساس بازه:\n" + "\n".join(lines)

    summary = (
        f"✅ آزمون «{test['title']}» با موفقیت ساخته شد!\n\n"
        f"━━━━━━━━━━━━━━\n"
        f"📁 دسته: {CATEGORIES.get(test['category'], test['category'])}\n"
        f"📝 تعداد سؤالات: {len(test['questions'])}\n"
        f"⏱ زمان تقریبی: {test.get('time_minutes')} دقیقه\n"
        f"📐 حداکثر نمره: {raw_max}"
        f"{ranges_summary}"
    )
    send_message(chat_id, summary, admin_main_kb())
    go_admin_menu(chat_id, uid, user, "admin_main")

# ---------------- روتر اصلی پنل ادمین ----------------
def admin_route(uid, chat_id, text, user, message=None):
    astate = user["admin_state"]
    mode = astate.get("mode")
    menu = astate.get("menu") or "admin_main"
    data = astate.setdefault("data", {})

    # لغو عمومی در هر مرحله از ویزارد آزمون‌سازی
    if mode and text == "↩️ لغو و بازگشت به منو":
        go_admin_menu(chat_id, uid, user, "admin_main")
        return

    # ---------------- ویزارد افزودن آزمون ----------------
    if mode == "admin_new_title":
        data["title"] = text.strip()
        astate["mode"] = "admin_new_desc"
        update_user(uid, user)
        send_message(chat_id, "📝 توضیح کوتاهی برای این آزمون بنویسید:")
        return

    if mode == "admin_new_desc":
        data["description"] = text.strip()
        astate["mode"] = "admin_new_category_wait"
        update_user(uid, user)
        send_message(chat_id, "📁 دسته‌بندی این آزمون را انتخاب کنید:", admin_category_kb())
        return

    if mode == "admin_new_category_wait":
        cat_key = LABEL_TO_CATEGORY.get(text.strip())
        if not cat_key:
            send_message(chat_id, "لطفاً یکی از دکمه‌های دسته‌بندی را انتخاب کنید.", admin_category_kb())
            return
        data["category"] = cat_key
        astate["mode"] = "admin_new_time"
        update_user(uid, user)
        send_message(chat_id, "⏱ زمان تقریبی آزمون (به دقیقه) را انتخاب یا تایپ کنید:", TIME_KB)
        return

    if mode == "admin_new_time":
        if not text.strip().isdigit():
            send_message(chat_id, "لطفاً فقط عدد وارد کنید (یا یکی از دکمه‌ها را بزنید):", TIME_KB)
            return
        data["time_minutes"] = int(text.strip())
        astate["mode"] = "admin_new_q_text"
        update_user(uid, user)
        send_message(
            chat_id,
            f"❓ متن سؤال شماره {len(data['questions']) + 1} را بنویسید:\n\n"
            "💡 اختیاری: اگه این سؤال متعلق به یه خرده‌مقیاس خاصه، اول متن با این فرمت شروع کن:\n"
            "[خرده‌مقیاس: اضطراب] متن سؤال...",
            remove_kb(),
        )
        return

    if mode == "admin_new_q_text":
        raw = text.strip()
        subscale = None
        m = re.match(r"^\[\s*خرده[‌ ]?مقیاس\s*:\s*(.+?)\s*\]\s*(.+)$", raw, re.DOTALL)
        if m:
            subscale = m.group(1).strip()
            raw = m.group(2).strip()
        data["current_question"] = {"text": raw, "subscale": subscale}
        astate["mode"] = "admin_new_q_options"
        update_user(uid, user)
        send_message(
            chat_id,
            "📝 حالا گزینه‌های این سؤال را بفرست — هر گزینه در یک خط، بدون نمره "
            "(نمره‌ها رو الان یکی‌یکی تعیین می‌کنیم):\n\n"
            "مثال:\nخیلی کم\nکم\nمتوسط\nزیاد\nخیلی زیاد",
        )
        return

    if mode == "admin_new_q_options":
        labels = [line.strip() for line in text.split("\n") if line.strip()]
        if len(labels) < 2:
            send_message(chat_id, "❗️ حداقل ۲ گزینه لازم است. گزینه‌ها را هر کدام در یک خط بفرست:")
            return
        data["current_question"]["options_pending"] = labels
        data["current_question"]["scores"] = []
        astate["mode"] = "admin_new_q_score"
        update_user(uid, user)
        first_label = labels[0]
        send_message(chat_id, f"🎯 امتیاز گزینه «{first_label}» چقدره؟\nهر عددی می‌تونه باشه (حتی 0 یا منفی) — از دکمه‌ها انتخاب کن یا خودت تایپ کن:", SCORE_KB)
        return

    if mode == "admin_new_q_score":
        if not text.strip().lstrip("-").isdigit():
            send_message(chat_id, "لطفاً یک عدد وارد کن یا از دکمه‌های زیر انتخاب کن:", SCORE_KB)
            return
        score = int(text.strip())
        cq = data["current_question"]
        cq["scores"].append(score)
        next_idx = len(cq["scores"])
        if next_idx < len(cq["options_pending"]):
            next_label = cq["options_pending"][next_idx]
            send_message(chat_id, f"🎯 امتیاز گزینه «{next_label}» چقدره؟\nهر عددی می‌تونه باشه — از دکمه‌ها انتخاب کن یا خودت تایپ کن:", SCORE_KB)
        else:
            options = [{"text": lbl, "score": sc} for lbl, sc in zip(cq["options_pending"], cq["scores"])]
            new_q = {"text": cq["text"], "options": options}
            if cq.get("subscale"):
                new_q["subscale"] = cq["subscale"]
            data["questions"].append(new_q)
            data.pop("current_question", None)
            astate["mode"] = "admin_new_q_more"
            update_user(uid, user)
            subscale_note = f" (خرده‌مقیاس: {new_q['subscale']})" if new_q.get("subscale") else ""
            send_message(
                chat_id,
                f"✅ سؤال {len(data['questions'])} با {len(options)} گزینه ثبت شد{subscale_note}.",
                reply_kb([["➕ افزودن سؤال بعدی"], ["✅ پایان و ذخیره آزمون"], ["↩️ لغو و بازگشت به منو"]]),
            )
        update_user(uid, user)
        return

    if mode == "admin_new_q_more":
        if text == "➕ افزودن سؤال بعدی":
            astate["mode"] = "admin_new_q_text"
            update_user(uid, user)
            send_message(
                chat_id,
                f"❓ متن سؤال شماره {len(data['questions']) + 1} را بنویسید:\n\n"
                "💡 اختیاری: [خرده‌مقیاس: نام] رو اول متن بذار اگه این سؤال به یه خرده‌مقیاس تعلق داره.",
                remove_kb(),
            )
        elif text == "✅ پایان و ذخیره آزمون":
            if not data["questions"]:
                send_message(chat_id, "حداقل باید یک سؤال اضافه کنید.")
                return
            raw_max = sum(max(o["score"] for o in q["options"]) for q in data["questions"])
            astate["mode"] = "admin_ranges_wait"
            update_user(uid, user)
            send_message(
                chat_id,
                f"📝 حالا اگه می‌خوای، می‌تونی متن نتیجه رو برای بازه‌های مختلف نمره تعیین کنی "
                f"(حداکثر نمره‌ی این آزمون: {raw_max}) — همه رو تو همین یک پیام بفرست، هر بازه در یک خط، به این شکل:\n\n"
                "حداقل-حداکثر: متن نتیجه\n\n"
                "مثال:\n"
                f"0-{raw_max // 3}: بهتره بیشتر مراقب خودت باشی و با یه متخصص صحبت کنی\n"
                f"{raw_max // 3 + 1}-{(raw_max * 2) // 3}: وضعیتت متوسطه، بهتره بهش توجه کنی\n"
                f"{(raw_max * 2) // 3 + 1}-{raw_max}: وضعیتت خوبه 🎉\n\n"
                "اگه نمی‌خوای این بخش رو تنظیم کنی، دکمه رد کردن رو بزن.",
                reply_kb([["⏭ رد کردن (بدون متن سفارشی)"], ["↩️ لغو و بازگشت به منو"]]),
            )
        else:
            send_message(chat_id, "یکی از دکمه‌های زیر را انتخاب کن:", reply_kb([["➕ افزودن سؤال بعدی"], ["✅ پایان و ذخیره آزمون"], ["↩️ لغو و بازگشت به منو"]]))
        return

    if mode == "admin_ranges_wait":
        if text == "⏭ رد کردن (بدون متن سفارشی)":
            data["ranges"] = []
            ask_related_link(uid, chat_id, user)
            return
        ranges = []
        bad_lines = []
        for line in [l.strip() for l in text.split("\n") if l.strip()]:
            m = re.match(r"^(-?\d+(?:\.\d+)?)\s*-\s*(-?\d+(?:\.\d+)?)\s*:\s*(.+)$", line)
            if not m:
                bad_lines.append(line)
                continue
            lo, hi, rtext = m.groups()
            ranges.append({"min": float(lo), "max": float(hi), "text": rtext.strip()})
        if not ranges:
            send_message(
                chat_id,
                "❗️ هیچ خطی با فرمت درست پیدا نشد. فرمت درست: «حداقل-حداکثر: متن»\n"
                "مثال: 0-15: بهتره مراقب خودت باشی\n\nدوباره بفرست یا رد کن.",
                reply_kb([["⏭ رد کردن (بدون متن سفارشی)"], ["↩️ لغو و بازگشت به منو"]]),
            )
            return
        data["ranges"] = ranges
        if bad_lines:
            send_message(chat_id, "⚠️ این خط‌ها فرمتشون درست نبود و نادیده گرفته شدن:\n" + "\n".join(bad_lines))
        ask_related_link(uid, chat_id, user)
        return

    if mode == "admin_related_link_wait":
        if text == "⏭ رد کردن":
            data["related_post_link"] = None
        elif text.startswith("http://") or text.startswith("https://"):
            data["related_post_link"] = text.strip()
        else:
            send_message(chat_id, "❗️ لینک باید با http:// یا https:// شروع بشه. دوباره بفرست یا رد کن.", reply_kb([["⏭ رد کردن"], ["↩️ لغو و بازگشت به منو"]]))
            return
        admin_finalize_test(uid, chat_id, user)
        return

    # ---------------- ویزارد پیام همگانی ----------------
    if mode == "admin_broadcast_wait":
        users_all = load_users()
        count = 0
        has_media = message is not None and message_has_media(message)
        for other_uid in users_all.keys():
            if has_media:
                send_message(other_uid, "📢 پیام از تیم مانا مایند:")
                relay_content(other_uid, message)
            else:
                send_message(other_uid, f"📢 پیام از تیم مانا مایند:\n\n{text}")
            count += 1
        send_message(chat_id, f"✅ پیام به {count} کاربر ارسال شد.")
        go_admin_menu(chat_id, uid, user, "admin_main")
        return

    # ---------------- ویرایش متن خدمات ----------------
    if mode == "admin_services_text_wait":
        settings = load_settings()
        settings["services_text"] = text
        save_settings(settings)
        send_message(chat_id, "✅ متن «خدمات و مزایا» به‌روزرسانی شد.")
        go_admin_menu(chat_id, uid, user, "admin_main")
        return

    # ---------------- اطلاعات محرمانه (پسورد + ارسال بک‌آپ فایل‌های JSON) ----------------
    if mode == "admin_confidential_password_wait":
        if text == "↩️ بازگشت":
            go_admin_menu(chat_id, uid, user, "admin_main")
            return
        entered = text.strip()
        astate["mode"] = None
        update_user(uid, user)
        if entered != ADMIN_SECRET_PASSWORD:
            send_message(chat_id, "❌ پسورد غلطه.", admin_main_kb())
            return
        send_message(chat_id, "✅ پسورد درست بود. در حال آماده‌سازی و ارسال فایل‌های اطلاعاتی (لحظه‌ای)...", admin_main_kb())
        send_all_json_backups(chat_id)  # فقط برای همین چت — همون ادمینی که پسورد رو درست وارد کرده
        return

    # ---------------- افزودن محتوای آموزشی ----------------
    if mode == "admin_edu_title_wait":
        data["title"] = text.strip()
        astate["mode"] = "admin_edu_body_wait"
        update_user(uid, user)
        send_message(chat_id, "📝 متن یا لینک محتوای آموزشی را وارد کنید:")
        return

    if mode == "admin_edu_body_wait":
        content = load_content()
        cid = str(uuid.uuid4())[:8]
        content[cid] = {"id": cid, "title": data["title"], "body": text, "created_at": now_str()}
        save_content(content)
        send_message(chat_id, f"✅ محتوای «{content[cid]['title']}» اضافه شد.")
        go_admin_menu(chat_id, uid, user, "admin_edu_menu")
        return

    # ---------------- افزودن تمرین ----------------
    if mode == "admin_exercise_title_wait":
        data["title"] = text.strip()
        astate["mode"] = "admin_exercise_body_wait"
        update_user(uid, user)
        send_message(chat_id, "📝 دستورالعمل کامل این تمرین را بنویسید:")
        return

    if mode == "admin_exercise_body_wait":
        data["instructions"] = text.strip()
        astate["mode"] = "admin_exercise_category_wait"
        update_user(uid, user)
        send_message(chat_id, "📁 اگه می‌خوای این تمرین به یه حوزه‌ی خاص وصل باشه (برای پیشنهاد تو «مشکل من چیست؟»)، انتخاب کن. یا رد کن:", admin_category_kb_with_skip())
        return

    if mode == "admin_exercise_category_wait":
        if text == "⏭ بدون دسته‌بندی":
            cat_key = None
        else:
            cat_key = LABEL_TO_CATEGORY.get(text.strip())
            if not cat_key:
                send_message(chat_id, "یکی از دکمه‌ها رو انتخاب کن یا رد کن.", admin_category_kb_with_skip())
                return
        exercises = load_exercises()
        eid = str(uuid.uuid4())[:8]
        exercises[eid] = {"id": eid, "title": data["title"], "instructions": data["instructions"], "category": cat_key, "created_at": now_str()}
        save_exercises(exercises)
        send_message(chat_id, f"✅ تمرین «{exercises[eid]['title']}» اضافه شد.")
        go_admin_menu(chat_id, uid, user, "admin_exercise_menu")
        return

    # ---------------- افزودن هدیه ----------------
    if mode == "admin_gift_title_wait":
        data["title"] = text.strip()
        astate["mode"] = "admin_gift_content_wait"
        update_user(uid, user)
        send_message(chat_id, "🎁 محتوای هدیه رو بنویس (متن، یا لینک فایل/دوره):")
        return

    if mode == "admin_gift_content_wait":
        data["content"] = text.strip()
        astate["mode"] = "admin_gift_type_wait"
        update_user(uid, user)
        send_message(chat_id, "🔓 این هدیه بعد از چند «آزمون» یا چند «تمرین» باز بشه؟", reply_kb([["📝 تعداد آزمون", "🔥 تعداد تمرین"], ["↩️ لغو و بازگشت به منو"]]))
        return

    if mode == "admin_gift_type_wait":
        if text == "📝 تعداد آزمون":
            data["unlock_type"] = "tests"
        elif text == "🔥 تعداد تمرین":
            data["unlock_type"] = "exercises"
        else:
            send_message(chat_id, "یکی از دکمه‌ها رو انتخاب کن:", reply_kb([["📝 تعداد آزمون", "🔥 تعداد تمرین"], ["↩️ لغو و بازگشت به منو"]]))
            return
        astate["mode"] = "admin_gift_count_wait"
        update_user(uid, user)
        send_message(chat_id, "🔢 عدد آستانه رو وارد کن (مثلاً 3):", remove_kb())
        return

    if mode == "admin_gift_count_wait":
        if not text.strip().isdigit():
            send_message(chat_id, "لطفاً فقط عدد وارد کن:")
            return
        gifts = load_gifts()
        gid = str(uuid.uuid4())[:8]
        gifts[gid] = {
            "id": gid, "title": data["title"], "content": data["content"],
            "unlock_type": data["unlock_type"], "unlock_count": int(text.strip()), "created_at": now_str(),
        }
        save_gifts(gifts)
        send_message(chat_id, f"✅ هدیه «{gifts[gid]['title']}» اضافه شد.")
        go_admin_menu(chat_id, uid, user, "admin_gift_menu")
        return

    # ---------------- افزودن محصول ----------------
    if mode == "admin_product_title_wait":
        data["title"] = text.strip()
        astate["mode"] = "admin_product_desc_wait"
        update_user(uid, user)
        send_message(chat_id, "📝 توضیح کوتاه محصول را بنویسید:")
        return

    if mode == "admin_product_desc_wait":
        data["description"] = text.strip()
        astate["mode"] = "admin_product_price_wait"
        update_user(uid, user)
        send_message(chat_id, "💰 قیمت محصول رو به تومان و فقط عدد وارد کن (مثلاً برای ۷۰ هزار تومان بنویس 70000):", remove_kb())
        return

    if mode == "admin_product_price_wait":
        cleaned = text.strip().replace(",", "").replace("،", "")
        if not cleaned.isdigit():
            send_message(chat_id, "لطفاً فقط عدد وارد کن (به تومان)، مثلاً 70000:")
            return
        data["price_toman"] = int(cleaned)
        astate["mode"] = "admin_product_delivery_wait"
        update_user(uid, user)
        send_message(chat_id, "📦 محتوایی که بعد از پرداخت موفق خودکار برای خریدار ارسال بشه رو بنویس (متن، لینک دانلود، یا هر توضیحی):")
        return

    if mode == "admin_product_delivery_wait":
        data["delivery_content"] = text.strip()
        astate["mode"] = "admin_product_photo_wait"
        update_user(uid, user)
        send_message(
            chat_id,
            "🖼 اگه می‌خوای برای این محصول عکس بذاری، عکس رو همینجا بفرست یا لینک تصویرش رو تایپ کن. "
            "اگه نمی‌خوای، رد کن.",
            reply_kb([["⏭ رد کردن (بدون عکس)"], ["↩️ لغو و بازگشت به منو"]]),
        )
        return

    if mode == "admin_product_photo_wait":
        photo = None
        if text == "⏭ رد کردن (بدون عکس)":
            photo = None
        elif message is not None and message.get("photo"):
            photo = message["photo"][-1]["file_id"]
        elif text.startswith("http://") or text.startswith("https://"):
            photo = text.strip()
        else:
            send_message(chat_id, "یه عکس بفرست، لینک تصویر بنویس، یا دکمه رد کردن رو بزن.", reply_kb([["⏭ رد کردن (بدون عکس)"], ["↩️ لغو و بازگشت به منو"]]))
            return
        products = load_products()
        pid = str(uuid.uuid4())[:8]
        products[pid] = {
            "id": pid, "title": data["title"], "description": data["description"],
            "price_toman": data["price_toman"], "delivery_content": data["delivery_content"],
            "photo": photo, "created_at": now_str(),
        }
        save_products(products)
        send_message(chat_id, f"✅ محصول «{products[pid]['title']}» با قیمت {data['price_toman']:,} تومان اضافه شد.", admin_main_kb())
        go_admin_menu(chat_id, uid, user, "admin_product_menu")
        return

    # ---------------- افزودن کانال جوین اجباری ----------------
    if mode == "admin_join_username_wait":
        data["username"] = text.strip()
        astate["mode"] = "admin_join_title_wait"
        update_user(uid, user)
        send_message(chat_id, "🏷 عنوان کانال برای نمایش به کاربر را وارد کنید:")
        return

    if mode == "admin_join_title_wait":
        data["title"] = text.strip()
        astate["mode"] = "admin_join_link_wait"
        update_user(uid, user)
        send_message(chat_id, "🔗 لینک عضویت کانال (برای دکمه عضویت) را وارد کنید:")
        return

    if mode == "admin_join_link_wait":
        data["link"] = text.strip()
        settings = load_settings()
        raw = data["username"]
        is_numeric = raw.lstrip("-").isdigit()
        settings["channels"].append({
            "id": str(uuid.uuid4())[:8],
            "username": raw,
            "chat_id": int(raw) if is_numeric else None,
            "title": data["title"],
            "link": data["link"],
        })
        save_settings(settings)
        note = "" if is_numeric else "\n\n💡 اگه بعداً چک عضویت خطا داد، کافیه یه پست تو کانال بفرستی — ربات خودش آیدی عددی دقیق کانال رو پیدا و ذخیره می‌کنه."
        send_message(
            chat_id,
            f"✅ کانال «{data['title']}» اضافه شد.\n\n"
            f"⚠️ یادت نره ربات رو ادمین همین کانال کنی تا بتونه عضویت کاربرها رو چک کنه.{note}",
        )
        go_admin_menu(chat_id, uid, user, "admin_join_menu")
        return

    if mode == "admin_join_manual_id_wait":
        raw = text.strip()
        if not raw.lstrip("-").isdigit():
            send_message(chat_id, "لطفاً یه عدد معتبر بفرست (مثلاً -1001234567890):")
            return
        chid = data.get("chid")
        settings = load_settings()
        for c in settings.get("channels", []):
            if c["id"] == chid:
                c["chat_id"] = int(raw)
        save_settings(settings)
        astate["mode"] = None
        update_user(uid, user)
        send_message(chat_id, f"✅ آیدی عددی ثبت شد: {raw}")
        go_admin_menu(chat_id, uid, user, "admin_join_list")
        return

    # ================== از اینجا به بعد: حالت منو (نه ویزارد) ==================
    if text == "↩️ خروج از پنل ادمین":
        user["admin_state"] = {"mode": None, "menu": None, "data": {}}
        update_user(uid, user)
        send_message(chat_id, "از پنل ادمین خارج شدید.", main_menu_keyboard())
        return

    if text == "↩️ بازگشت":
        parent = ADMIN_BACK_MAP.get(menu, "admin_main")
        go_admin_menu(chat_id, uid, user, parent)
        return

    if menu == "admin_main":
        if text == "➕ افزودن آزمون جدید":
            start_admin_add_test(uid, chat_id, user)
        elif text == "📋 مدیریت آزمون‌ها":
            go_admin_menu(chat_id, uid, user, "admin_manage_tests_list")
        elif text == "📚 مدیریت محتوای آموزشی":
            go_admin_menu(chat_id, uid, user, "admin_edu_menu")
        elif text == "🧘 مدیریت تمرین‌ها":
            go_admin_menu(chat_id, uid, user, "admin_exercise_menu")
        elif text == "🎁 مدیریت هدایا":
            go_admin_menu(chat_id, uid, user, "admin_gift_menu")
        elif text == "✏️ ویرایش متن خدمات":
            astate["mode"] = "admin_services_text_wait"
            update_user(uid, user)
            settings = load_settings()
            send_message(chat_id, f"متن فعلی:\n\n{settings.get('services_text','')}\n\n✏️ متن جدید را ارسال کنید:", remove_kb())
        elif text == "📥 درخواست‌های مشاوره":
            go_admin_menu(chat_id, uid, user, "admin_consult_list")
        elif text == "🎫 تیکت‌های پشتیبانی":
            go_admin_menu(chat_id, uid, user, "admin_support_list")
        elif text == "📅 رزروهای مشاوره":
            go_admin_menu(chat_id, uid, user, "admin_booking_list")
        elif text == "🛍 مدیریت محصولات":
            go_admin_menu(chat_id, uid, user, "admin_product_menu")
        elif text == "📦 سفارش‌ها":
            go_admin_menu(chat_id, uid, user, "admin_order_list")
        elif text == "🔗 تنظیم جوین اجباری":
            go_admin_menu(chat_id, uid, user, "admin_join_menu")
        elif text == "📊 آمار کلی":
            users_all = load_users()
            tests_all = load_tests()
            total_participation = sum(t.get("participation_count", 0) for t in tests_all.values())
            popular = max(tests_all.values(), key=lambda t: t.get("participation_count", 0), default=None)
            consults = load_consultations()
            supports = load_support()
            bookings = load_bookings()
            orders = load_orders()
            with_phone = sum(1 for u in users_all.values() if u.get("phone"))
            ratings = [c.get("rating") for c in list(consults.values()) + list(supports.values()) if c.get("rating")]
            avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else None

            today = datetime.now()
            active_7d = 0
            for u in users_all.values():
                ls = u.get("last_seen")
                if ls:
                    try:
                        days_ago = (today - datetime.strptime(ls, "%Y-%m-%d")).days
                        if days_ago <= 7:
                            active_7d += 1
                    except ValueError:
                        pass
            incomplete_tests = sum(len(u.get("in_progress", {})) for u in users_all.values())

            settings = load_settings()
            topic_clicks = settings.get("problem_topic_clicks", {})
            top_topic = max(topic_clicks.items(), key=lambda kv: kv[1], default=None)
            top_topic_label = CATEGORIES.get(top_topic[0], top_topic[0]) if top_topic else "-"

            stats_text = (
                "📊 ✨ آمار کلی مانا مایند ✨\n"
                "━━━━━━━━━━━━━━━━━\n"
                f"👥 کاربران: {len(users_all)}   🟢 فعال (۷ روز اخیر): {active_7d}\n"
                f"📱 با شماره ثبت‌شده: {with_phone}\n"
                "━━━━━━━━━━━━━━━━━\n"
                f"🧠 آزمون‌ها: {len(tests_all)}   ✅ انجام‌شده: {total_participation}\n"
                f"⏳ آزمون‌های نیمه‌کاره: {incomplete_tests}\n"
                f"🔥 محبوب‌ترین آزمون: {popular['title'] if popular else '-'}\n"
                f"💭 محبوب‌ترین موضوع «مشکل من چیست»: {top_topic_label}\n"
                "━━━━━━━━━━━━━━━━━\n"
                f"📚 محتوای آموزشی: {len(load_content())}\n"
                f"💬 مشاوره‌ها: {len(consults)} (باز: {sum(1 for c in consults.values() if c.get('status')=='pending')})\n"
                f"🎫 تیکت‌ها: {len(supports)} (باز: {sum(1 for t in supports.values() if t.get('status')=='pending')})\n"
                f"📅 رزروها: {len(bookings)} (در انتظار: {sum(1 for b in bookings.values() if b.get('status')=='pending')})\n"
                f"📦 سفارش‌ها: {len(orders)}\n"
                f"⭐ میانگین امتیاز پاسخگویی: {avg_rating if avg_rating else 'هنوز ثبت نشده'}"
            )
            send_message(chat_id, stats_text, admin_main_kb())
        elif text == "👥 مدیریت کاربران":
            users_all = load_users()
            u_text = f"👥 مدیریت کاربران\n━━━━━━━━━━━━━━━━━\nتعداد کل: {len(users_all)}\n\n📋 آخرین کاربران:\n\n"
            for u in list(users_all.values())[-10:]:
                phone_mark = "📱" if u.get("phone") else "❌"
                u_text += f"👤 {u.get('first_name', '')} — 🆔 {u['id']} — {phone_mark} — 📝 {len(u.get('results', []))} آزمون\n"
            send_message(chat_id, u_text, admin_main_kb())
        elif text == "📢 ارسال پیام همگانی":
            astate["mode"] = "admin_broadcast_wait"
            update_user(uid, user)
            send_message(chat_id, "📢 متن پیام همگانی را ارسال کنید:", remove_kb())
        elif text == "🔒 اطلاعات محرمانه":
            astate["mode"] = "admin_confidential_password_wait"
            update_user(uid, user)
            send_message(chat_id, "🔒 برای دسترسی به اطلاعات محرمانه، پسورد رو وارد کن:", back_kb())
        else:
            send_message(chat_id, "یکی از گزینه‌های منو را انتخاب کن 👇", admin_main_kb())
        return

    if menu == "admin_manage_tests_list":
        t = find_test_by_title(text)
        if not t:
            send_message(chat_id, "این آزمون پیدا نشد. یکی از دکمه‌ها را بزن.")
            return
        astate["menu"] = "admin_test_detail"
        astate["data"] = {"tid": t["id"]}
        update_user(uid, user)
        show_admin_test_detail(chat_id, t["id"])
        return

    if menu == "admin_test_detail":
        tid = data.get("tid")
        tests = load_tests()
        t = tests.get(tid)
        if text == "🆕/❌ تغییر وضعیت جدید" and t:
            t["is_new"] = not t.get("is_new", False)
            save_tests(tests)
            show_admin_test_detail(chat_id, tid)
        elif text == "🗑 حذف آزمون" and t:
            del tests[tid]
            save_tests(tests)
            send_message(chat_id, "🗑 آزمون حذف شد.")
            go_admin_menu(chat_id, uid, user, "admin_manage_tests_list")
        else:
            send_message(chat_id, "یکی از دکمه‌ها را انتخاب کن.")
        return

    if menu == "admin_edu_menu":
        if text == "➕ افزودن محتوا":
            astate["mode"] = "admin_edu_title_wait"
            update_user(uid, user)
            send_message(chat_id, "📝 عنوان محتوای آموزشی را وارد کنید:", remove_kb())
        elif text == "📋 لیست / حذف محتوا":
            go_admin_menu(chat_id, uid, user, "admin_edu_list")
        else:
            send_message(chat_id, "یکی از دکمه‌ها را انتخاب کن.")
        return

    if menu == "admin_edu_list":
        c = find_content_by_title(text)
        if not c:
            send_message(chat_id, "این محتوا پیدا نشد. یکی از دکمه‌ها را بزن.")
            return
        astate["menu"] = "admin_edu_detail"
        astate["data"] = {"cid": c["id"]}
        update_user(uid, user)
        send_message(chat_id, f"📚 {c['title']}\n\n{c['body']}", reply_kb([["🗑 حذف این محتوا"], ["↩️ بازگشت"]]))
        return

    if menu == "admin_edu_detail":
        cid = data.get("cid")
        if text == "🗑 حذف این محتوا":
            content = load_content()
            if cid in content:
                del content[cid]
                save_content(content)
            send_message(chat_id, "🗑 حذف شد.")
            go_admin_menu(chat_id, uid, user, "admin_edu_list")
        else:
            send_message(chat_id, "یکی از دکمه‌ها را انتخاب کن.")
        return

    if menu == "admin_exercise_menu":
        if text == "➕ افزودن تمرین":
            astate["mode"] = "admin_exercise_title_wait"
            update_user(uid, user)
            send_message(chat_id, "📝 عنوان تمرین را وارد کنید:", remove_kb())
        elif text == "📋 لیست / حذف تمرین‌ها":
            go_admin_menu(chat_id, uid, user, "admin_exercise_list")
        else:
            send_message(chat_id, "یکی از دکمه‌ها را انتخاب کن.")
        return

    if menu == "admin_exercise_list":
        e = find_exercise_by_title(text)
        if not e:
            send_message(chat_id, "این تمرین پیدا نشد. یکی از دکمه‌ها را بزن.")
            return
        astate["menu"] = "admin_exercise_detail"
        astate["data"] = {"eid": e["id"]}
        update_user(uid, user)
        cat_label = CATEGORIES.get(e.get("category"), "بدون دسته‌بندی") if e.get("category") else "بدون دسته‌بندی"
        send_message(chat_id, f"📝 {e['title']}\n\n{e['instructions']}\n\n📁 دسته: {cat_label}", reply_kb([["🗑 حذف این تمرین"], ["↩️ بازگشت"]]))
        return

    if menu == "admin_exercise_detail":
        eid = data.get("eid")
        if text == "🗑 حذف این تمرین":
            exercises = load_exercises()
            if eid in exercises:
                del exercises[eid]
                save_exercises(exercises)
            send_message(chat_id, "🗑 حذف شد.")
            go_admin_menu(chat_id, uid, user, "admin_exercise_list")
        else:
            send_message(chat_id, "یکی از دکمه‌ها را انتخاب کن.")
        return

    if menu == "admin_gift_menu":
        if text == "➕ افزودن هدیه":
            astate["mode"] = "admin_gift_title_wait"
            update_user(uid, user)
            send_message(chat_id, "🎁 عنوان هدیه را وارد کنید:", remove_kb())
        elif text == "📋 لیست / حذف هدایا":
            go_admin_menu(chat_id, uid, user, "admin_gift_list")
        else:
            send_message(chat_id, "یکی از دکمه‌ها را انتخاب کن.")
        return

    if menu == "admin_gift_list":
        g = find_gift_by_title(text)
        if not g:
            send_message(chat_id, "این هدیه پیدا نشد. یکی از دکمه‌ها را بزن.")
            return
        astate["menu"] = "admin_gift_detail"
        astate["data"] = {"gid": g["id"]}
        update_user(uid, user)
        unlock_label = f"{g['unlock_count']} {'آزمون' if g['unlock_type']=='tests' else 'تمرین'}"
        send_message(chat_id, f"🎁 {g['title']}\n\n{g['content']}\n\n🔓 شرط باز شدن: {unlock_label}", reply_kb([["🗑 حذف این هدیه"], ["↩️ بازگشت"]]))
        return

    if menu == "admin_gift_detail":
        gid = data.get("gid")
        if text == "🗑 حذف این هدیه":
            gifts = load_gifts()
            if gid in gifts:
                del gifts[gid]
                save_gifts(gifts)
            send_message(chat_id, "🗑 حذف شد.")
            go_admin_menu(chat_id, uid, user, "admin_gift_list")
        else:
            send_message(chat_id, "یکی از دکمه‌ها را انتخاب کن.")
        return

    if menu == "admin_booking_list":
        if text == "🗑 پاک کردن کل تاریخچه رزروها":
            go_admin_menu(chat_id, uid, user, "admin_booking_clear_confirm")
            return
        bid, b = find_booking_by_label(text)
        if not b:
            send_message(chat_id, "این رزرو پیدا نشد. یکی از دکمه‌ها را بزن.")
            return
        astate["menu"] = "admin_booking_detail"
        astate["data"] = {"bid": bid}
        update_user(uid, user)
        detail = (
            f"📅 رزرو مشاوره\n\nنوع: {b['type_label']}\nنام: {b['name']}\nیوزرنیم: @{b['username']}\n"
            f"آیدی: {b['uid']}\nتلفن: {b.get('phone') or 'ثبت نشده'}\nزمان ترجیحی: {b['time_pref']}\n"
            f"وضعیت: {b['status']}\nتوضیح: {b.get('note') or '-'}"
        )
        send_message(chat_id, detail, back_kb())
        return

    if menu == "admin_booking_detail":
        send_message(chat_id, "برای بازگشت، دکمه ↩️ بازگشت را بزن.", back_kb())
        return

    if menu == "admin_booking_clear_confirm":
        if text == "✅ بله، پاک کن":
            save_bookings({})
            send_message(chat_id, "🗑 تاریخچه‌ی رزروها پاک شد.")
            go_admin_menu(chat_id, uid, user, "admin_main")
        else:
            go_admin_menu(chat_id, uid, user, "admin_booking_list")
        return

    if menu == "admin_product_menu":
        if text == "➕ افزودن محصول":
            astate["mode"] = "admin_product_title_wait"
            update_user(uid, user)
            send_message(chat_id, "🛍 عنوان محصول را وارد کنید:", remove_kb())
        elif text == "📋 لیست / حذف محصولات":
            go_admin_menu(chat_id, uid, user, "admin_product_list")
        else:
            send_message(chat_id, "یکی از دکمه‌ها را انتخاب کن.")
        return

    if menu == "admin_product_list":
        p = find_product_by_title(text)
        if not p:
            send_message(chat_id, "این محصول پیدا نشد. یکی از دکمه‌ها را بزن.")
            return
        astate["menu"] = "admin_product_detail"
        astate["data"] = {"pid": p["id"]}
        update_user(uid, user)
        send_message(chat_id, f"🛍 {p['title']}\n\n{p['description']}\n\n💰 قیمت: {p['price_toman']:,} تومان\n📦 محتوای تحویل: {p.get('delivery_content','-')}\n🖼 عکس: {'دارد' if p.get('photo') else 'ندارد'}", reply_kb([["🗑 حذف این محصول"], ["↩️ بازگشت"]]))
        return

    if menu == "admin_product_detail":
        pid = data.get("pid")
        if text == "🗑 حذف این محصول":
            products = load_products()
            if pid in products:
                del products[pid]
                save_products(products)
            send_message(chat_id, "🗑 حذف شد.")
            go_admin_menu(chat_id, uid, user, "admin_product_list")
        else:
            send_message(chat_id, "یکی از دکمه‌ها را انتخاب کن.")
        return

    if menu == "admin_order_list":
        if text == "🗑 پاک کردن کل تاریخچه سفارش‌ها":
            go_admin_menu(chat_id, uid, user, "admin_order_clear_confirm")
            return
        oid, o = find_order_by_label(text)
        if not o:
            send_message(chat_id, "این سفارش پیدا نشد. یکی از دکمه‌ها را بزن.")
            return
        astate["menu"] = "admin_order_detail"
        astate["data"] = {"oid": oid}
        update_user(uid, user)
        detail = (
            f"📦 سفارش\n\nمحصول: {o['product_title']}\nقیمت: {o['price_toman']:,} تومان\nنام: {o['name']}\n"
            f"یوزرنیم: @{o['username']}\nآیدی: {o['uid']}\nتلفن: {o.get('phone') or 'ثبت نشده'}\n"
            f"وضعیت: {o['status']}\nتاریخ: {o['date']}"
        )
        send_message(chat_id, detail, back_kb())
        return

    if menu == "admin_order_detail":
        send_message(chat_id, "برای بازگشت، دکمه ↩️ بازگشت را بزن.", back_kb())
        return

    if menu == "admin_order_clear_confirm":
        if text == "✅ بله، پاک کن":
            save_orders({})
            send_message(chat_id, "🗑 تاریخچه‌ی سفارش‌ها پاک شد.")
            go_admin_menu(chat_id, uid, user, "admin_main")
        else:
            go_admin_menu(chat_id, uid, user, "admin_order_list")
        return

    if menu == "admin_consult_list":
        if text == "🗑 پاک کردن کل تاریخچه مشاوره":
            go_admin_menu(chat_id, uid, user, "admin_consult_clear_confirm")
            return
        cid, c = find_consult_by_label(text)
        if not c:
            send_message(chat_id, "این درخواست پیدا نشد. یکی از دکمه‌ها را بزن.")
            return
        astate["menu"] = "admin_consult_detail"
        astate["data"] = {"cid": cid}
        update_user(uid, user)
        detail = f"💬 درخواست مشاوره\n\nنام: {c['name']}\nیوزرنیم: @{c['username']}\nآیدی: {c['uid']}\nتاریخ: {c['date']}\n\nمتن:\n{c['text']}"
        send_message(chat_id, detail, back_kb())
        return

    if menu == "admin_consult_detail":
        send_message(chat_id, "برای بازگشت، دکمه ↩️ بازگشت را بزن.", back_kb())
        return

    if menu == "admin_consult_clear_confirm":
        if text == "✅ بله، پاک کن":
            save_consultations({})
            send_message(chat_id, "🗑 تاریخچه‌ی مشاوره پاک شد.")
            go_admin_menu(chat_id, uid, user, "admin_main")
        else:
            go_admin_menu(chat_id, uid, user, "admin_consult_list")
        return

    if menu == "admin_support_list":
        if text == "🗑 پاک کردن کل تاریخچه پشتیبانی":
            go_admin_menu(chat_id, uid, user, "admin_support_clear_confirm")
            return
        tid, t = find_support_by_label(text)
        if not t:
            send_message(chat_id, "این تیکت پیدا نشد. یکی از دکمه‌ها را بزن.")
            return
        astate["menu"] = "admin_support_detail"
        astate["data"] = {"tid": tid}
        update_user(uid, user)
        detail = f"🆘 تیکت پشتیبانی\n\nنام: {t['name']}\nیوزرنیم: @{t['username']}\nآیدی: {t['uid']}\nتاریخ: {t['date']}\n\nمتن:\n{t['text']}"
        send_message(chat_id, detail, back_kb())
        return

    if menu == "admin_support_detail":
        send_message(chat_id, "برای بازگشت، دکمه ↩️ بازگشت را بزن.", back_kb())
        return

    if menu == "admin_support_clear_confirm":
        if text == "✅ بله، پاک کن":
            save_support({})
            send_message(chat_id, "🗑 تاریخچه‌ی پشتیبانی پاک شد.")
            go_admin_menu(chat_id, uid, user, "admin_main")
        else:
            go_admin_menu(chat_id, uid, user, "admin_support_list")
        return

    if menu == "admin_join_menu":
        settings = load_settings()
        if text == "⚡️ فعال / غیرفعال‌سازی":
            settings["force_join"] = not settings.get("force_join", False)
            save_settings(settings)
            render_admin_menu_screen(chat_id, "admin_join_menu")
        elif text == "➕ افزودن کانال":
            astate["mode"] = "admin_join_username_wait"
            update_user(uid, user)
            send_message(chat_id, "🔗 آیدی عددی یا یوزرنیم کانال را وارد کنید (مثل @your_channel یا -100xxxxxxxxxx):", remove_kb())
        elif text == "📋 لیست / حذف کانال‌ها":
            go_admin_menu(chat_id, uid, user, "admin_join_list")
        elif text == "🧪 تست اتصال به کانال‌ها":
            send_message(chat_id, diagnose_join_channels(uid))
        else:
            send_message(chat_id, "یکی از دکمه‌ها را انتخاب کن.")
        return

    if menu == "admin_join_list":
        c = find_channel_by_title(text)
        if not c:
            send_message(chat_id, "این کانال پیدا نشد. یکی از دکمه‌ها را بزن.")
            return
        astate["menu"] = "admin_join_detail"
        astate["data"] = {"chid": c["id"]}
        update_user(uid, user)
        id_status = f"✅ {c['chat_id']}" if c.get("chat_id") else "❌ پیدا نشده (یوزرنیم @ استفاده می‌شه که ممکنه خطا بده)"
        send_message(
            chat_id,
            f"🔗 {c['title']}\nیوزرنیم: {c['username']}\nلینک: {c['link']}\nآیدی عددی: {id_status}",
            reply_kb([["🔢 تنظیم دستی آیدی عددی"], ["🗑 حذف این کانال"], ["↩️ بازگشت"]]),
        )
        return

    if menu == "admin_join_detail":
        chid = data.get("chid")
        if text == "🗑 حذف این کانال":
            settings = load_settings()
            settings["channels"] = [c for c in settings.get("channels", []) if c["id"] != chid]
            save_settings(settings)
            send_message(chat_id, "🗑 کانال حذف شد.")
            go_admin_menu(chat_id, uid, user, "admin_join_list")
        elif text == "🔢 تنظیم دستی آیدی عددی":
            astate["mode"] = "admin_join_manual_id_wait"
            update_user(uid, user)
            send_message(
                chat_id,
                "🔢 آیدی عددی کانال رو بفرست (یه عدد منفی طولانی، مثلاً -1001234567890).\n\n"
                "برای پیدا کردنش: یه پیام از کانال رو مستقیم برای همین ربات فوروارد کن — خودکار پیدا و ذخیره می‌شه. "
                "اگه فوروارد جواب نداد، از یه ربات دیگه مثل @RawDataBot یا ابزارهای مشابه بله برای گرفتن آیدی عددی کمک بگیر.",
                remove_kb(),
            )
        else:
            send_message(chat_id, "یکی از دکمه‌ها را انتخاب کن.")
        return

    # پیش‌فرض: بازگشت به منوی اصلی ادمین
    go_admin_menu(chat_id, uid, user, "admin_main")

def show_admin_test_detail(chat_id, tid):
    tests = load_tests()
    t = tests.get(tid)
    if not t:
        send_message(chat_id, "پیدا نشد.")
        return
    raw_max = sum(max(o["score"] for o in q["options"]) for q in t["questions"]) if t.get("questions") else 0
    ranges_block = ""
    if t.get("ranges"):
        lines = [f"  • {r['min']} تا {r['max']}: {r['text'][:35]}{'...' if len(r['text']) > 35 else ''}" for r in t["ranges"]]
        ranges_block = "\n📝 بازه‌های نتیجه:\n" + "\n".join(lines)
    text = (
        f"🧠 {t['title']}\n"
        f"━━━━━━━━━━━━━━\n"
        f"{t['description']}\n\n"
        f"📁 دسته: {CATEGORIES.get(t['category'], t['category'])}\n"
        f"📝 سؤالات: {len(t['questions'])}   ⏱ {t.get('time_minutes', '-')} دقیقه\n"
        f"📐 حداکثر نمره: {raw_max}\n"
        f"🙋 مشارکت: {t.get('participation_count', 0)} نفر\n"
        f"🆕 وضعیت جدید: {'بله ✅' if t.get('is_new') else 'خیر'}"
        f"{ranges_block}"
    )
    send_message(chat_id, text, reply_kb([["🆕/❌ تغییر وضعیت جدید"], ["🗑 حذف آزمون"], ["↩️ بازگشت"]]))

# ====================================================================
# حلقه اصلی
# ====================================================================
def check_daily_reminder():
    """اگه ساعت یادآوری رسیده و امروز هنوز نفرستادیم، به کاربرهای مشترک پیام یادآوری بفرست."""
    settings = load_settings()
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    if settings.get("last_reminder_date") == today:
        return
    if now.hour != settings.get("daily_reminder_hour", 20):
        return
    users = load_users()
    count = 0
    for uid, u in users.items():
        if u.get("daily_reminder") and u.get("mood_log", {}).get(today) is None:
            send_message(uid, "🌱 وقتشه بگی امروز حالت چطور بود؟ فقط چند ثانیه وقت می‌گیره 🌿", inline_kb([[("🌱 ثبت حال امروز", "mood_open")]]))
            count += 1
    settings["last_reminder_date"] = today
    save_settings(settings)
    if count:
        print(f"[daily-reminder] sent to {count} users")

JOIN_RECHECK_INTERVAL_SECONDS = 5
_last_join_recheck = [0.0]

def periodic_join_recheck():
    """هر چند ثانیه یک‌بار، عضویت کاربرهایی که قبلاً از گیت رد شده بودن رو دوباره چک می‌کنه.
    اگه کسی کانال رو لفت داده باشه، دوباره پیام جوین اجباری براش می‌فرسته."""
    now_ts = time.time()
    if now_ts - _last_join_recheck[0] < JOIN_RECHECK_INTERVAL_SECONDS:
        return
    _last_join_recheck[0] = now_ts

    settings = load_settings()
    if not settings.get("force_join") or not settings.get("channels"):
        return

    users = load_users()
    for uid, u in users.items():
        if is_admin(uid):
            continue
        if not u.get("join_gate_passed"):
            continue  # فقط کسایی که قبلاً عضویتشون تأیید شده بود رو دوباره چک می‌کنیم
        still_member = user_is_member_everywhere(uid)
        if not still_member:
            u["join_gate_passed"] = False
            save_users(users)
            send_message(
                uid,
                "⚠️ به نظر می‌رسه از کانال ما خارج شدید!\n\nبرای ادامه استفاده از ربات، لطفاً دوباره عضو کانال بشید:",
            )
            send_join_gate(uid)

def main():
    print("🤖 ربات مانا مایند در حال اجراست...")
    load_settings()
    offset = None
    while True:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1
            try:
                if "message" in update:
                    handle_message(update["message"])
                elif "channel_post" in update:
                    capture_channel_numeric_id(update["channel_post"].get("chat", {}))
                elif "callback_query" in update:
                    handle_callback_query(update["callback_query"])
                elif "pre_checkout_query" in update:
                    handle_pre_checkout_query(update["pre_checkout_query"])
            except Exception as e:
                print(f"[update handling error] {e}")
        try:
            check_daily_reminder()
        except Exception as e:
            print(f"[daily-reminder error] {e}")
        try:
            periodic_join_recheck()
        except Exception as e:
            print(f"[join-recheck error] {e}")
        time.sleep(0.5)

if __name__ == "__main__":
    main()

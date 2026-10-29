import streamlit as st
import sqlite3
import hashlib
import secrets
import hmac
import os
import re
import json
import io
from pathlib import Path
from datetime import datetime

from PIL import Image, ImageOps

# =========================================================
# NUMBER ONE — ADVERTISING & CREATIVE STUDIO
# =========================================================

st.set_page_config(
    page_title="NUMBER ONE | استوديو الإبداع",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="expanded"
)

APP_NAME = "NUMBER ONE"
DB_PATH = os.getenv("NUMBER_ONE_DB", "number_one.db")
UPLOAD_DIR = Path("user_uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# احتفظ بإعداد كلمة مرور المالك الحالية في Secrets.
# لا تضع كلمة المرور داخل ملف الكود.
OWNER_USERNAME = os.getenv("NUMBER_ONE_OWNER_USERNAME", "owner")
OWNER_PASSWORD = os.getenv("NUMBER_ONE_OWNER_PASSWORD", "")

try:
    OWNER_USERNAME = str(
        st.secrets.get("NUMBER_ONE_OWNER_USERNAME", OWNER_USERNAME)
    )
    OWNER_PASSWORD = str(
        st.secrets.get("NUMBER_ONE_OWNER_PASSWORD", OWNER_PASSWORD)
    )
except Exception:
    pass


# =========================================================
# DATABASE
# =========================================================

def connect_db():
    con = sqlite3.connect(DB_PATH, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def init_db():
    con = connect_db()
    cur = con.cursor()

    # الحفاظ على جدول المستخدمين الموجود في النسخة السابقة.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            plan TEXT DEFAULT 'Free',
            created TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            method TEXT NOT NULL,
            amount TEXT NOT NULL,
            reference TEXT NOT NULL,
            status TEXT DEFAULT 'قيد المراجعة',
            created TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            category TEXT NOT NULL,
            details TEXT NOT NULL,
            contact TEXT NOT NULL,
            created TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            username TEXT PRIMARY KEY,
            email TEXT DEFAULT '',
            role TEXT DEFAULT 'user',
            status TEXT DEFAULT 'active'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            content TEXT NOT NULL,
            created TEXT NOT NULL,
            updated TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS merchant_ads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            placement TEXT NOT NULL,
            duration INTEGER NOT NULL,
            price TEXT DEFAULT 'يحدد من الإدارة',
            status TEXT DEFAULT 'بانتظار المراجعة',
            created TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ad_spaces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            price TEXT DEFAULT 'يحدد من الإدارة',
            active INTEGER DEFAULT 1
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS social_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            platform TEXT NOT NULL,
            profile_url TEXT DEFAULT '',
            status TEXT DEFAULT 'قريبًا',
            created TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT DEFAULT '',
            created TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    cur.execute("SELECT COUNT(*) FROM ad_spaces")
    if cur.fetchone()[0] == 0:
        cur.executemany("""
            INSERT INTO ad_spaces
            (title, description, price, active)
            VALUES (?, ?, ?, 1)
        """, [
            ("الصفحة الرئيسية", "مساحة إعلانية في الواجهة الرئيسية",
             "يحدد من الإدارة"),
            ("معرض القوالب", "مساحة إعلانية داخل معرض القوالب",
             "يحدد من الإدارة"),
            ("مساحة التجار", "مساحة مخصصة للعروض التجارية",
             "يحدد من الإدارة")
        ])

    con.commit()
    con.close()


init_db()


# =========================================================
# SECURITY AND ACCOUNTS
# =========================================================

def password_hash(password):
    salt = os.getenv(
        "NUMBER_ONE_PASSWORD_SALT",
        "change-this-salt-before-production"
    )

    try:
        salt = str(
            st.secrets.get("NUMBER_ONE_PASSWORD_SALT", salt)
        )
    except Exception:
        pass

    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        200000
    ).hex()


def log_action(actor, action, details=""):
    con = connect_db()
    con.execute("""
        INSERT INTO audit_log(actor, action, details, created)
        VALUES (?, ?, ?, ?)
    """, (actor or "anonymous", action, str(details)[:500], now()))
    con.commit()
    con.close()


def get_profile(username):
    con = connect_db()
    row = con.execute("""
        SELECT * FROM user_profiles WHERE username=?
    """, (username,)).fetchone()
    con.close()
    return dict(row) if row else {
        "username": username,
        "email": "",
        "role": "user",
        "status": "active"
    }


def register_user(username, password, email=""):
    username = username.strip()
    email = email.strip().lower()

    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,32}", username):
        return False, "اسم المستخدم يجب أن يكون من 3 إلى 32 حرفًا."

    if len(password) < 10:
        return False, "كلمة المرور يجب أن تكون 10 أحرف على الأقل."

    if email and not re.fullmatch(
        r"[^@\s]+@[^@\s]+\.[^@\s]+", email
    ):
        return False, "البريد الإلكتروني غير صحيح."

    con = connect_db()

    try:
        con.execute("""
            INSERT INTO users(username, password, plan, created)
            VALUES (?, ?, 'Free', ?)
        """, (username, password_hash(password), now()))

        con.execute("""
            INSERT INTO user_profiles(username, email, role, status)
            VALUES (?, ?, 'user', 'active')
        """, (username, email))

        con.commit()
        log_action(username, "register")
        return True, "تم إنشاء الحساب بنجاح."

    except sqlite3.IntegrityError:
        con.rollback()
        return False, "اسم المستخدم مستخدم بالفعل."

    finally:
        con.close()


def authenticate(username, password):
    con = connect_db()

    user = con.execute("""
        SELECT username, password, plan
        FROM users WHERE username=?
    """, (username.strip(),)).fetchone()

    con.close()

    if not user:
        return None

    profile = get_profile(user["username"])

    if profile["status"] != "active":
        return None

    expected = password_hash(password)

    # يدعم التجزئة القديمة المتوافقة مع الإصدار السابق.
    if not hmac.compare_digest(str(user["password"]), expected):
        return None

    return {
        "username": user["username"],
        "plan": user["plan"],
        "role": profile["role"]
    }


def current_user():
    return st.session_state.get("user")


def is_owner():
    user = current_user()
    return bool(user and user["role"] == "owner")


def is_merchant():
    user = current_user()
    return bool(user and user["role"] in ("merchant", "owner"))


def require_login():
    if not current_user():
        st.warning("سجل الدخول أولًا لاستخدام هذه الميزة.")
        return False
    return True


# =========================================================
# OWNER ACCESS
# =========================================================

# لا يتم إنشاء حساب مالك تلقائي بكلمة مرور افتراضية.
# يجب استخدام بيانات المالك الموجودة لديك أو ضبطها بأمان.

def owner_login(username, password):
    if not OWNER_PASSWORD:
        return False

    return (
        hmac.compare_digest(username, OWNER_USERNAME)
        and hmac.compare_digest(password, OWNER_PASSWORD)
    )


# =========================================================
# DESIGN SYSTEM
# =========================================================

st.markdown("""
<style>
@import url(
'https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800&display=swap'
);

html, body, [class*="css"] {
    font-family: 'Cairo', sans-serif;
}

.stApp {
    background:
        radial-gradient(circle at top right, #1b3157, transparent 38%),
        linear-gradient(135deg, #070b16, #111a2e);
    color: #f5f7ff;
}

section[data-testid="stSidebar"] {
    background: #0a1120;
    border-left: 1px solid #344563;
}

.hero {
    background: linear-gradient(135deg, #192a49, #0b1221);
    border: 1px solid #d7b45d;
    border-radius: 22px;
    padding: 25px;
    text-align: center;
    margin-bottom: 22px;
}

.hero h1 {
    color: #f0cc70;
    font-size: clamp(28px, 4vw, 44px);
    font-weight: 800;
}

.hero p {
    color: #d7dfef;
}

.panel {
    background: linear-gradient(145deg, #19243a, #0d1526);
    border: 1px solid #344663;
    border-radius: 16px;
    padding: 18px;
    margin-bottom: 14px;
}

.gold {
    color: #f0cc70;
}

div.stButton > button,
div.stDownloadButton > button {
    border-radius: 10px;
    min-height: 42px;
    font-weight: 700;
}

.stTextInput input,
.stTextArea textarea {
    background: #111c30;
    color: white;
    border: 1px solid #344663;
}

@media (max-width: 768px) {
    .hero { padding: 15px; }
}
</style>
""", unsafe_allow_html=True)


st.markdown("""
<div class="hero">
    <h1>👑 NUMBER ONE</h1>
    <p>استوديو الإعلانات والتصميم الإبداعي</p>
    <p>أنشئ محتواك ونظّم مشاريعك من مكان واحد</p>
</div>
""", unsafe_allow_html=True)


# =========================================================
# NAVIGATION
# =========================================================

PAGES = [
    "🏠 الرئيسية",
    "🎨 قوالب الإعلانات",
    "✍️ صانع الإعلان",
    "🗂️ مشاريعي",
    "🎬 الصور والفيديو",
    "🌐 حسابات التواصل",
    "🏪 مساحة التجار",
    "💎 الاشتراكات",
    "💳 الدفع",
    "📋 طلب تصميم",
    "👤 حسابي",
    "🔐 تسجيل الدخول",
    "📝 إنشاء حساب",
    "🔑 استعادة الحساب",
    "⚙️ الإعدادات",
    "📜 الخصوصية والشروط",
    "📞 التواصل",
    "🛡️ لوحة المالك"
]

st.sidebar.markdown(
    "<h2 style='color:#f0cc70;text-align:center'>👑 NUMBER ONE</h2>",
    unsafe_allow_html=True
)

if current_user():
    st.sidebar.success(
        f"{current_user()['username']} · {current_user()['plan']}"
    )

    if st.sidebar.button("تسجيل الخروج", use_container_width=True):
        log_action(current_user()["username"], "logout")
        st.session_state.pop("user", None)
        st.rerun()
else:
    st.sidebar.info("يمكنك تصفح الموقع دون حساب.")

page = st.sidebar.radio("القائمة الرئيسية", PAGES)

st.sidebar.caption("واجهة متجاوبة • العربية أولًا • الكمبيوتر والهاتف")


# =========================================================
# AD TEMPLATES
# =========================================================

TEMPLATES = [
    {
        "name": "إعلان متجر إلكتروني",
        "category": "التجارة",
        "description": "إعلان منتجات وعروض وخصومات."
    },
    {
        "name": "إعلان مطعم",
        "category": "المطاعم",
        "description": "إعلان وجبات وعروض المطاعم."
    },
    {
        "name": "إعلان عقاري",
        "category": "العقارات",
        "description": "تسويق الأراضي والشقق والعقارات."
    },
    {
        "name": "إعلان دورة تدريبية",
        "category": "التعليم",
        "description": "إعلان الدورات والمعاهد."
    },
    {
        "name": "إعلان منتج تجميلي",
        "category": "الجمال",
        "description": "تصميم تسويقي للمنتجات التجميلية."
    },
    {
        "name": "إعلان تخفيضات",
        "category": "التجارة",
        "description": "إبراز العروض ومدة التخفيض."
    },
    {
        "name": "إعلان خدمة",
        "category": "الخدمات",
        "description": "التعريف بالخدمات المهنية."
    },
    {
        "name": "إعلان علامة تجارية",
        "category": "العلامات التجارية",
        "description": "تعريف الجمهور بالعلامة."
    }
]


# =========================================================
# HOME
# =========================================================

if page == "🏠 الرئيسية":

    st.subheader("مرحبًا بك في NUMBER ONE")

    st.write(
        "منصة لإنشاء الأفكار الإعلانية وتنظيم المشاريع "
        "وتجهيز الصور ومتابعة الطلبات التجارية."
    )

    cols = st.columns(4)

    cards = [
        ("🎨 القوالب", "قوالب لمجالات متعددة"),
        ("✍️ صانع الإعلان", "إنشاء نصوص إعلانية"),
        ("🗂️ مشاريعي", "حفظ الأعمال وتنزيلها"),
        ("🎬 الصور والفيديو", "تجهيز مقاسات الصور")
    ]

    for col, item in zip(cols, cards):
        with col:
            st.markdown(
                f'<div class="panel"><h3 class="gold">{item[0]}</h3>'
                f'<p>{item[1]}</p></div>',
                unsafe_allow_html=True
            )

    st.markdown("### الميزات قيد التطوير")

    st.info(
        "قريبًا: توليد الصور والشعارات بالذكاء الاصطناعي، "
        "وتحرير الفيديو، والربط المباشر بحسابات التواصل الاجتماعي."
    )

    st.caption(
        "لن تظهر هذه الخدمات على أنها مفعلة قبل ربطها واختبارها."
    )


# =========================================================
# TEMPLATES
# =========================================================

elif page == "🎨 قوالب الإعلانات":

    st.subheader("مكتبة القوالب الإعلانية")

    category = st.selectbox(
        "اختر المجال",
        ["الكل"] + sorted(set(t["category"] for t in TEMPLATES))
    )

    for i, template in enumerate(TEMPLATES):

        if category != "الكل" and template["category"] != category:
            continue

        with st.container(border=True):

            st.markdown(f"### {template['name']}")
            st.caption(template["category"])
            st.write(template["description"])

            if st.button(
                "استخدام القالب",
                key=f"template_{i}",
                type="primary"
            ):
                st.session_state["selected_template"] = template
                st.success(
                    "تم اختيار القالب. انتقل إلى صانع الإعلان."
                )


# =========================================================
# AD CREATOR
# =========================================================

elif page == "✍️ صانع الإعلان":

    st.subheader("صانع الإعلان")

    with st.form("ad_creator_form"):

        brand = st.text_input("اسم العلامة التجارية")
        product = st.text_input("المنتج أو الخدمة")
        audience = st.text_input("الجمهور المستهدف")
        offer = st.text_area("العرض أو الرسالة الرئيسية")

        tone = st.selectbox(
            "أسلوب الإعلان",
            ["احترافي", "فاخر", "حيوي", "ودود", "رسمي", "مختصر"]
        )

        platform = st.selectbox(
            "المنصة",
            [
                "Instagram",
                "Facebook",
                "TikTok",
                "YouTube",
                "X",
                "LinkedIn",
                "موقع إلكتروني"
            ]
        )

        submitted = st.form_submit_button(
            "إنشاء النص الإعلاني",
            type="primary"
        )

    if submitted:

        if not product.strip():
            st.error("اكتب اسم المنتج أو الخدمة.")
        else:

            ad = f"""
{brand or 'اسم العلامة التجارية'}

{product}

{offer or 'اكتشف المنتج وتعرّف على تفاصيله.'}

الجمهور المستهدف: {audience or 'العملاء المهتمون'}
أسلوب الإعلان: {tone}
المنصة: {platform}

تواصل معنا لمعرفة التفاصيل.
            """.strip()

            st.session_state["last_ad"] = ad
            st.session_state["last_ad_title"] = product

    if st.session_state.get("last_ad"):

        edited = st.text_area(
            "راجع النص وعدّله قبل استخدامه",
            value=st.session_state["last_ad"],
            height=230
        )

        st.download_button(
            "تنزيل النص",
            data=edited.encode("utf-8"),
            file_name="number_one_ad.txt",
            mime="text/plain"
        )

        if st.button("حفظ في مشاريعي", type="primary"):

            if require_login():

                con = connect_db()

                con.execute("""
                    INSERT INTO projects
                    (username,title,category,content,created,updated)
                    VALUES (?,?,'إعلان',?,?,?)
                """, (
                    current_user()["username"],
                    st.session_state.get("last_ad_title", "إعلان جديد"),
                    edited,
                    now(),
                    now()
                ))

                con.commit()
                con.close()

                log_action(
                    current_user()["username"],
                    "project_saved"
                )

                st.success("تم حفظ المشروع.")


# =========================================================
# PROJECTS
# =========================================================

elif page == "🗂️ مشاريعي":

    st.subheader("مشاريعي")

    if require_login():

        con = connect_db()

        projects = con.execute("""
            SELECT * FROM projects
            WHERE username=?
            ORDER BY updated DESC
        """, (current_user()["username"],)).fetchall()

        con.close()

        if not projects:
            st.info("لا توجد مشاريع محفوظة.")
        else:

            for project in projects:

                with st.expander(project["title"]):

                    edited = st.text_area(
                        "المحتوى",
                        project["content"],
                        key=f"edit_{project['id']}"
                    )

                    c1, c2 = st.columns(2)

                    with c1:

                        if st.button(
                            "حفظ التعديل",
                            key=f"save_{project['id']}"
                        ):

                            con = connect_db()

                            con.execute("""
                                UPDATE projects
                                SET content=?, updated=?
                                WHERE id=? AND username=?
                            """, (
                                edited,
                                now(),
                                project["id"],
                                current_user()["username"]
                            ))

                            con.commit()
                            con.close()

                            st.success("تم تحديث المشروع.")
                            st.rerun()

                    with c2:

                        st.download_button(
                            "تنزيل المشروع",
                            edited.encode("utf-8"),
                            file_name=f"project_{project['id']}.txt",
                            key=f"download_{project['id']}"
                        )

                    if st.button(
                        "حذف المشروع",
                        key=f"delete_{project['id']}"
                    ):

                        con = connect_db()

                        con.execute("""
                            DELETE FROM projects
                            WHERE id=? AND username=?
                        """, (
                            project["id"],
                            current_user()["username"]
                        ))

                        con.commit()
                        con.close()

                        st.success("تم حذف المشروع.")
                        st.rerun()


# =========================================================
# IMAGE RESIZING AND VIDEO
# =========================================================

elif page == "🎬 الصور والفيديو":

    st.subheader("الصور والفيديو")

    sizes = {
        "منشور مربع": (1080, 1080),
        "قصة أو ريلز": (1080, 1920),
        "منشور أفقي": (1200, 630),
        "فيديو أفقي": (1920, 1080),
        "فيديو عمودي": (1080, 1920)
    }

    size_name = st.selectbox("المقاس", list(sizes.keys()))

    width, height = sizes[size_name]

    st.write(f"الأبعاد المطلوبة: **{width} × {height}**")

    uploaded = st.file_uploader(
        "ارفع صورة لتغيير مقاسها",
        type=["png", "jpg", "jpeg", "webp"]
    )

    if uploaded:

        try:

            img = Image.open(uploaded).convert("RGB")

            mode = st.radio(
                "طريقة ضبط الصورة",
                [
                    "احتواء الصورة كاملة",
                    "ملء الإطار وقص الزوائد"
                ]
            )

            if mode == "احتواء الصورة كاملة":

                resized = ImageOps.contain(img, (width, height))

                output = Image.new(
                    "RGB",
                    (width, height),
                    (15, 23, 40)
                )

                output.paste(
                    resized,
                    (
                        (width - resized.width) // 2,
                        (height - resized.height) // 2
                    )
                )

            else:

                output = ImageOps.fit(
                    img,
                    (width, height),
                    method=Image.Resampling.LANCZOS
                )

            st.image(
                output,
                caption=f"{width} × {height}",
                use_container_width=True
            )

            buffer = io.BytesIO()
            output.save(buffer, format="PNG")

            st.download_button(
                "تنزيل الصورة بالمقاس الجديد",
                buffer.getvalue(),
                file_name=f"number_one_{width}x{height}.png",
                mime="image/png",
                type="primary"
            )

        except Exception as exc:
            st.error(f"تعذرت معالجة الصورة: {exc}")

    st.markdown("---")
    st.subheader("تحرير الفيديو")

    st.info(
        "قريبًا — تغيير أبعاد الفيديو وقصه وتصديره يحتاج "
        "إلى وحدة معالجة فيديو مثل FFmpeg على الخادم."
    )

    st.subheader("توليد الصور والشعارات بالذكاء الاصطناعي")

    st.info(
        "قريبًا — يلزم ربط مزود توليد صور بمفتاح API آمن."
    )


# =========================================================
# SOCIAL MEDIA
# =========================================================

elif page == "🌐 حسابات التواصل":

    st.subheader("حسابات التواصل الاجتماعي")

    st.write(
        "يمكن تجهيز قائمة الحسابات التي تريد ربطها بالمنصة."
    )

    platforms = [
        "Facebook",
        "Instagram",
        "TikTok",
        "YouTube",
        "X",
        "LinkedIn"
    ]

    if require_login():

        for platform in platforms:

            with st.container(border=True):

                st.markdown(f"### {platform}")

                url = st.text_input(
                    "رابط الحساب",
                    key=f"social_url_{platform}"
                )

                if st.button(
                    "حفظ الرابط",
                    key=f"social_save_{platform}"
                ):

                    if url and not url.startswith(("https://", "http://")):
                        st.error("أدخل رابطًا يبدأ بـ https:// أو http://")
                    else:

                        con = connect_db()

                        con.execute("""
                            INSERT INTO social_accounts
                            (username,platform,profile_url,status,created)
                            VALUES (?,?,?,'رابط محفوظ',?)
                        """, (
                            current_user()["username"],
                            platform,
                            url,
                            now()
                        ))

                        con.commit()
                        con.close()

                        st.success("تم حفظ الرابط.")

                st.caption(
                    "النشر المباشر وإدارة الرسائل والإحصاءات: قريبًا."
                )


# =========================================================
# MERCHANT WORKSPACE
# =========================================================

elif page == "🏪 مساحة التجار":

    st.subheader("مساحة التجار")

    if not require_login():
        st.stop()

    profile = get_profile(current_user()["username"])

    if profile["role"] not in ("merchant", "owner"):

        st.warning(
            "حسابك ليس حساب تاجر بعد. يمكنك التواصل مع المالك "
            "لطلب تفعيل صلاحية التاجر."
        )

    con = connect_db()

    spaces = con.execute("""
        SELECT * FROM ad_spaces
        WHERE active=1
    """).fetchall()

    con.close()

    if not spaces:
        st.info("لا توجد مساحات إعلانية متاحة.")
    else:

        with st.form("merchant_ad_form"):

            title = st.text_input("عنوان الإعلان")
            description = st.text_area("وصف الإعلان")

            placement = st.selectbox(
                "المساحة",
                [s["title"] for s in spaces]
            )

            duration = st.selectbox(
                "مدة الإعلان",
                [7, 14, 30]
            )

            submitted = st.form_submit_button(
                "إرسال للمراجعة",
                type="primary"
            )

        if submitted:

            if not title.strip() or not description.strip():

                st.error("أدخل عنوان الإعلان والوصف.")

            else:

                con = connect_db()

                con.execute("""
                    INSERT INTO merchant_ads
                    (username,title,description,placement,duration,created)
                    VALUES (?,?,?,?,?,?)
                """, (
                    current_user()["username"],
                    title,
                    description,
                    placement,
                    duration,
                    now()
                ))

                con.commit()
                con.close()

                log_action(
                    current_user()["username"],
                    "merchant_ad_submitted",
                    title
                )

                st.success(
                    "تم إرسال الطلب للمراجعة. النشر غير تلقائي."
                )

    con = connect_db()

    mine = con.execute("""
        SELECT * FROM merchant_ads
        WHERE username=?
        ORDER BY id DESC
    """, (current_user()["username"],)).fetchall()

    con.close()

    st.markdown("### طلباتي الإعلانية")

    for ad in mine:

        st.markdown(
            f"**{ad['title']}** — {ad['status']} — "
            f"{ad['price']}"
        )


# =========================================================
# SUBSCRIPTIONS
# =========================================================

elif page == "💎 الاشتراكات":

    st.subheader("الاشتراكات")

    free, pro, merchant = st.columns(3)

    with free:

        st.markdown("""
        <div class="panel">
        <h3 class="gold">Free</h3>
        <h2>مجاني</h2>
        <p>تصفح القوالب</p>
        <p>إنشاء نصوص إعلانية</p>
        <p>حفظ المشاريع بعد التسجيل</p>
        </div>
        """, unsafe_allow_html=True)

    with pro:

        st.markdown("""
        <div class="panel">
        <h3 class="gold">Pro</h3>
        <h2>مدفوع</h2>
        <p>مزايا إضافية عند تفعيلها</p>
        <p>خدمات موسعة</p>
        <p>ميزات مستقبلية</p>
        </div>
        """, unsafe_allow_html=True)

    with merchant:

        st.markdown("""
        <div class="panel">
        <h3 class="gold">Merchant</h3>
        <h2>للتجار</h2>
        <p>طلبات إعلانية</p>
        <p>متابعة حالة الطلبات</p>
        <p>مساحات إعلانية</p>
        </div>
        """, unsafe_allow_html=True)

    st.warning(
        "لا يتم خصم أموال تلقائيًا. لا تُفعّل الاشتراكات "
        "المدفوعة إلا بعد مراجعة الدفع."
    )

    if st.button("طلب اشتراك Pro", type="primary"):

        if require_login():

            st.session_state["requested_plan"] = "Pro"
            st.success("انتقل إلى صفحة الدفع لتقديم طلب الاشتراك.")


# =========================================================
# PAYMENTS
# =========================================================

elif page == "💳 الدفع":

    st.subheader("طلبات الدفع")

    if not require_login():
        st.stop()

    with st.form("payment_form"):

        plan = st.selectbox(
            "الخطة",
            ["Pro", "مساحة إعلانية"]
        )

        method = st.selectbox(
            "وسيلة الدفع",
            [
                "تحويل يدوي / محفظة",
                "وسيلة أخرى معتمدة"
            ]
        )

        amount = st.text_input("المبلغ والعملة")
        reference = st.text_input("رقم العملية أو المرجع")

        submitted = st.form_submit_button(
            "إرسال طلب الدفع",
            type="primary"
        )

    if submitted:

        if not amount.strip() or not reference.strip():

            st.error("أدخل المبلغ ومرجع العملية.")

        else:

            con = connect_db()

            con.execute("""
                INSERT INTO payments
                (username,method,amount,reference,status,created)
                VALUES (?,?,?,?,?,?)
            """, (
                current_user()["username"],
                method,
                amount,
                reference,
                "قيد المراجعة",
                now()
            ))

            con.commit()
            con.close()

            log_action(
                current_user()["username"],
                "payment_submitted",
                plan
            )

            st.success(
                "تم تسجيل الطلب للمراجعة. لم يتم تفعيل الاشتراك بعد."
            )

    con = connect_db()

    payments = con.execute("""
        SELECT * FROM payments
        WHERE username=?
        ORDER BY id DESC
    """, (current_user()["username"],)).fetchall()

    con.close()

    for payment in payments:

        st.markdown(
            f"**{payment['method']}** — "
            f"{payment['amount']} — "
            f"{payment['status']}"
        )

    st.info(
        "الربط الآلي مع YemenPay أو Esaalat: قريبًا، "
        "حتى إعداد مزود الدفع والتحقق من العمليات."
    )


# =========================================================
# DESIGN ORDERS
# =========================================================

elif page == "📋 طلب تصميم":

    st.subheader("طلب تصميم")

    with st.form("design_order_form"):

        category = st.selectbox(
            "نوع التصميم",
            [
                "شعار",
                "إعلان",
                "هوية بصرية",
                "فيديو",
                "إدارة محتوى",
                "أخرى"
            ]
        )

        details = st.text_area("تفاصيل الطلب")
        contact = st.text_input("وسيلة التواصل")

        submitted = st.form_submit_button(
            "إرسال الطلب",
            type="primary"
        )

    if submitted:

        if not require_login():
            pass

        elif not details.strip() or not contact.strip():

            st.error("أدخل تفاصيل الطلب ووسيلة التواصل.")

        else:

            con = connect_db()

            con.execute("""
                INSERT INTO orders
                (username,category,details,contact,created)
                VALUES (?,?,?,?,?)
            """, (
                current_user()["username"],
                category,
                details,
                contact,
                now()
            ))

            con.commit()
            con.close()

            log_action(
                current_user()["username"],
                "design_order_submitted",
                category
            )

            st.success("تم تسجيل طلبك.")


# =========================================================
# ACCOUNT
# =========================================================

elif page == "👤 حسابي":

    st.subheader("حسابي")

    if require_login():

        con = connect_db()

        user = con.execute("""
            SELECT username,plan,created
            FROM users WHERE username=?
        """, (current_user()["username"],)).fetchone()

        con.close()

        profile = get_profile(current_user()["username"])

        st.write(f"**اسم المستخدم:** {user['username']}")
        st.write(f"**نوع الحساب:** {profile['role']}")
        st.write(f"**الخطة:** {user['plan']}")
        st.write(f"**تاريخ الإنشاء:** {user['created']}")

        st.info(
            "استعادة كلمة المرور عبر البريد: قريبًا، "
            "حتى إعداد خدمة بريد آمنة."
        )


# =========================================================
# LOGIN
# =========================================================

elif page == "🔐 تسجيل الدخول":

    st.subheader("تسجيل الدخول")

    with st.form("login_form"):

        username = st.text_input("اسم المستخدم")
        password = st.text_input("كلمة المرور", type="password")

        submitted = st.form_submit_button(
            "تسجيل الدخول",
            type="primary"
        )

    if submitted:

        # دخول المالك منفصل عن حسابات المستخدمين.
        if owner_login(username, password):

            st.session_state["user"] = {
                "username": OWNER_USERNAME,
                "plan": "Pro",
                "role": "owner"
            }

            log_action(OWNER_USERNAME, "owner_login")
            st.success("تم تسجيل دخول المالك.")
            st.rerun()

        else:

            user = authenticate(username, password)

            if user:

                st.session_state["user"] = user
                st.success("تم تسجيل الدخول.")
                st.rerun()

            else:

                st.error(
                    "بيانات الدخول غير صحيحة أو الحساب غير نشط."
                )


# =========================================================
# REGISTRATION
# =========================================================

elif page == "📝 إنشاء حساب":

    st.subheader("إنشاء حساب")

    with st.form("register_form"):

        username = st.text_input("اسم المستخدم")
        email = st.text_input("البريد الإلكتروني")
        password = st.text_input("كلمة المرور", type="password")
        confirm = st.text_input("تأكيد كلمة المرور", type="password")

        consent = st.checkbox(
            "أوافق على الشروط وسياسة الخصوصية"
        )

        submitted = st.form_submit_button(
            "إنشاء الحساب",
            type="primary"
        )

    if submitted:

        if not consent:

            st.error("يجب الموافقة على الشروط.")

        elif password != confirm:

            st.error("كلمتا المرور غير متطابقتين.")

        else:

            ok, message = register_user(
                username,
                password,
                email
            )

            if ok:
                st.success(message)
            else:
                st.error(message)


# =========================================================
# ACCOUNT RECOVERY
# =========================================================

elif page == "🔑 استعادة الحساب":

    st.subheader("استعادة الحساب")

    st.warning(
        "قريبًا — يجب إعداد خدمة بريد إلكتروني آمنة "
        "لإرسال روابط إعادة تعيين كلمة المرور."
    )

    st.write(
        "لا تدخل كلمة مرور حسابك أو رمز تحقق في هذه الصفحة."
    )


# =========================================================
# SETTINGS
# =========================================================

elif page == "⚙️ الإعدادات":

    st.subheader("الإعدادات")

    if require_login():

        st.write("إعدادات الحساب والبيانات.")

        con = connect_db()

        projects = con.execute("""
            SELECT title,category,content,created,updated
            FROM projects WHERE username=?
        """, (current_user()["username"],)).fetchall()

        orders = con.execute("""
            SELECT category,details,contact,created
            FROM orders WHERE username=?
        """, (current_user()["username"],)).fetchall()

        con.close()

        data = {
            "username": current_user()["username"],
            "projects": [dict(x) for x in projects],
            "orders": [dict(x) for x in orders]
        }

        st.download_button(
            "تنزيل نسخة من بياناتي",
            json.dumps(
                data,
                ensure_ascii=False,
                indent=2
            ).encode("utf-8"),
            file_name="number_one_data.json",
            mime="application/json"
        )


# =========================================================
# PRIVACY AND TERMS
# =========================================================

elif page == "📜 الخصوصية والشروط":

    st.subheader("الخصوصية والشروط")

    st.markdown("""
    ### الخصوصية
    - تُستخدم بيانات الحساب لتشغيل خدمات المنصة.
    - لا تشارك كلمات مرور حسابات التواصل الاجتماعي.
    - لا تدخل بيانات بطاقتك البنكية في النماذج.
    - يمكنك تنزيل بيانات مشاريعك من الإعدادات.
    - يجب حماية قاعدة البيانات ونسخها احتياطيًا.

    ### الشروط
    - تأكد من امتلاك حقوق المحتوى الذي تستخدمه.
    - راجع الأسعار والعروض قبل نشر أي إعلان.
    - طلب الدفع لا يعني قبول العملية.
    - الميزات التي تظهر «قريبًا» غير مفعلة.
    - قد تُعلّق الحسابات المخالفة للشروط.

    هذه صيغة أولية، ويجب مراجعتها قانونيًا قبل الإطلاق العام.
    """)


# =========================================================
# CONTACT
# =========================================================

elif page == "📞 التواصل":

    st.subheader("التواصل مع NUMBER ONE")

    st.write(
        "يمكنك إرسال طلبك من صفحة «طلب تصميم» "
        "ومتابعة الطلب من حسابك."
    )

    st.info(
        "البريد الرسمي والدعم المباشر: قريبًا، "
        "حتى إعداد قناة تواصل حقيقية."
    )


# =========================================================
# OWNER DASHBOARD
# =========================================================

elif page == "🛡️ لوحة المالك":

    st.subheader("لوحة إدارة المالك")

    if not is_owner():

        st.error(
            "هذه الصفحة مخصصة للمالك. سجّل الدخول "
            "باستخدام بيانات المالك المضبوطة في Secrets."
        )

        st.stop()

    con = connect_db()

    users = con.execute("""
        SELECT username,plan,created FROM users
        ORDER BY id DESC
    """).fetchall()

    payments = con.execute("""
        SELECT * FROM payments ORDER BY id DESC
    """).fetchall()

    orders = con.execute("""
        SELECT * FROM orders ORDER BY id DESC
    """).fetchall()

    ads = con.execute("""
        SELECT * FROM merchant_ads ORDER BY id DESC
    """).fetchall()

    audit = con.execute("""
        SELECT * FROM audit_log ORDER BY id DESC LIMIT 100
    """).fetchall()

    con.close()

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("المستخدمون", len(users))
    c2.metric("طلبات الدفع", len(payments))
    c3.metric("طلبات التصميم", len(orders))
    c4.metric("إعلانات التجار", len(ads))

    st.markdown("### المستخدمون")

    if users:

        st.dataframe(
            [
                {
                    "المستخدم": u["username"],
                    "الخطة": u["plan"],
                    "تاريخ التسجيل": u["created"]
                }
                for u in users
            ],
            use_container_width=True,
            hide_index=True
        )

    st.markdown("### إدارة الصلاحيات")

    with st.form("manage_user_form"):

        target = st.text_input("اسم المستخدم")
        role = st.selectbox(
            "الصلاحية",
            ["user", "merchant"]
        )
        status = st.selectbox(
            "حالة الحساب",
            ["active", "suspended"]
        )
        plan = st.selectbox(
            "الخطة",
            ["Free", "Pro"]
        )

        submitted = st.form_submit_button(
            "حفظ التغييرات"
        )

    if submitted:

        if not target.strip():

            st.error("أدخل اسم المستخدم.")

        elif target.strip() == OWNER_USERNAME:

            st.error("لا يمكن تغيير صلاحيات المالك من هنا.")

        else:

            con = connect_db()

            exists = con.execute("""
                SELECT username FROM users WHERE username=?
            """, (target.strip(),)).fetchone()

            if exists:

                con.execute("""
                    INSERT OR IGNORE INTO user_profiles
                    (username,email,role,status)
                    VALUES (?,'','user','active')
                """, (target.strip(),))

                con.execute("""
                    UPDATE user_profiles
                    SET role=?, status=?
                    WHERE username=?
                """, (role, status, target.strip()))

                con.execute("""
                    UPDATE users SET plan=?
                    WHERE username=?
                """, (plan, target.strip()))

                con.commit()
                con.close()

                log_action(
                    OWNER_USERNAME,
                    "user_permissions_updated",
                    target
                )

                st.success("تم تحديث الحساب.")
                st.rerun()

            else:

                con.close()
                st.error("لم يتم العثور على المستخدم.")

    st.markdown("### مراجعة المدفوعات")

    for payment in payments:

        with st.container(border=True):

            st.write(
                f"المستخدم: {payment['username']} | "
                f"المبلغ: {payment['amount']} | "
                f"المرجع: {payment['reference']} | "
                f"الحالة: {payment['status']}"
            )

            decision = st.selectbox(
                "قرار الدفع",
                ["قيد المراجعة", "مقبول", "مرفوض"],
                key=f"payment_decision_{payment['id']}"
            )

            if st.button(
                "حفظ قرار الدفع",
                key=f"save_payment_{payment['id']}"
            ):

                con = connect_db()

                con.execute("""
                    UPDATE payments SET status=?
                    WHERE id=?
                """, (decision, payment["id"]))

                if decision == "مقبول":
                    con.execute("""
                        UPDATE users SET plan='Pro'
                        WHERE username=?
                    """, (payment["username"],))

                con.commit()
                con.close()

                log_action(
                    OWNER_USERNAME,
                    "payment_reviewed",
                    str(payment["id"])
                )

                st.success("تم حفظ القرار.")
                st.rerun()

    st.markdown("### طلبات التصميم")

    for order in orders:

        with st.expander(
            f"#{order['id']} — {order['username']} — "
            f"{order['category']}"
        ):

            st.write(order["details"])
            st.write(f"التواصل: {order['contact']}")

    st.markdown("### طلبات إعلانات التجار")

    for ad in ads:

        with st.expander(
            f"#{ad['id']} — {ad['title']} — {ad['status']}"
        ):

            st.write(ad["description"])
            st.write(f"المساحة: {ad['placement']}")

            decision = st.selectbox(
                "حالة الإعلان",
                [
                    "بانتظار المراجعة",
                    "مقبول",
                    "مرفوض",
                    "متوقف"
                ],
                key=f"merchant_status_{ad['id']}"
            )

            price = st.text_input(
                "السعر",
                value=ad["price"],
                key=f"merchant_price_{ad['id']}"
            )

            if st.button(
                "حفظ حالة الإعلان",
                key=f"merchant_save_{ad['id']}"
            ):

                con = connect_db()

                con.execute("""
                    UPDATE merchant_ads
                    SET status=?, price=?
                    WHERE id=?
                """, (decision, price, ad["id"]))

                con.commit()
                con.close()

                log_action(
                    OWNER_USERNAME,
                    "merchant_ad_reviewed",
                    str(ad["id"])
                )

                st.success("تم تحديث الإعلان.")
                st.rerun()

    st.markdown("### سجل العمليات")

    if audit:

        st.dataframe(
            [
                {
                    "الفاعل": x["actor"],
                    "العملية": x["action"],
                    "التفاصيل": x["details"],
                    "التاريخ": x["created"]
                }
                for x in audit
            ],
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# FOOTER
# =========================================================

st.markdown("---")

st.caption(
    "NUMBER ONE © 2026 | استوديو الإعلانات والتصميم"
)

st.caption(
    "الميزات غير المرتبطة بخدمات خارجية تظهر بوضوح على أنها قريبًا."
)

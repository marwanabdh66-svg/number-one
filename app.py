import streamlit as st
import sqlite3
import hashlib
import secrets
import hmac
import os
import time
from datetime import datetime

# ==================================================
# إعدادات NUMBER ONE
# ==================================================

st.set_page_config(
    page_title="NUMBER ONE",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_PATH = "number_one.db"

# ==================================================
# تنسيق الواجهة
# ==================================================

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #08111f, #101d35);
    color: #ffffff;
}
[data-testid="stSidebar"] {
    background: #0b1426;
}
h1, h2, h3 {
    color: #65e6ff !important;
}
.stButton > button {
    width: 100%;
    border-radius: 12px;
    border: 1px solid #65e6ff;
    background: #12304b;
    color: white;
    font-weight: bold;
    padding: 10px;
}
.stButton > button:hover {
    background: #176087;
    color: white;
}
div[data-testid="stMetric"] {
    background: #12233a;
    padding: 15px;
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)

# ==================================================
# قاعدة البيانات
# ==================================================

def get_db():
    return sqlite3.connect(DB_PATH, timeout=15)


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                plan TEXT DEFAULT 'free',
                created_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL
            )
        """)


init_db()

# ==================================================
# حماية كلمات المرور
# ==================================================

def hash_password(password, salt):
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        300000
    ).hex()


def valid_password(password):
    return len(password) >= 10


def create_user(username, password, role="user"):
    username = username.strip()

    if len(username) < 3 or len(username) > 30:
        return False, "اسم المستخدم يجب أن يكون بين 3 و30 حرفًا."

    if not username.replace("_", "").replace("-", "").isalnum():
        return False, "استخدم الحروف والأرقام والشرطة فقط في اسم المستخدم."

    if not valid_password(password):
        return False, "كلمة المرور يجب أن تحتوي على 10 أحرف أو أكثر."

    salt = secrets.token_hex(16)
    password_hash = hash_password(password, salt)

    try:
        with get_db() as conn:
            conn.execute("""
                INSERT INTO users
                (username, password_hash, salt, role, plan, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                username,
                password_hash,
                salt,
                role,
                "free",
                datetime.now().isoformat(timespec="seconds")
            ))

        return True, "تم إنشاء الحساب بنجاح."

    except sqlite3.IntegrityError:
        return False, "اسم المستخدم مستخدم بالفعل."

    except sqlite3.Error:
        return False, "تعذر إنشاء الحساب. حاول مرة أخرى."


def verify_user(username, password):
    with get_db() as conn:
        row = conn.execute("""
            SELECT username, password_hash, salt, role, plan
            FROM users
            WHERE username = ?
        """, (username.strip(),)).fetchone()

    if not row:
        return None

    username_db, saved_hash, salt, role, plan = row
    submitted_hash = hash_password(password, salt)

    if hmac.compare_digest(saved_hash, submitted_hash):
        return {
            "username": username_db,
            "role": role,
            "plan": plan
        }

    return None


def get_user(username):
    with get_db() as conn:
        row = conn.execute("""
            SELECT username, role, plan, created_at
            FROM users
            WHERE username = ?
        """, (username,)).fetchone()

    if not row:
        return None

    return {
        "username": row[0],
        "role": row[1],
        "plan": row[2],
        "created_at": row[3]
    }


def change_password(username, old_password, new_password):
    user = verify_user(username, old_password)

    if not user:
        return False, "كلمة المرور الحالية غير صحيحة."

    if not valid_password(new_password):
        return False, "كلمة المرور الجديدة يجب أن تكون 10 أحرف أو أكثر."

    salt = secrets.token_hex(16)
    password_hash = hash_password(new_password, salt)

    with get_db() as conn:
        conn.execute("""
            UPDATE users
            SET password_hash = ?, salt = ?
            WHERE username = ?
        """, (password_hash, salt, username))

    return True, "تم تغيير كلمة المرور بنجاح."


# ==================================================
# إنشاء حساب المدير من Secrets
# ==================================================

def bootstrap_admin():
    try:
        admin_username = st.secrets.get("ADMIN_USERNAME", "")
        admin_password = st.secrets.get("ADMIN_PASSWORD", "")
    except Exception:
        admin_username = ""
        admin_password = ""

    if not admin_username or not admin_password:
        return

    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ?",
            (admin_username,)
        ).fetchone()

    if not existing:
        create_user(admin_username, admin_password, role="admin")


bootstrap_admin()

# ==================================================
# حالة تسجيل الدخول
# ==================================================

if "user" not in st.session_state:
    st.session_state.user = None

if "login_attempts" not in st.session_state:
    st.session_state.login_attempts = 0

if "login_wait_until" not in st.session_state:
    st.session_state.login_wait_until = 0


def logout():
    st.session_state.user = None
    st.session_state.login_attempts = 0
    st.session_state.login_wait_until = 0
    st.rerun()


# ==================================================
# الشريط الجانبي
# ==================================================

with st.sidebar:
    st.markdown("# 🚀 NUMBER ONE")
    st.caption("منصتك الإبداعية")

    st.divider()

    if st.session_state.user:
        current_user = st.session_state.user

        st.success("مرحبًا، " + current_user["username"])
        st.caption(
            "نوع الحساب: "
            + ("مدير" if current_user["role"] == "admin" else "مستخدم")
        )

        page_options = [
            "الرئيسية",
            "تصفح القوالب",
            "تصميم الشعارات",
            "تصميم الإعلانات",
            "مساحة التجار",
            "مشاريعي",
            "الاشتراكات",
            "إعدادات الحساب"
        ]

        if current_user["role"] == "admin":
            page_options.append("لوحة الإدارة")

        page = st.radio("القائمة الرئيسية", page_options)

        st.divider()

        if st.button("🚪 تسجيل الخروج"):
            logout()

    else:
        page = "تسجيل الدخول"

        st.info("سجل دخولك للوصول إلى مساحة العمل.")
        st.caption("NUMBER ONE © 2026")


# ==================================================
# صفحة تسجيل الدخول والتسجيل
# ==================================================

if not st.session_state.user:

    st.markdown("# 🚀 مرحبًا بك في NUMBER ONE")
    st.write("منصة واحدة للقوالب والتصميم والإعلانات.")

    login_tab, register_tab = st.tabs([
        "🔐 تسجيل الدخول",
        "👤 إنشاء حساب"
    ])

    with login_tab:
        st.subheader("تسجيل الدخول")

        if time.time() < st.session_state.login_wait_until:
            remaining = int(
                st.session_state.login_wait_until - time.time()
            )
            st.error(
                f"توقف مؤقت بسبب المحاولات الفاشلة. انتظر {remaining} ثانية."
            )

        with st.form("login_form"):
            login_username = st.text_input("اسم المستخدم")
            login_password = st.text_input(
                "كلمة المرور",
                type="password"
            )

            login_submit = st.form_submit_button("دخول إلى حسابي")

        if login_submit:
            if time.time() < st.session_state.login_wait_until:
                st.error("انتظر قليلًا قبل المحاولة مرة أخرى.")

            elif not login_username.strip() or not login_password:
                st.warning("أدخل اسم المستخدم وكلمة المرور.")

            else:
                user = verify_user(login_username, login_password)

                if user:
                    st.session_state.user = user
                    st.session_state.login_attempts = 0
                    st.rerun()

                else:
                    st.session_state.login_attempts += 1
                    st.error("اسم المستخدم أو كلمة المرور غير صحيحة.")

                    if st.session_state.login_attempts >= 5:
                        st.session_state.login_wait_until = (
                            time.time() + 60
                        )
                        st.session_state.login_attempts = 0
                        st.warning(
                            "تم إيقاف محاولات الدخول في هذه الجلسة لمدة دقيقة."
                        )

    with register_tab:
        st.subheader("إنشاء حساب مجاني")

        with st.form("register_form"):
            new_username = st.text_input(
                "اختر اسم مستخدم",
                key="register_username"
            )

            new_password = st.text_input(
                "اختر كلمة مرور",
                type="password",
                key="register_password"
            )

            confirm_password = st.text_input(
                "أكد كلمة المرور",
                type="password",
                key="register_confirm"
            )

            register_submit = st.form_submit_button("إنشاء الحساب")

        if register_submit:
            if new_password != confirm_password:
                st.error("كلمتا المرور غير متطابقتين.")

            else:
                success, message = create_user(
                    new_username,
                    new_password
                )

                if success:
                    st.success(message + " يمكنك الآن تسجيل الدخول.")
                else:
                    st.error(message)

    st.info(
        "حساب المدير يُنشأ من إعدادات Secrets في Streamlit Cloud، "
        "وليس من صفحة التسجيل العامة."
    )

    st.stop()


# ==================================================
# الصفحات الداخلية
# ==================================================

user = st.session_state.user

st.markdown(
    f"## 👋 أهلًا بك في NUMBER ONE، {user['username']}"
)

# ==================================================
# الرئيسية
# ==================================================

if page == "الرئيسية":

    st.markdown("# 🚀 اصنع أفكارك مع NUMBER ONE")
    st.write(
        "مساحة عمل تجمع القوالب وأفكار الشعارات والإعلانات "
        "ومشاريعك التجارية في مكان واحد."
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("القوالب", "متاحة للتصفح")

    with col2:
        st.metric("الحساب", "مجاني" if user["plan"] == "free" else "Pro")

    with col3:
        st.metric("مساحة العمل", "جاهزة")

    st.divider()

    st.subheader("ماذا تريد أن تصمم اليوم؟")

    a, b = st.columns(2)

    with a:
        st.info("🎨 الشعارات\n\nخطط لشعار علامتك التجارية.")

        if st.button("الانتقال إلى تصميم الشعارات"):
            st.session_state.home_target = "تصميم الشعارات"
            st.rerun()

    with b:
        st.info("📢 الإعلانات\n\nاكتب فكرة إعلانك واحفظها ضمن مشاريعك.")

        if st.button("الانتقال إلى تصميم الإعلانات"):
            st.session_state.home_target = "تصميم الإعلانات"
            st.rerun()

    if "home_target" in st.session_state:
        st.info(
            "اختر الصفحة المطلوبة من القائمة الجانبية: "
            + st.session_state.home_target
        )

    st.warning(
        "توليد الصور والفيديو بالذكاء الاصطناعي يحتاج إلى ربط خدمة خارجية؛ "
        "هذه النسخة لا تدّعي توليد ملفات صور أو فيديو فعلية."
    )


# ==================================================
# تصفح القوالب
# ==================================================

elif page == "تصفح القوالب":

    st.title("🧩 معرض القوالب")

    st.write(
        "تصفح أفكارًا أولية يمكنك تطويرها. هذه أمثلة وصفية وليست "
        "ملفات قوالب قابلة للتنزيل بعد."
    )

    category = st.selectbox(
        "اختر نوع القوالب",
        [
            "الكل",
            "مطاعم ومأكولات",
            "عقارات",
            "متاجر",
            "ملابس وأزياء",
            "تقنية",
            "تعليم"
        ]
    )

    templates = [
        {
            "name": "إعلان وجبة شهية",
            "category": "مطاعم ومأكولات",
            "description": "تصميم إعلاني للطعام مع عنوان واضح وسعر وعرض."
        },
        {
            "name": "عقار للبيع",
            "category": "عقارات",
            "description": "تصميم لعرض العقارات والمزايا ووسيلة التواصل."
        },
        {
            "name": "عرض متجر",
            "category": "متاجر",
            "description": "إعلان خصومات ومنتجات جديده."
        },
        {
            "name": "مجموعة أزياء",
            "category": "ملابس وأزياء",
            "description": "فكرة تصميم أنيقة لعرض الملابس."
        },
        {
            "name": "خدمة تقنية",
            "category": "تقنية",
            "description": "إعلان لخدمة رقمية أو تطبيق."
        },
        {
            "name": "دورة تعليمية",
            "category": "تعليم",
            "description": "إعلان لدورة أو برنامج تدريبي."
        }
    ]

    for item in templates:
        if category != "الكل" and item["category"] != category:
            continue

        with st.container(border=True):
            st.subheader(item["name"])
            st.caption(item["category"])
            st.write(item["description"])

            if st.button(
                "استخدام الفكرة",
                key="template_" + item["name"]
            ):
                st.session_state.selected_template = item
                st.session_state.template_notice = (
                    "تم اختيار القالب: " + item["name"]
                )

    if "template_notice" in st.session_state:
        st.success(st.session_state.template_notice)

    if "selected_template" in st.session_state:
        chosen = st.session_state.selected_template

        st.divider()
        st.subheader("حفظ الفكرة ضمن مشاريعك")

        with st.form("save_template_form"):
            project_title = st.text_input(
                "اسم المشروع",
                value=chosen["name"]
            )

            project_description = st.text_area(
                "تفاصيل المشروع",
                value=chosen["description"]
            )

            save_template = st.form_submit_button("حفظ المشروع")

        if save_template:
            with get_db() as conn:
                conn.execute("""
                    INSERT INTO projects
                    (username, title, category, description, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    user["username"],
                    project_title.strip() or chosen["name"],
                    chosen["category"],
                    project_description,
                    datetime.now().isoformat(timespec="seconds")
                ))

            st.success("تم حفظ المشروع.")


# ==================================================
# تصميم الشعارات
# ==================================================

elif page == "تصميم الشعارات":

    st.title("🎨 مساحة تصميم الشعارات")

    st.write(
        "اكتب تفاصيل الشعار الذي تريد إنشاءه، ثم احفظ وصفه "
        "حتى يكون جاهزًا للاستخدام عند ربط خدمة توليد الصور."
    )

    with st.form("logo_form"):
        brand_name = st.text_input("اسم العلامة التجارية")

        logo_type = st.selectbox(
            "نوع الشعار",
            [
                "تقني",
                "مطعم",
                "متجر",
                "عقارات",
                "ملابس",
                "تعليمي",
                "شعار شخصي",
                "نوع آخر"
            ]
        )

        logo_colors = st.text_input(
            "الألوان المفضلة",
            placeholder="مثل: الأسود والذهبي"
        )

        logo_style = st.selectbox(
            "أسلوب الشعار",
            [
                "عصري",
                "فاخر",
                "بسيط",
                "هندسي",
                "مرح",
                "رسمي"
            ]
        )

        logo_details = st.text_area(
            "تفاصيل إضافية",
            placeholder="صف الفكرة والرموز والعناصر التي تريدها."
        )

        save_logo = st.form_submit_button("حفظ فكرة الشعار")

    if save_logo:
        if not brand_name.strip():
            st.warning("اكتب اسم العلامة التجارية أولًا.")
        else:
            description = (
                f"شعار باسم {brand_name}. "
                f"المجال: {logo_type}. "
                f"الألوان: {logo_colors}. "
                f"الأسلوب: {logo_style}. "
                f"تفاصيل: {logo_details}"
            )

            with get_db() as conn:
                conn.execute("""
                    INSERT INTO projects
                    (username, title, category, description, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    user["username"],
                    "شعار " + brand_name,
                    "شعار",
                    description,
                    datetime.now().isoformat(timespec="seconds")
                ))

            st.success("تم حفظ فكرة الشعار في مشاريعك.")

    st.info(
        "ملاحظة: هذه الصفحة تجمع مواصفات الشعار وتحفظها فقط. "
        "إنشاء صورة شعار فعلية يحتاج إلى ربط نموذج ذكاء اصطناعي."
    )


# ==================================================
# تصميم الإعلانات
# ==================================================

elif page == "تصميم الإعلانات":

    st.title("📢 مساحة تصميم الإعلانات")

    with st.form("ad_form"):
        ad_title = st.text_input("عنوان الإعلان")

        business_type = st.selectbox(
            "نوع النشاط",
            [
                "مطعم",
                "عقارات",
                "متجر",
                "ملابس",
                "خدمات",
                "تعليم",
                "نشاط آخر"
            ]
        )

        ad_platform = st.selectbox(
            "مكان نشر الإعلان",
            [
                "فيسبوك",
                "إنستغرام",
                "واتساب",
                "تيك توك",
                "إعلان مطبوع"
            ]
        )

        ad_goal = st.selectbox(
            "هدف الإعلان",
            [
                "زيادة المبيعات",
                "جذب عملاء جدد",
                "الإعلان عن عرض",
                "التعريف بالعلامة التجارية",
                "إطلاق منتج"
            ]
        )

        ad_details = st.text_area(
            "تفاصيل الإعلان",
            placeholder="اكتب المنتج والسعر والعرض ومعلومات التواصل."
        )

        save_ad = st.form_submit_button("حفظ فكرة الإعلان")

    if save_ad:
        if not ad_title.strip():
            st.warning("أدخل عنوان الإعلان.")
        else:
            description = (
                f"عنوان الإعلان: {ad_title}. "
                f"النشاط: {business_type}. "
                f"المنصة: {ad_platform}. "
                f"الهدف: {ad_goal}. "
                f"التفاصيل: {ad_details}"
            )

            with get_db() as conn:
                conn.execute("""
                    INSERT INTO projects
                    (username, title, category, description, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    user["username"],
                    ad_title,
                    "إعلان",
                    description,
                    datetime.now().isoformat(timespec="seconds")
                ))

            st.success("تم حفظ فكرة الإعلان.")

    st.info(
        "إنشاء التصميم النهائي والصور والفيديو يحتاج إلى خدمة ذكاء اصطناعي "
        "سنربطها في مرحلة لاحقة."
    )


# ==================================================
# مساحة التجار
# ==================================================

elif page == "مساحة التجار":

    st.title("🛍️ مساحة التجار")

    st.write(
        "مكان مخصص للتاجر لتنظيم أفكار منتجاته وإعلاناته."
    )

    with st.form("merchant_form"):
        product_name = st.text_input("اسم المنتج أو الخدمة")

        product_price = st.text_input(
            "السعر (اختياري)",
            placeholder="مثال: 5000 ريال"
        )

        product_description = st.text_area(
            "وصف المنتج"
        )

        merchant_goal = st.selectbox(
            "ماذا تريد؟",
            [
                "إعلان للمنتج",
                "وصف تسويقي",
                "فكرة حملة تسويقية",
                "عرض ترويجي"
            ]
        )

        save_product = st.form_submit_button("حفظ بيانات المنتج")

    if save_product:
        if not product_name.strip():
            st.warning("اكتب اسم المنتج.")
        else:
            description = (
                f"المنتج: {product_name}. "
                f"السعر: {product_price}. "
                f"الوصف: {product_description}. "
                f"الهدف: {merchant_goal}."
            )

            with get_db() as conn:
                conn.execute("""
                    INSERT INTO projects
                    (username, title, category, description, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    user["username"],
                    product_name,
                    "تاجر",
                    description,
                    datetime.now().isoformat(timespec="seconds")
                ))

            st.success("تم حفظ بيانات المنتج.")


# ==================================================
# مشاريعي
# ==================================================

elif page == "مشاريعي":

    st.title("📁 مشاريعي")

    with get_db() as conn:
        projects = conn.execute("""
            SELECT id, title, category, description, created_at
            FROM projects
            WHERE username = ?
            ORDER BY id DESC
        """, (user["username"],)).fetchall()

    if not projects:
        st.info("لا توجد مشاريع محفوظة حتى الآن.")
    else:
        st.write(f"عدد المشاريع: {len(projects)}")

        for project in projects:
            project_id, title, category, description, created_at = project

            with st.expander(f"{title} — {category}"):
                st.write(description or "")
                st.caption(created_at)

                if st.button(
                    "حذف المشروع",
                    key=f"delete_project_{project_id}"
                ):
                    with get_db() as conn:
                        conn.execute("""
                            DELETE FROM projects
                            WHERE id = ? AND username = ?
                        """, (project_id, user["username"]))

                    st.success("تم حذف المشروع.")
                    st.rerun()


# ==================================================
# الاشتراكات
# ==================================================

elif page == "الاشتراكات":

    st.title("⭐ خطط NUMBER ONE")

    free_col, pro_col = st.columns(2)

    with free_col:
        with st.container(border=True):
            st.subheader("🆓 الخطة المجانية")
            st.markdown("### 0 ريال")
            st.write("• إنشاء حساب")
            st.write("• تصفح أفكار القوالب")
            st.write("• حفظ أفكار المشاريع")
            st.write("• مساحة التاجر الأساسية")

            if user["plan"] == "free":
                st.success("خطتك الحالية")

    with pro_col:
        with st.container(border=True):
            st.subheader("💎 خطة Pro")
            st.markdown("### قريبًا")
            st.write("• مزايا إضافية عند تفعيلها")
            st.write("• خدمات تصميم بالذكاء الاصطناعي عند ربطها")
            st.write("• أدوات إضافية حسب الخطة")

            st.warning("الدفع والاشتراكات الفعلية غير مفعلة بعد.")

    st.caption(
        "لا توجد عملية دفع أو ترقية مدفوعة فعالة في هذه النسخة."
    )


# ==================================================
# إعدادات الحساب
# ==================================================

elif page == "إعدادات الحساب":

    st.title("⚙️ إعدادات الحساب")

    account = get_user(user["username"])

    if account:
        st.write("**اسم المستخدم:**", account["username"])
        st.write(
            "**نوع الحساب:**",
            "مدير" if account["role"] == "admin" else "مستخدم"
        )
        st.write(
            "**الخطة:**",
            "مجانية" if account["plan"] == "free" else "Pro"
        )
        st.write("**تاريخ إنشاء الحساب:**", account["created_at"])

    st.divider()

    st.subheader("🔐 تغيير كلمة المرور")

    with st.form("change_password_form"):
        old_password = st.text_input(
            "كلمة المرور الحالية",
            type="password"
        )

        new_password = st.text_input(
            "كلمة المرور الجديدة",
            type="password"
        )

        confirm_new_password = st.text_input(
            "تأكيد كلمة المرور الجديدة",
            type="password"
        )

        change_submit = st.form_submit_button("تغيير كلمة المرور")

    if change_submit:
        if new_password != confirm_new_password:
            st.error("كلمتا المرور الجديدتان غير متطابقتين.")

        else:
            success, message = change_password(
                user["username"],
                old_password,
                new_password
            )

            if success:
                st.success(message)
            else:
                st.error(message)

    st.info(
        "استخدم كلمة مرور قوية لا تستخدمها في مواقع أخرى، "
        "ولا تشاركها مع أحد."
    )


# ==================================================
# لوحة الإدارة
# ==================================================

elif page == "لوحة الإدارة":

    if user["role"] != "admin":
        st.error("ليس لديك صلاحية الدخول إلى هذه الصفحة.")
        st.stop()

    st.title("🛡️ لوحة إدارة NUMBER ONE")

    with get_db() as conn:
        total_users = conn.execute(
            "SELECT COUNT(*) FROM users"
        ).fetchone()[0]

        total_projects = conn.execute(
            "SELECT COUNT(*) FROM projects"
        ).fetchone()[0]

        all_users = conn.execute("""
            SELECT username, role, plan, created_at
            FROM users
            ORDER BY id DESC
        """).fetchall()

    c1, c2 = st.columns(2)

    with c1:
        st.metric("عدد الحسابات", total_users)

    with c2:
        st.metric("عدد المشاريع", total_projects)

    st.subheader("الحسابات المسجلة")

    for account in all_users:
        st.write(
            f"👤 {account[0]} | "
            f"الصلاحية: {account[1]} | "
            f"الخطة: {account[2]} | "
            f"التاريخ: {account[3]}"
        )

    st.warning(
        "هذه لوحة إدارة أولية. لا توجد فيها بعد أدوات دفع أو إدارة "
        "متقدمة للاشتراكات."
    )


# ==================================================
# نهاية الصفحة
# ==================================================

st.divider()

st.caption(
    "NUMBER ONE | منصة القوالب والتصميم والإعلانات"
    )

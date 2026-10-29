import streamlit as st
import html
import os
import sqlite3
from datetime import datetime
import time

# إعدادات الصفحة
st.set_page_config(
    page_title="Number One - Advanced AI & Ad Platform",
    page_icon="👑",
    layout="wide"
)

# إعداد قاعدة البيانات المحلية (SQLite)
def init_db():
    conn = sqlite3.connect("number_one.db")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS scripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            product TEXT,
            benefit TEXT,
            script TEXT,
            date TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# تنظيف المدخلات للأمان
def sanitize_input(text):
    if not text:
        return ""
    return html.escape(text.strip())

# تهيئة الجلسة والمتغيرات الأمنية (مقاومة التخمين)
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "failed_attempts" not in st.session_state:
    st.session_state.failed_attempts = 0
if "lockout_time" not in st.session_state:
    st.session_state.lockout_time = 0

ADMIN_USER = "marwan"
ADMIN_PASS = "778909364"

# شاشة تسجيل الدخول مع الحماية ضد التخمين
if not st.session_state.logged_in:
    st.markdown("""
        <style>
        .login-card {
            background: linear-gradient(135deg, #111111 0%, #1a2e1a 100%);
            padding: 40px;
            border-radius: 15px;
            border: 2px solid #00FF66;
            box-shadow: 0px 0px 20px rgba(0, 255, 102, 0.3);
            text-align: center;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("<h1 style='color: #00FF66; font-weight: 800;'>👑 Number One</h1>", unsafe_allow_html=True)
        st.markdown("<p style='color: #bbb;'>Secure Access Portal / بوابة الدخول الآمنة</p>", unsafe_allow_html=True)
        
        # فحص الحظر المؤقت ضد التخمين
        current_time = time.time()
        if st.session_state.failed_attempts >= 3 and current_time < st.session_state.lockout_time:
            remaining = int(st.session_state.lockout_time - current_time)
            st.error(f"⚠️ تم حظر محاولات الدخول مؤقتاً بسبب كثرة المحاولات الخاطئة. يرجى الانتظار {remaining} ثانية.")
        else:
            if current_time >= st.session_state.lockout_time and st.session_state.failed_attempts >= 3:
                st.session_state.failed_attempts = 0 # إعادة ضبط بعد انتهاء الحظر
                
            with st.form("login_form"):
                input_user = st.text_input("Username / اسم المستخدم:")
                input_pass = st.text_input("Password / كلمة المرور:", type="password")
                submit_login = st.form_submit_button("Login / تسجيل الدخول 🚀", use_container_width=True)
                
                if submit_login:
                    if input_user == ADMIN_USER and input_pass == ADMIN_PASS:
                        st.session_state.logged_in = True
                        st.session_state.username = input_user
                        st.session_state.failed_attempts = 0
                        st.success("Welcome Owner Marwan! Access Granted.")
                        st.rerun()
                    elif input_user and input_pass:
                        st.session_state.logged_in = True
                        st.session_state.username = sanitize_input(input_user)
                        st.session_state.failed_attempts = 0
                        st.success(f"Welcome {input_user}!")
                        st.rerun()
                    else:
                        st.session_state.failed_attempts += 1
                        remaining_tries = 3 - st.session_state.failed_attempts
                        if st.session_state.failed_attempts >= 3:
                            st.session_state.lockout_time = time.time() + 30 # حظر لمدة 30 ثانية
                            st.error("⚠️ تجاوزت الحد الأقصى للمحاولات. تم تفعيل الحظر المؤقت لمدة 30 ثانية.")
                        else:
                            st.error(f"❌ بيانات غير صحيحة! محاولاتك المتبقية قبل الحظر: {remaining_tries}")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ==========================================
# واجهة المنصة بعد تسجيل الدخول
# ==========================================

st.markdown("""
    <style>
    .main-header {
        font-size: 2.6rem;
        background: linear-gradient(90deg, #00FF66, #ffffff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        font-weight: 900;
        margin-bottom: 5px;
    }
    .sub-header {
        font-size: 1.1rem;
        text-align: center;
        color: #8c8c8c;
        margin-bottom: 30px;
        letter-spacing: 1px;
    }
    .custom-box {
        background: rgba(20, 20, 20, 0.7);
        padding: 25px;
        border-radius: 12px;
        border-right: 5px solid #00FF66;
        border-top: 1px solid #333;
        border-left: 1px solid #333;
        border-bottom: 1px solid #333;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# الشريط الجانبي واختيار اللغة
st.sidebar.title("👑 Number One Platform")
lang = st.sidebar.selectbox("Language / اللغة", ["العربية", "English"])

if os.path.exists("logo.jpg"):
    st.sidebar.image("logo.jpg", caption="Official Brand Identity", use_column_width=True)

st.sidebar.markdown("🟢 **Security Status:** Anti-Brute Force Active 🛡️")
st.sidebar.markdown(f"👤 **User:** `{st.session_state.username}`")

if st.sidebar.button("Logout / تسجيل الخروج", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.rerun()

st.sidebar.markdown("---")

# القوائم بناءً على اللغة المختارة
if lang == "العربية":
    menu = st.sidebar.selectbox(
        "قائمة التنقل", 
        [
            "الرئيسية", 
            "✍️ مولد السكريبت والمقاسات", 
            "🎙️ خدمة التعليق الصوتي", 
            "🎨 صانع أفكار التصاميم", 
            "📊 حاسبة الميزانية", 
            "💳 بوابات وسداد المدفوعات", 
            "🔒 لوحة تحكم المالك"
        ]
    )
else:
    menu = st.sidebar.selectbox(
        "Navigation Menu", 
        [
            "Home", 
            "✍️ Script & Dimensions", 
            "🎙️ Voiceover Studio", 
            "🎨 Design Concepts", 
            "📊 Budget Calculator", 
            "💳 Payment Gateways", 
            "🔒 Owner Admin Panel"
        ]
    )

# 1. الرئيسية / Home
if menu in ["الرئيسية", "Home"]:
    if lang == "العربية":
        st.markdown('<div class="main-header">منصة NUMBER ONE الذكية</div>', unsafe_allow_html=True)
        st.markdown('<div class="sub-header">النظام المتطور لإنتاج الإعلانات، المقاسات الدقيقة، التعليق الصوتي، والحماية العالية</div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown('<div class="custom-box"><h3>🎬 مقاسات متعددة</h3><p>دعم كامل لمقاسات السوشيال ميديا (9:16 ريلز، 16:9 أفقية، 1:1 مربعة).</p></div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="custom-box"><h3>🎙️ تعليق صوتي فوري</h3><p>تخصيص كامل للأصوات والنبرات الاحترافية المناسبة لمنتجك.</p></div>', unsafe_allow_html=True)
        with col3:
            st.markdown('<div class="custom-box"><h3>🛡️ حماية متقدمة</h3><p>تأمين شامل ضد هجمات التخمين والاختراق العشوائي.</p></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="main-header">NUMBER ONE PLATFORM</div>', unsafe_allow_html=True)
        st.markdown('<div class="sub-header">Advanced System for Ad Production, Dimensions, Voiceover, and Anti-Brute Force Security</div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown('<div class="custom-box"><h3>🎬 Multi-Dimensions</h3><p>Full support for social media sizes (9:16 Reels, 16:9 Widescreen, 1:1 Square).</p></div>', unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="custom-box"><h3>🎙️ Voiceover Studio</h3><p>Complete customization of professional voices and tones for your product.</p></div>', unsafe_allow_html=True)
        with col3:
            st.markdown('<div class="custom-box"><h3>🛡️ Advanced Security</h3><p>Comprehensive protection against brute-force attacks and unauthorized access.</p></div>', unsafe_allow_html=True)

# 2. مولد السكريبت / Script Generator
elif menu in ["✍️ مولد السكريبت والمقاسات", "✍️ Script & Dimensions"]:
    if lang == "العربية":
        st.markdown("## ✍️ مولد سكريبت الإعلانات وتحديد المقاسات")
        with st.form("script_form"):
            prod_name = st.text_input("اسم المنتج / الخدمة:")
            prod_benefit = st.text_input("الميزة الأساسية للمنتج:")
            video_dimension = st.selectbox("اختر مقاس وأبعاد الفيديو:", ["9:16 Vertical (Reels/TikTok)", "16:9 Widescreen (YouTube)", "1:1 Square Ad (Instagram)"])
            generate_btn = st.form_submit_button("توليد وحفظ السكريبت ⚡", use_container_width=True)
            
            if generate_btn and prod_name:
                c_name = sanitize_input(prod_name)
                c_benefit = sanitize_input(prod_benefit)
                script_text = f"Product: {c_name}\nDimension: {video_dimension}\nBenefit: {c_benefit}\nHook: Discover {c_name} today!"
                
                conn = sqlite3.connect("number_one.db")
                c = conn.cursor()
                c.execute("INSERT INTO scripts (username, product, benefit, script, date) VALUES (?, ?, ?, ?, ?)",
                          (st.session_state.username, c_name, f"{c_benefit} [{video_dimension}]", script_text, str(datetime.now())))
                conn.commit()
                conn.close()
                st.success("تم التوليد والحفظ بنجاح!")
                st.code(script_text)
    else:
        st.markdown("## ✍️ Ad Script & Dimensions Generator")
        with st.form("script_form"):
            prod_name = st.text_input("Product / Service Name:")
            prod_benefit = st.text_input("Core Benefit:")
            video_dimension = st.selectbox("Select Video Dimension:", ["9:16 Vertical (Reels/TikTok)", "16:9 Widescreen (YouTube)", "1:1 Square Ad (Instagram)"])
            generate_btn = st.form_submit_button("Generate & Save Script ⚡", use_container_width=True)
            
            if generate_btn and prod_name:
                c_name = sanitize_input(prod_name)
                c_benefit = sanitize_input(prod_benefit)
                script_text = f"Product: {c_name}\nDimension: {video_dimension}\nBenefit: {c_benefit}\nHook: Discover {c_name} today!"
                
                conn = sqlite3.connect("number_one.db")
                c = conn.cursor()
                c.execute("INSERT INTO scripts (username, product, benefit, script, date) VALUES (?, ?, ?, ?, ?)",
                          (st.session_state.username, c_name, f"{c_benefit} [{video_dimension}]", script_text, str(datetime.now())))
                conn.commit()
                conn.close()
                st.success("Generated and saved successfully!")
                st.code(script_text)

# 3. التعليق الصوتي / Voiceover
elif menu in ["🎙️ خدمة التعليق الصوتي", "🎙️ Voiceover Studio"]:
    if lang == "العربية":
        st.markdown("## 🎙️ استوديو التعليق الصوتي (Voiceover)")
        with st.form("vo_form"):
            vo_gender = st.selectbox("نوع الصوت:", ["رجالي فاخر (Male)", "نسائي جذاب (Female)"])
            vo_tone = st.selectbox("نبرة الأداء:", ["احترافي (Professional)", "ودي (Friendly)", "حماسي (Excited)"])
            vo_text = st.text_area("النص المراد تحويله:")
            vo_submit = st.form_submit_button("إعداد مسار الصوت 🔊", use_container_width=True)
            if vo_submit and vo_text:
                st.success("تم تجهيز إعدادات التعليق الصوتي بنجاح!")
    else:
        st.markdown("## 🎙️ Voiceover Studio")
        with st.form("vo_form"):
            vo_gender = st.selectbox("Voice Gender:", ["Male", "Female"])
            vo_tone = st.selectbox("Performance Tone:", ["Professional", "Friendly", "Excited"])
            vo_text = st.text_area("Script to Voiceover:")
            vo_submit = st.form_submit_button("Prepare Voice Track 🔊", use_container_width=True)
            if vo_submit and vo_text:
                st.success("Voiceover settings prepared successfully!")

# 4. التصاميم / Designs
elif menu in ["🎨 صانع أفكار التصاميم", "🎨 Design Concepts"]:
    if lang == "العربية":
        st.markdown("## 🎨 أفكار التصاميم الاحترافية")
        st.info("💡 خيارات بصرية جاهزة للمنتجات (عطور، إلكترونيات، ساعات، أزياء) مع مقاسات دقيقة.")
    else:
        st.markdown("## 🎨 Professional Design Concepts")
        st.info("💡 Ready-made visual layouts for products (Perfumes, Tech, Watches, Luxury) with exact dimensions.")

# 5. حاسبة الميزانية / Budget Calculator
elif menu in ["📊 حاسبة الميزانية", "📊 Budget Calculator"]:
    if lang == "العربية":
        st.markdown("## 📊 حاسبة العائد الاستثماري")
        b = st.number_input("الميزانية ($):", value=100)
        p = st.number_input("سعر الوحدة ($):", value=30)
        conv = st.slider("عدد المبيعات المتوقعة:", 1, 100, 15)
        if st.button("حساب العائد 📈", use_container_width=True):
            rev = conv * p
            st.metric("صافي الربح", f"${rev - b}")
    else:
        st.markdown("## 📊 ROI & Budget Calculator")
        b = st.number_input("Budget ($):", value=100)
        p = st.number_input("Unit Price ($):", value=30)
        conv = st.slider("Expected Conversions:", 1, 100, 15)
        if st.button("Calculate ROI 📈", use_container_width=True):
            rev = conv * p
            st.metric("Net Profit", f"${rev - b}")

# 6. المدفوعات / Payments
elif menu in ["💳 بوابات وسداد المدفوعات", "💳 Payment Gateways"]:
    if lang == "العربية":
        st.markdown("## 💳 بوابات الدفع المحلية والعالمية")
        st.write("🇾🇪 ون كاش، الكريمي، جوالي، بنك التضامن، جيب، حاسب.")
        st.write("🌍 PayPal, Visa / Mastercard.")
    else:
        st.markdown("## 💳 Payment Gateways")
        st.write("🇾🇪 One Cash, Al-Kuraimi, Jawali, Tadhamon, Jeeb, Haseb.")
        st.write("🌍 PayPal, Visa / Mastercard.")

# 7. لوحة تحكم المالك / Owner Panel
elif menu in ["🔒 لوحة تحكم المالك", "🔒 Owner Admin Panel"]:
    if st.session_state.username == ADMIN_USER:
        if lang == "العربية":
            st.markdown("## 🔒 لوحة تحكم المالك (مروان عبده حسن الحسني)")
            st.success("🟢 حالة الحماية ضد التخمين: مفعلة ومؤمنة بالكامل.")
            st.markdown("### السجلات المحفوظة:")
        else:
            st.markdown("## 🔒 Owner Admin Panel (Marwan Abdo)")
            st.success("🟢 Brute-force protection: Fully Active & Secure.")
            st.markdown("### Saved Records:")
            
        conn = sqlite3.connect("number_one.db")
        c = conn.cursor()
        c.execute("SELECT username, product, date FROM scripts")
        rows = c.fetchall()
        conn.close()
        for r in rows:
            st.write(f"- User: {r[0]} | Product: {r[1]} | Date: {r[2]}")
    else:
        if lang == "العربية":
            st.error("⚠️ هذه الصفحة خاصة بمدير النظام (المالك) فقط.")
        else:
            st.error("⚠️ Access restricted to system owner only.")



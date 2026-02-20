import streamlit as st
import os
from openai import OpenAI
from dotenv import load_dotenv
import sqlite3
from datetime import datetime
import hashlib

# =============================
# OpenAI設定
# =============================
load_dotenv()
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# =============================
# SQLite設定
# =============================
DB_FILE = "diary.db"
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()

# ユーザーテーブル
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT
)
""")

# 日記テーブル
c.execute("""
CREATE TABLE IF NOT EXISTS diaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    datetime TEXT,
    content TEXT,
    FOREIGN KEY(username) REFERENCES users(username)
)
""")
conn.commit()

# =============================
# ユーティリティ
# =============================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password):
    c.execute("INSERT INTO users (username, password) VALUES (?, ?)",
              (username, hash_password(password)))
    conn.commit()

def check_user(username, password):
    c.execute("SELECT password FROM users WHERE username=?", (username,))
    row = c.fetchone()
    return row and row[0] == hash_password(password)

def save_diary(username, content):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute("INSERT INTO diaries (username, datetime, content) VALUES (?, ?, ?)",
              (username, now, content))
    conn.commit()
    return now

def load_user_diaries(username):
    c.execute("SELECT datetime, content FROM diaries WHERE username=? ORDER BY datetime DESC", (username,))
    return c.fetchall()

# =============================
# UI設定
# =============================
st.set_page_config(page_title="AI Diary", layout="centered")

st.markdown("""
<style>
.stApp { background: linear-gradient(135deg, #1e1e2f, #2b2b45); color: white; }
.block-container { max-width: 480px; padding-top: 2rem; }
.card { background: rgba(255,255,255,0.05); padding: 20px; border-radius: 20px; backdrop-filter: blur(10px); box-shadow: 0 8px 20px rgba(0,0,0,0.3); margin-bottom: 20px; }
.section-title { font-size: 18px; font-weight: 600; margin-bottom: 10px; }
.stButton > button, .stDownloadButton > button { width: 100%; border-radius: 15px; height: 50px; font-size: 16px; font-weight: 600; background: linear-gradient(90deg,#6a5acd,#00c9ff) !important; color: white !important; border: none !important; }
.stTextArea textarea { border-radius: 15px !important; background-color: white !important; color: black !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<h1 style='text-align:center; font-weight:800;'>🌙 AI Diary</h1>
<p style='text-align:center; opacity:0.7;'>今日の気持ちを、物語に。</p>
""", unsafe_allow_html=True)

# =============================
# セッションステート初期化
# =============================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "step" not in st.session_state:
    st.session_state.step = "login"
if "username" not in st.session_state:
    st.session_state.username = ""
if "summary" not in st.session_state:
    st.session_state.summary = ""
if "first_questions" not in st.session_state:
    st.session_state.first_questions = []
if "first_answers" not in st.session_state:
    st.session_state.first_answers = []
if "diary" not in st.session_state:
    st.session_state.diary = ""

# =============================
# ログイン画面
# =============================
if not st.session_state.logged_in:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🔐 ログイン / 新規登録</div>', unsafe_allow_html=True)

    username_input = st.text_input("ユーザー名", key="login_username")
    password_input = st.text_input("パスワード", type="password", key="login_password")

    col1, col2 = st.columns(2)
    with col1:
        login = st.button("ログイン", key="login_button")
    with col2:
        register = st.button("新規登録", key="register_button")

    if login:
        if check_user(username_input, password_input):
            st.session_state.logged_in = True
            st.session_state.username = username_input
            st.session_state.step = "input_summary"
            st.success("ログイン成功！")
            st.experimental_rerun()
        else:
            st.error("ユーザー名またはパスワードが違います")

    if register:
        c.execute("SELECT username FROM users WHERE username=?", (username_input,))
        if c.fetchone():
            st.error("そのユーザー名は既に存在します")
        else:
            register_user(username_input, password_input)
            st.success("登録完了！ログインしてください")

    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# =============================
# 今日の出来事入力
# =============================
if st.session_state.step == "input_summary":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📝 今日の出来事</div>', unsafe_allow_html=True)

    summary = st.text_area(
        "",
        placeholder="例）友達とカフェに行った。部活が大変だった…",
        height=120,
        key="summary_input"
    )

    col1, col2 = st.columns(2)
    with col1:
        generate_questions = st.button("✍️ 質問を作る", key="generate_first_questions")
    with col2:
        generate_diary_direct = st.button("📓 そのまま日記生成", key="generate_diary_direct")

    # 質問生成
    if generate_questions and summary.strip():
        st.session_state.summary = summary
        with st.spinner("質問生成中..."):
            prompt = f"""
出来事: {summary}

この出来事を日記にするための基本的な質問を作ってください。
「何をした」「誰と話した」「印象に残った出来事は」「気持ちはどうだった」など、事実を聞く質問を4つ作ってください。
"""
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
            )
            questions_text = response.choices[0].message.content
            st.session_state.first_questions = [
                q.strip("0123456789. ").strip()
                for q in questions_text.split("\n") if q.strip()
            ]
            st.session_state.first_answers = [""] * len(st.session_state.first_questions)
            st.session_state.step = "first_q"

    # 日記直接生成
    if generate_diary_direct and summary.strip():
        st.session_state.summary = summary
        with st.spinner("日記生成中..."):
            diary_prompt = f"""
出来事: {summary}

この出来事を元に、今日の感情や空気感も含めた日記を書いてください。
・出来事を整理するだけでなく、空気や感情が伝わる文章にしてください。
・その時の言葉や思考も自然に含めてください。
・身体の感覚や音・空気感も描写してください。
・少し迷いや揺れを残す文章にしてください。
・未来の自分が読んで情景を思い出せる文章にしてください。
"""
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": diary_prompt}],
            )
            st.session_state.diary = response.choices[0].message.content
            save_diary(st.session_state.username, st.session_state.diary)
            st.session_state.step = "diary"
            st.success("日記を保存しました！")

    st.markdown('</div>', unsafe_allow_html=True)

# =============================
# 過去日記表示
# =============================
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">📚 過去の日記</div>', unsafe_allow_html=True)

user_diaries = load_user_diaries(st.session_state.username)
if user_diaries:
    sorted_dates = [d[0] for d in user_diaries]
    selected_date = st.selectbox(
        "",
        sorted_dates,
        key="selected_date"
    )
    diary_text = next(content for dt, content in user_diaries if dt == selected_date)

    st.text_area(
        "",
        value=diary_text,
        height=200,
        key="past_diary_view"
    )
else:
    st.info("まだ日記がありません。")

st.markdown('</div>', unsafe_allow_html=True)

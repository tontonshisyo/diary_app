import streamlit as st
import os
from openai import OpenAI
from dotenv import load_dotenv
import json
from datetime import datetime
import hashlib

# =============================
# OpenAI設定
# =============================
load_dotenv()
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# =============================
# ファイル設定
# =============================
DIARY_FILE = "saved_diaries.json"
USER_FILE = "users.json"

# =============================
# ユーティリティ
# =============================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_json(file):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# =============================
# UI設定
# =============================
st.set_page_config(page_title="AI Diary", layout="centered")

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #1e1e2f, #2b2b45);
    color: white;
}
.block-container {
    max-width: 480px;
    padding-top: 2rem;
}
.card {
    background: rgba(255,255,255,0.05);
    padding: 20px;
    border-radius: 20px;
    backdrop-filter: blur(10px);
    box-shadow: 0 8px 20px rgba(0,0,0,0.3);
    margin-bottom: 20px;
}
.section-title {
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 10px;
}
.stButton > button,
.stDownloadButton > button {
    width: 100%;
    border-radius: 15px;
    height: 50px;
    font-size: 16px;
    font-weight: 600;
    background: linear-gradient(90deg,#6a5acd,#00c9ff) !important;
    color: white !important;
    border: none !important;
}
.stTextArea textarea {
    border-radius: 15px !important;
    background-color: white !important;
    color: black !important;
}
</style>
""", unsafe_allow_html=True)

# =============================
# タイトル
# =============================
st.markdown("""
<h1 style='text-align:center; font-weight:800;'>🌙 AI Diary</h1>
<p style='text-align:center; opacity:0.7;'>今日の気持ちを、物語に。</p>
""", unsafe_allow_html=True)

# =============================
# ログインUI
# =============================
users = load_json(USER_FILE)

st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">🔐 ログイン / 新規登録</div>', unsafe_allow_html=True)

username = st.text_input("ユーザー名", key="login_username")
password = st.text_input("パスワード", type="password", key="login_password")

col1, col2 = st.columns(2)
with col1:
    login = st.button("ログイン", key="login_button")
with col2:
    register = st.button("新規登録", key="register_button")

if login:
    if username in users and users[username] == hash_password(password):
        st.session_state.logged_in = True
        st.session_state.username = username
        st.success("ログイン成功！")
    else:
        st.error("ユーザー名またはパスワードが違います")

if register:
    if username in users:
        st.error("そのユーザー名は既に存在します")
    else:
        users[username] = hash_password(password)
        save_json(USER_FILE, users)
        st.success("登録完了！ログインしてください")

st.markdown('</div>', unsafe_allow_html=True)

if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.stop()

# =============================
# ログイン後処理
# =============================
diaries = load_json(DIARY_FILE)
if st.session_state.username not in diaries:
    diaries[st.session_state.username] = {}

if "questions" not in st.session_state:
    st.session_state.questions = []
if "diary" not in st.session_state:
    st.session_state.diary = ""

# =============================
# 今日の出来事
# =============================
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">📝 今日の出来事</div>', unsafe_allow_html=True)

summary = st.text_area(
    "",
    placeholder="例）友達とカフェに行った。部活が大変だった…",
    height=120,
    key="summary_input"
)

if st.button("✍️ 質問を作る", key="generate_questions"):
    if summary.strip():
        with st.spinner("質問生成中..."):
            prompt = f"""
出来事: {summary}

日記作成用に具体的な質問を4つ作成。
会話・感情・身体/空気・迷いを各1問。
抽象禁止。情景が浮かぶ形で、1問1文。
"""
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
            )
            questions_text = response.choices[0].message.content
            st.session_state.questions = [
                q.strip("0123456789. ").strip()
                for q in questions_text.split("\n")
                if q.strip()
            ]

st.markdown('</div>', unsafe_allow_html=True)

# =============================
# 質問回答
# =============================
if st.session_state.questions:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📝 質問に答えてください</div>', unsafe_allow_html=True)

    answers = []
    for i, q in enumerate(st.session_state.questions):
        st.markdown(f"<div class='section-title'>{q}</div>", unsafe_allow_html=True)
        a = st.text_area("", key=f"answer_{i}")
        answers.append((q, a))

    if st.button("📓 日記を生成する", key="generate_diary"):
        with st.spinner("生成中..."):
            qna_text = "\n".join([f"{q} {a}" for q, a in answers])
            diary_prompt = f"""
出来事: {summary}

質問と回答:
{qna_text}

自然で感情のこもった日記を書いてください。
です・ます調で。
"""
            diary_response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": diary_prompt}],
            )
            diary = diary_response.choices[0].message.content
            st.session_state.diary = diary

            today = datetime.today().strftime("%Y-%m-%d %H:%M")
            diaries[st.session_state.username][today] = diary
            save_json(DIARY_FILE, diaries)

            st.success("日記を保存しました！")

    st.markdown('</div>', unsafe_allow_html=True)

# =============================
# 日記表示
# =============================
if st.session_state.diary:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📘 あなたの日記</div>', unsafe_allow_html=True)

    edited = st.text_area(
        "",
        value=st.session_state.diary,
        height=200,
        key="current_diary_edit"
    )

    st.download_button(
        "💾 日記を保存する（テキストファイル）",
        edited,
        file_name="my_diary.txt",
        key="download_button"
    )

    st.markdown('</div>', unsafe_allow_html=True)

# =============================
# 過去日記
# =============================
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">📚 過去の日記</div>', unsafe_allow_html=True)

user_diaries = diaries[st.session_state.username]

if user_diaries:
    selected_date = st.selectbox(
        "",
        list(user_diaries.keys())[::-1],
        key="selected_date"
    )

    st.text_area(
        "",
        value=user_diaries[selected_date],
        height=200,
        key="past_diary_view"
    )
else:
    st.info("まだ日記がありません。")

st.markdown('</div>', unsafe_allow_html=True)


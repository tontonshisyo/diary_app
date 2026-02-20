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

# =============================
# ログインUI
# =============================
users = load_json(USER_FILE)

st.markdown("## 🔐 ログイン / 新規登録")

username = st.text_input("ユーザー名")
password = st.text_input("パスワード", type="password")

col1, col2 = st.columns(2)

with col1:
    login = st.button("ログイン")
with col2:
    register = st.button("新規登録")

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

# ログインしていない場合は停止
if "logged_in" not in st.session_state or not st.session_state.logged_in:
    st.stop()

# =============================
# ログイン後処理
# =============================
st.markdown(f"### 👋 ようこそ {st.session_state.username} さん")

diaries = load_json(DIARY_FILE)

if st.session_state.username not in diaries:
    diaries[st.session_state.username] = {}

# セッション初期化
if "questions" not in st.session_state:
    st.session_state.questions = []
if "diary" not in st.session_state:
    st.session_state.diary = ""

# =============================
# 出来事入力
# =============================
st.markdown("### 📝 今日の出来事")

summary = st.text_area("")

if st.button("✍️ 質問を作る") and summary.strip():
    with st.spinner("質問生成中..."):
        prompt = f"""
以下の出来事を日記に書くために、質問を3つ作ってください。
出来事: {summary}
質問は感情や背景を引き出すものにしてください。
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

# =============================
# 質問回答
# =============================
if st.session_state.questions:
    answers = []
    for i, q in enumerate(st.session_state.questions):
        st.write(q)
        a = st.text_area("", key=f"answer_{i}")
        answers.append((q, a))

    if st.button("📓 日記を生成する"):
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

# =============================
# 日記表示
# =============================
if st.session_state.diary:
    st.markdown("### 📘 あなたの日記")
    edited = st.text_area("", value=st.session_state.diary, height=200)
    st.session_state.diary = edited

    st.download_button(
        "💾 テキスト保存",
        edited,
        file_name="my_diary.txt"
    )

# =============================
# 過去日記
# =============================
st.markdown("### 📚 過去の日記")

user_diaries = diaries[st.session_state.username]

if user_diaries:
    selected_date = st.selectbox(
        "日付を選択",
        list(user_diaries.keys())[::-1]
    )

    st.text_area(
        "",
        value=user_diaries[selected_date],
        height=200
    )
else:
    st.info("まだ日記がありません。")

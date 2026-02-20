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
# ログイン処理
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

# セッションステート初期化
if "step" not in st.session_state:
    st.session_state.step = "input_summary"  # input_summary → first_q → first_a → deep_q → deep_a → diary
if "summary" not in st.session_state:
    st.session_state.summary = ""
if "first_questions" not in st.session_state:
    st.session_state.first_questions = []
if "first_answers" not in st.session_state:
    st.session_state.first_answers = []
if "deep_questions" not in st.session_state:
    st.session_state.deep_questions = []
if "deep_answers" not in st.session_state:
    st.session_state.deep_answers = []
if "diary" not in st.session_state:
    st.session_state.diary = ""

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

    if st.button("✍️ 質問を作る", key="generate_first_questions"):
        if summary.strip():
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

    st.markdown('</div>', unsafe_allow_html=True)

# =============================
# 一次質問回答
# =============================
if st.session_state.step == "first_q":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📝 基本質問に答えてください</div>', unsafe_allow_html=True)

    for i, q in enumerate(st.session_state.first_questions):
        st.markdown(f"<div class='section-title'>{q}</div>", unsafe_allow_html=True)
        st.session_state.first_answers[i] = st.text_area(
            "",
            value=st.session_state.first_answers[i],
            key=f"first_answer_{i}"
        )

    if st.button("➡ 深掘り質問を作る", key="generate_deep_questions"):
        with st.spinner("深掘り質問生成中..."):
            first_qna_text = "\n".join([f"{q} {a}" for q, a in zip(st.session_state.first_questions, st.session_state.first_answers)])
            prompt = f"""
一次回答:
{first_qna_text}

この回答をもとに、感情・身体感覚・空気感・迷いなどを引き出す深掘り質問を作ってください。
それぞれの質問は具体的で、今日の出来事に沿ったものにしてください。
4問程度作成してください。
"""
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
            )
            questions_text = response.choices[0].message.content
            st.session_state.deep_questions = [
                q.strip("0123456789. ").strip()
                for q in questions_text.split("\n") if q.strip()
            ]
            st.session_state.deep_answers = [""] * len(st.session_state.deep_questions)
            st.session_state.step = "deep_q"

    st.markdown('</div>', unsafe_allow_html=True)

# =============================
# 深掘り質問回答
# =============================
if st.session_state.step == "deep_q":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📝 深掘り質問に答えてください</div>', unsafe_allow_html=True)

    for i, q in enumerate(st.session_state.deep_questions):
        st.markdown(f"<div class='section-title'>{q}</div>", unsafe_allow_html=True)
        st.session_state.deep_answers[i] = st.text_area(
            "",
            value=st.session_state.deep_answers[i],
            key=f"deep_answer_{i}"
        )

    if st.button("📓 日記を生成する", key="generate_final_diary"):
        with st.spinner("日記生成中..."):
            all_qna_text = "\n".join(
                [f"{q} {a}" for q, a in zip(st.session_state.first_questions + st.session_state.deep_questions,
                                            st.session_state.first_answers + st.session_state.deep_answers)]
            )
            diary_prompt = f"""
出来事: {st.session_state.summary}

質問と回答:
{all_qna_text}

これらの回答から日記を書いてください。

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
            today = datetime.today().strftime("%Y-%m-%d %H:%M")
            diaries[st.session_state.username][today] = st.session_state.diary
            save_json(DIARY_FILE, diaries)
            st.session_state.step = "diary"
        st.success("日記を保存しました！")

# =============================
# 日記表示
# =============================
if st.session_state.step == "diary" and st.session_state.diary:
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
# 過去日記表示
# =============================
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">📚 過去の日記</div>', unsafe_allow_html=True)

user_diaries = diaries.get(st.session_state.username, {})
if user_diaries:
    sorted_dates = sorted(user_diaries.keys(), reverse=True)
    selected_date = st.selectbox(
        "",
        sorted_dates,
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

import streamlit as st
import os
from openai import OpenAI
from dotenv import load_dotenv
import json
from datetime import datetime

# 環境変数からAPIキーを読み込む
load_dotenv()
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# 保存用ファイル
DIARY_FILE = "saved_diaries.json"

# JSON形式で日記を保存・読み込み
def load_diaries():
    if os.path.exists(DIARY_FILE):
        with open(DIARY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_diaries(diaries):
    with open(DIARY_FILE, "w", encoding="utf-8") as f:
        json.dump(diaries, f, ensure_ascii=False, indent=2)

# UI設定
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

.stButton > button {
    width: 100%;
    border-radius: 15px;
    height: 50px;
    font-size: 16px;
    font-weight: 600;
    background: linear-gradient(90deg,#6a5acd,#00c9ff) !important;
    color: white !important;
    border: none !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}

/* hover時 */
.stButton > button:hover {
    background: linear-gradient(90deg,#7b6cff,#33d6ff) !important;
    color: white !important;
}

/* クリック時 */
.stButton > button:active {
    transform: scale(0.98);
}

.stTextArea textarea {
    border-radius: 15px !important;
    background-color: white !important;
    color: black !important;
}

.section-title {
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 8px;
}
.stDownloadButton > button {
    width: 100%;
    border-radius: 15px;
    height: 50px;
    font-size: 16px;
    font-weight: 600;
    background: linear-gradient(90deg,#6a5acd,#00c9ff) !important;
    color: white !important;
    border: none !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}

.stDownloadButton > button:hover {
    background: linear-gradient(90deg,#7b6cff,#33d6ff) !important;
}
</style>
""", unsafe_allow_html=True)

# タイトル
st.markdown("""
<h1 style='text-align:center; font-weight:800; margin-bottom:0;'>
🌙 AI Diary
</h1>
<p style='text-align:center; opacity:0.7; margin-top:5px; margin-bottom:30px;'>
今日の気持ちを、物語に。
</p>
""", unsafe_allow_html=True)

# セッション初期化
if "questions" not in st.session_state:
    st.session_state.questions = []
if "qna" not in st.session_state:
    st.session_state.qna = []
if "diary" not in st.session_state:
    st.session_state.diary = ""
if "saved_diaries" not in st.session_state:
    st.session_state.saved_diaries = load_diaries()

# ===== 出来事入力 =====
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">📝 今日の出来事</div>', unsafe_allow_html=True)

summary = st.text_area(
    "",
    placeholder="例）友達とカフェに行った。テストが返ってきた。部活が大変だった…",
    height=120,
    key="summary_input"
)

if st.button("✍️ 質問を作る") and summary.strip():
    with st.spinner("🤖 質問を生成中..."):
        prompt = (
            f"以下の出来事を日記に書くために、質問を3つ作ってください。\n"
            f"出来事: {summary}\n"
            f"質問は答えやすく、感情や背景を引き出すようにしてください。"
        )
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
        st.success("✅ 質問を作成しました！")

st.markdown('</div>', unsafe_allow_html=True)

# ===== 質問回答 =====
if st.session_state.questions:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📝 質問に答えてください</div>', unsafe_allow_html=True)

    answers = []
    for i, q in enumerate(st.session_state.questions):
        st.markdown(f"<div class='section-title'>{q}</div>", unsafe_allow_html=True)
        a = st.text_area("", key=f"answer_{i}")
        answers.append((q, a))

    st.session_state.qna = answers

    if st.button("📓 日記を生成する"):
        with st.spinner("生成中..."):
            qna_text = "\n".join([f"{q} {a}" for q, a in answers])
            diary_prompt = (
                f"以下の出来事と質問回答をもとに、自然で感情のこもった日記を書いてください。\n"
                f"出来事: {summary}\n"
                f"質問と回答:\n{qna_text}\n\n"
                f"日記は『です・ます調』でお願いします。"
            )
            diary_response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": diary_prompt}],
            )
            diary = diary_response.choices[0].message.content
            st.session_state.diary = diary

            today = datetime.today().strftime("%Y-%m-%d %H:%M")
            st.session_state.saved_diaries[today] = diary
            save_diaries(st.session_state.saved_diaries)

            st.success("✅ 日記が生成され、保存されました！")

    st.markdown('</div>', unsafe_allow_html=True)

# ===== 日記表示 =====
if st.session_state.diary:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📘 あなたの日記</div>', unsafe_allow_html=True)

    edited_diary = st.text_area(
        "",
        value=st.session_state.diary,
        height=200,
        key="generated_diary"
    )

    st.session_state.diary = edited_diary

    st.download_button(
        "💾 日記を保存する（テキストファイル）",
        st.session_state.diary,
        file_name="my_diary.txt"
    )

    st.markdown('</div>', unsafe_allow_html=True)

# ===== 過去日記 =====
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">📚 過去の日記</div>', unsafe_allow_html=True)

if st.session_state.saved_diaries:
    selected_date = st.selectbox(
        "",
        list(st.session_state.saved_diaries.keys())[::-1],
        key="date_selector"
    )

    st.text_area(
        "",
        value=st.session_state.saved_diaries[selected_date],
        height=200
    )
else:
    st.info("まだ保存された日記がありません。")

st.markdown('</div>', unsafe_allow_html=True)







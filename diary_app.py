import streamlit as st
import os
from openai import OpenAI
from dotenv import load_dotenv
import json
from datetime import datetime

# 環境変数からAPIキーを読み込む
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

# Streamlit UI設定
st.set_page_config(page_title="日記生成アプリ", layout="centered")
st.title("📘 日記生成アプリ（GPT-3.5 Turbo）")

# 日記データの初期化
if "questions" not in st.session_state:
    st.session_state.questions = []
if "qna" not in st.session_state:
    st.session_state.qna = []
if "diary" not in st.session_state:
    st.session_state.diary = ""
if "saved_diaries" not in st.session_state:
    st.session_state.saved_diaries = load_diaries()

# 出来事入力
summary = st.text_area("今日の出来事をざっくり入力してください:")

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
        st.session_state.questions = [q.strip("0123456789. ").strip() for q in questions_text.split("\n") if q.strip()]
        st.success("✅ 質問を作成しました！")

# 質問に回答
if st.session_state.questions:
    st.subheader("📝 質問に答えてください：")
    answers = []
    for i, q in enumerate(st.session_state.questions):
        a = st.text_area(f"{q}", key=f"answer_{i}")
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

            # 保存
            today = datetime.today().strftime("%Y-%m-%d %H:%M")
            st.session_state.saved_diaries[today] = diary
            save_diaries(st.session_state.saved_diaries)

            st.success("✅ 日記が生成され、保存されました！")

# 結果表示
if st.session_state.diary:
    st.subheader("📘 あなたの日記：")
    edited_diary = st.text_area("日記の内容を編集できます：", value=st.session_state.diary, height=200)
    st.session_state.diary = edited_diary

    if st.download_button("💾 日記を保存する（テキストファイル）", st.session_state.diary, file_name="my_diary.txt"):
        st.success("✅ 保存しました！")

# 過去日記の表示
st.subheader("📚 過去の日記を見る")
if st.session_state.saved_diaries:
    selected_date = st.selectbox("日付を選択してください", list(st.session_state.saved_diaries.keys())[::-1])
    st.text_area("選択した日記：", value=st.session_state.saved_diaries[selected_date], height=200)
else:
    st.info("まだ保存された日記がありません。")

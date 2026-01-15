import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 設定頁面資訊 ---
st.set_page_config(page_title="My TOEIC Master", layout="wide", page_icon="📝")

# --- 連接 Google Sheets ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # 讀取 Sheet1，ttl=0 代表不快取，每次抓最新
        df = conn.read(worksheet="Sheet1", ttl=0)
        # 如果欄位少於2個，代表是空表，回傳預設結構
        if df.empty or len(df.columns) < 2:
            return pd.DataFrame(columns=[
                "Date", "Category", "Sub_Type", "Question", "Answer", 
                "Explanation", "Error_Count", "Last_Review"
            ])
        # 處理數字欄位，避免錯誤
        df['Error_Count'] = pd.to_numeric(df['Error_Count'], errors='coerce').fillna(1).astype(int)
        # 處理日期欄位為字串，避免格式問題
        df['Date'] = df['Date'].astype(str)
        return df
    except Exception:
        return pd.DataFrame(columns=[
            "Date", "Category", "Sub_Type", "Question", "Answer", 
            "Explanation", "Error_Count", "Last_Review"
        ])

def save_data(df):
    conn.update(worksheet="Sheet1", data=df)
    st.cache_data.clear()

# 載入資料
df = load_data()

# --- 側邊欄 ---
st.sidebar.title("🚀 TOEIC 雲端學習")
page = st.sidebar.radio("功能選單", ["📊 學習儀表板", "✍️ 新增錯題", "📖 錯題複習庫", "🎲 隨機抽考"])

# --- 1. 儀表板 ---
if page == "📊 學習儀表板":
    st.title("📊 學習戰情室")
    if df.empty:
        st.info("目前無資料，請先新增錯題！")
    else:
        col1, col2 = st.columns(2)
        col1.metric("累積錯題數", len(df))
        today = datetime.now().strftime("%Y-%m-%d")
        col2.metric("今日新增", len(df[df['Date'] == today]))
        
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("能力分析")
            if not df.empty:
                counts = df['Category'].value_counts().reset_index()
                counts.columns = ['theta', 'r']
                fig = px.line_polar(counts, r='r', theta='theta', line_close=True)
                fig.update_traces(fill='toself')
                st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.subheader("常錯重點")
            top = df.sort_values(by='Error_Count', ascending=False).head(3)
            for _, row in top.iterrows():
                st.error(f"[{row['Category']}] {row['Question']} (錯 {row['Error_Count']} 次)")

# --- 2. 新增錯題 ---
elif page == "✍️ 新增錯題":
    st.title("✍️ 新增錯題")
    with st.form("add_form"):
        c1, c2 = st.columns(2)
        cat = c1.selectbox("分類", ["聽力", "閱讀", "單字", "文法"])
        sub = c2.text_input("子標籤", placeholder="ex: Part 5")
        q = st.text_area("題目")
        a = st.text_input("答案")
        exp = st.text_area("解析")
        if st.form_submit_button("儲存"):
            new = pd.DataFrame([{
                "Date": datetime.now().strftime("%Y-%m-%d"),
                "Category": cat, "Sub_Type": sub, "Question": q,
                "Answer": a, "Explanation": exp, "Error_Count": 1,
                "Last_Review": datetime.now().strftime("%Y-%m-%d")
            }])
            save_data(pd.concat([df, new], ignore_index=True))
            st.success("已儲存！")
            st.rerun()

# --- 3. 複習庫 ---
elif page == "📖 錯題複習庫":
    st.title("📖 錯題列表")
    st.dataframe(df, use_container_width=True)
    idx = st.number_input("輸入刪除編號(Index)", min_value=0, step=1)
    if st.button("刪除"):
        if 0 <= idx < len(df):
            save_data(df.drop(idx).reset_index(drop=True))
            st.warning("已刪除")
            st.rerun()

# --- 4. 抽考 ---
elif page == "🎲 隨機抽考":
    st.title("🎲 隨機抽考")
    if df.empty: st.warning("沒題目！")
    else:
        if 'q' not in st.session_state:
            st.session_state.q = df.sample(1).iloc[0]
            st.session_state.q_idx = df.index[df['Question'] == st.session_state.q['Question']][0]
        
        q = st.session_state.q
        st.info(f"[{q['Category']}] {q['Question']}")
        if st.button("看答案"):
            st.success(q['Answer'])
            st.write(q['Explanation'])
            c1, c2 = st.columns(2)
            if c1.button("✅ 答對"):
                del st.session_state.q
                st.rerun()
            if c2.button("❌ 答錯"):
                df.at[st.session_state.q_idx, 'Error_Count'] += 1
                save_data(df)
                del st.session_state.q
                st.rerun()
        if st.button("下一題"):
            del st.session_state.q
            st.rerun()

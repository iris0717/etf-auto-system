import streamlit as st
import pandas as pd

st.set_page_config(page_title="ETF 自动系统", layout="centered")

st.title("📊 ETF 自动判断系统（稳定版）")

# === 模拟数据（保证不报错）===
data = {
    "close": [1.00, 1.02, 1.01, 1.03, 1.05, 1.06, 1.07,
              1.06, 1.08, 1.10, 1.12, 1.11, 1.13,
              1.15, 1.14, 1.16, 1.18, 1.17, 1.19, 1.20]
}

df = pd.DataFrame(data)

df["ma20"] = df["close"].rolling(20).mean()

st.success("🟢 系统运行正常（测试数据）")

st.write("最新收盘价：", df["close"].iloc[-1])
st.write("20 日均线：", round(df["ma20"].iloc[-1], 3))

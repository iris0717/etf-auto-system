import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="ETF 自动判断系统", layout="centered")

st.title("📊 ETF 自动判断系统（真实数据版）")

# === ETF 对应关系（A股 ETF → Yahoo 代码）===
ETF_MAP = {
    "半导体设备 ETF（159516）": "159516.SZ",
    "证券 ETF（512000）": "512000.SS",
    "机器人 ETF（159770）": "159770.SZ",
}

def load_data(code):
    try:
        df = yf.download(code, period="3mo", interval="1d", progress=False)
        if df.empty:
            return None
        df = df.reset_index()
        df.rename(columns={"Close": "close"}, inplace=True)
        return df
    except Exception:
        return None

for name, code in ETF_MAP.items():
    st.subheader(name)
    df = load_data(code)

    if df is None or "close" not in df.columns:
        st.warning("⚠️ 数据获取失败，暂无法判断")
        continue

    df["ma20"] = df["close"].rolling(20).mean()

    latest = df.iloc[-1]
    price = float(latest["close"])
    ma20 = float(latest["ma20"])

    if pd.isna(ma20):
        st.warning("⚠️ 数据不足 20 天")
        continue

    if price > ma20:
        st.success(f"🟢 符合条件｜现价 {price:.2f} ＞ MA20 {ma20:.2f}")
        st.info("建议试仓：30% ｜ 止损 -4% ｜ 目标 +6% / +10%")
    else:
        st.warning(f"🔴 不符合条件｜现价 {price:.2f} ＜ MA20 {ma20:.2f}")

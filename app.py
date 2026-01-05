import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="ETF 自动交易系统", layout="centered")

st.title("📊 ETF 自动交易系统（Yahoo 版）")

# ======================
# 工具函数
# ======================
def load_data(code, period="3mo"):
    df = yf.download(code, period=period, interval="1d", progress=False)
    if df.empty:
        return None
    df = df.reset_index()
    df.rename(columns={"Close": "close"}, inplace=True)
    return df

def calc_ma20(df):
    df["ma20"] = df["close"].rolling(20).mean()
    return df

# ======================
# 大盘环境判断
# ======================
st.header("📈 大盘环境")

index_df = load_data("510300.SS")
if index_df is None:
    st.error("❌ 大盘数据获取失败")
    st.stop()

index_df = calc_ma20(index_df)

idx_latest = index_df.iloc[-1]
idx_prev = index_df.iloc[-2]

market_ok = (
    idx_latest["close"] > idx_latest["ma20"]
    and idx_latest["ma20"] >= idx_prev["ma20"]
)

if market_ok:
    st.success("🟢 大盘环境：允许建仓")
else:
    st.error("🔴 大盘环境：禁止建仓")

# ======================
# ETF 列表（Yahoo 可用）
# ======================
st.header("🔥 ETF 建仓判断")

ETF_LIST = {
    "沪深300 ETF（510300）": "510300.SS",
    "上证50 ETF（510050）": "510050.SS",
    "创业板 ETF（159915）": "159915.SZ",
}

for name, code in ETF_LIST.items():
    st.subheader(name)
    df = load_data(code)

    if df is None:
        st.warning("⚠️ 数据获取失败")
        continue

    df = calc_ma20(df)
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    price = float(latest["close"])
    ma20 = float(latest["ma20"])
    ma20_prev = float(prev["ma20"])

    if pd.isna(ma20):
        st.warning("⚠️ 数据不足")
        continue

    etf_ok = (
        market_ok
        and price > ma20
        and ma20 >= ma20_prev
    )

    if etf_ok:
        st.success("✅ 可建仓")
        st.info("建议仓位：30% ｜ 止损 -4% 或跌破 MA20 ｜ 目标 +6% / +10%")
    else:
        st.warning("❌ 不符合建仓条件")

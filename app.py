import streamlit as st
import akshare as ak
import pandas as pd

st.set_page_config(page_title="ETF 自动交易系统", layout="centered")

st.title("ETF 自动短线系统")

# ================= 大盘环境 =================
index = ak.stock_zh_index_daily(symbol="sh000300")
index = index.tail(60)

index["ma20"] = index["close"].rolling(20).mean()
close = index.iloc[-1]["close"]
ma20 = index.iloc[-1]["ma20"]
ma20_prev = index.iloc[-2]["ma20"]

if close > ma20 and ma20 > ma20_prev:
    env = "🟢 可进攻"
    max_pos = "50%"
elif close > ma20:
    env = "🟡 中性"
    max_pos = "30%"
else:
    env = "🔴 风险"
    max_pos = "0%"

st.subheader("📊 今日大盘环境")
st.write(f"**{env}** ｜ 单只 ETF 最大仓位：{max_pos}")

# ================= ETF 推荐 =================
st.subheader("🔥 今日最优 ETF（自动）")

etfs = {
    "159516": "半导体设备 ETF",
    "512000": "证券 ETF",
    "159770": "机器人 ETF",
}

for code, name in etfs.items():
    df = ak.fund_etf_hist_em(symbol=code)
    df = df.tail(60)
    df["ma20"] = df["close"].rolling(20).mean()

    score = 0
    if df.iloc[-1]["close"] > df.iloc[-1]["ma20"]:
        score += 1
    if df.iloc[-1]["ma20"] > df.iloc[-2]["ma20"]:
        score += 1

    st.write(f"**{name}（{code}）** ｜ 评分：{score}")
    if score >= 2 and env != "🔴 风险":
        st.success("可试仓：30% ｜ 止损 -4% ｜ 目标 +6% / +10%")
    else:
        st.warning("观望")

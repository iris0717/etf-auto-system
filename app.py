import streamlit as st
import akshare as ak
import pandas as pd

st.set_page_config(page_title="ETF自动交易系统", layout="centered")

st.title("ETF 自动短线系统")

# ========= 大盘环境 =========
index = ak.stock_zh_index_daily(symbol="sh000300")
index = index.tail(60)

index["ma20"] = index["close"].rolling(20).mean()
index_close = index.iloc[-1]["close"]
index_ma20 = index.iloc[-1]["ma20"]
ma20_prev = index.iloc[-2]["ma20"]

if index_close > index_ma20 and index_ma20 > ma20_prev:
    market_env = "GOOD"
    env_text = "🟢 可进攻"
    max_pos = "50%"
elif index_close > index_ma20:
    market_env = "NEUTRAL"
    env_text = "🟡 中性"
    max_pos = "30%"
else:
    market_env = "RISK"
    env_text = "🔴 风险"
    max_pos = "0%"

st.subheader("📊 今日大盘环境")
st.write(f"**{env_text}** ｜ 单只ETF最大仓位：{max_pos}")

# ========= ETF 推荐 =========
st.subheader("🔥 今日最优板块 ETF")

etfs = {
    "159516": "半导体设备 ETF",
    "512000": "证券 ETF",
    "159770": "机器人 ETF",
}

results = []

for code, name in etfs.items():
    df = ak.fund_etf_hist_em(symbol=code)
    df = df.tail(60)

    df["ma20"] = df["close"].rolling(20).mean()
    close = df.iloc[-1]["close"]
    ma20 = df.iloc[-1]["ma20"]

    score = 0
    if close > ma20:
        score += 1
    if ma20 > df.iloc[-2]["ma20"]:
        score += 1

    results.append((name, code, score))

results = sorted(results, key=lambda x: x[2], reverse=True)

for i, r in enumerate(results, 1):
    st.write(f"{i}️⃣ **{r[0]}（{r[1]}）** ｜ 评分：{r[2]}")
    if r[2] >= 2 and market_env != "RISK":
        st.success("可试仓：30%｜止损 -4%｜目标 +6% / +10%")
    else:
        st.warning("观望")

import streamlit as st
import tushare as ts
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ===============================
# 基础配置
# ===============================
st.set_page_config(page_title="ETF 板块短线系统", layout="centered")

# TuShare 初始化
ts.set_token(st.secrets["TUSHARE_TOKEN"])
pro = ts.pro_api()

# ===============================
# 工具函数
# ===============================
def calc_macd(df):
    exp1 = df["close"].ewm(span=12, adjust=False).mean()
    exp2 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = exp1 - exp2
    df["signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    return df

def calc_kdj(df, n=9):
    low_n = df["low"].rolling(n).min()
    high_n = df["high"].rolling(n).max()
    rsv = (df["close"] - low_n) / (high_n - low_n) * 100
    df["K"] = rsv.ewm(com=2).mean()
    df["D"] = df["K"].ewm(com=2).mean()
    df["J"] = 3 * df["K"] - 2 * df["D"]
    return df

def get_etf_daily(ts_code):
    df = pro.fund_daily(
        ts_code=ts_code,
        start_date=(datetime.now() - timedelta(days=120)).strftime("%Y%m%d")
    )
    if df is None or len(df) < 30:
        return None

    df = df.sort_values("trade_date")
    df["ma20"] = df["close"].rolling(20).mean()
    df["vol_ma5"] = df["vol"].rolling(5).mean()
    df = calc_macd(df)
    df = calc_kdj(df)
    return df

def signal_judge(df):
    l = df.iloc[-1]

    cond_price = l["close"] > l["ma20"]
    cond_macd = l["macd"] > l["signal"]
    cond_kdj = l["K"] > l["D"] and l["K"] < 80
    cond_vol = l["vol"] > l["vol_ma5"]

    score = sum([cond_price, cond_macd, cond_kdj, cond_vol])

    if score >= 3:
        return "🟢 买入"
    elif score == 2:
        return "🟡 等待"
    else:
        return "🔴 观望"

# ===============================
# 大盘过滤（上证指数）
# ===============================
def market_ok():
    idx = pro.index_daily(
        ts_code="000001.SH",
        start_date=(datetime.now() - timedelta(days=120)).strftime("%Y%m%d")
    )
    idx = idx.sort_values("trade_date")
    idx["ma20"] = idx["close"].rolling(20).mean()

    l = idx.iloc[-1]
    return l["close"] > l["ma20"]

# ===============================
# ETF 池（你现在用的）
# ===============================
ETF_POOL = {
    "159218": "光伏ETF",
    "512660": "军工ETF",
    "515880": "科技ETF",
    "159732": "新能源车ETF",
    "159516": "芯片ETF",
    "562500": "计算机ETF"
}

# ===============================
# 页面展示
# ===============================
st.title("📊 A股板块 ETF 短线系统（收盘版）")

market_status = market_ok()
st.subheader("📈 大盘环境")
st.write("🟢 允许交易" if market_status else "🔴 大盘偏弱，谨慎开仓")

results = []

for code, name in ETF_POOL.items():
    df = get_etf_daily(code)
    if df is None:
        continue

    sig = signal_judge(df)
    l = df.iloc[-1]

    strength = (
        (l["close"] / l["ma20"] - 1) * 100
        + (l["macd"] - l["signal"]) * 10
    )

    results.append({
        "ETF": name,
        "代码": code,
        "信号": sig,
        "强度": round(strength, 2)
    })

df_res = pd.DataFrame(results)

if not df_res.empty:
    df_res = df_res.sort_values("强度", ascending=False)

    st.subheader("🔥 当前板块强度排序")
    st.dataframe(df_res, use_container_width=True)

    st.subheader("🎯 今日执行建议")
    if market_status:
        top = df_res.iloc[0]
        st.success(
            f"优先关注：{top['ETF']}（{top['代码']}）\n"
            f"信号：{top['信号']}｜建议仓位：30%~40%"
        )
    else:
        st.warning("大盘不支持开新仓，仅观察")

else:
    st.warning("暂无有效数据")

st.write("Token loaded:", "TUSHARE_TOKEN" in st.secrets)
import streamlit as st
import pandas as pd
import numpy as np
import tushare as ts
from datetime import datetime, time

# ======================
# TuShare 初始化（f4671fb19df2327e5d5348cd1bf83dfa5a5b5e50a9be775fd9c3411c）
# ======================
ts.set_token(st.secrets["TUSHARE_TOKEN"])
pro = ts.pro_api()

# ======================
# 15 分钟自动刷新（官方方式）
# ======================
st.markdown("<meta http-equiv='refresh' content='900'>", unsafe_allow_html=True)

# ======================
# 时间判断（14:45 收盘确认）
# ======================
now = datetime.now().time()
is_close_mode = now >= time(14, 45)

# ======================
# 页面设置
# ======================
st.set_page_config(page_title="板块ETF短线系统（封版）", layout="centered")
st.title("📊 A股板块 ETF 短线系统（TuShare 封版）")

if is_close_mode:
    st.warning("🕒 14:45 收盘确认模式（信号可执行）")
else:
    st.info("ℹ️ 盘中观察模式（不执行）")

# ======================
# TuShare 数据函数
# ======================
def load_data(ts_code, start_date="20240101"):
    try:
        df = pro.fund_daily(ts_code=ts_code, start_date=start_date)
        if df is None or df.empty:
            return None
        df = df.sort_values("trade_date")
        df.rename(columns={"vol": "Volume"}, inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df
    except:
        return None

# ======================
# 技术指标
# ======================
def add_indicators(df):
    df["ma20"] = df["close"].rolling(20).mean()
    df["ema12"] = df["close"].ewm(span=12, adjust=False).mean()
    df["ema26"] = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = df["ema12"] - df["ema26"]
    df["signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["vol_ma5"] = df["Volume"].rolling(5).mean()
    df["ma20_slope"] = df["ma20"] - df["ma20"].shift(5)

    low_n = df["close"].rolling(9).min()
    high_n = df["close"].rolling(9).max()
    rsv = (df["close"] - low_n) / (high_n - low_n) * 100
    df["kdj_k"] = rsv.ewm(com=2).mean()
    return df

# ======================
# 大盘过滤器
# ======================
def load_market():
    for name, code in [
        ("沪深300", "000300.SH"),
        ("上证指数", "000001.SH")
    ]:
        df = load_data(code)
        if df is not None and len(df) >= 30:
            return name, add_indicators(df)
    return None, None

market_name, market_df = load_market()

if market_df is None:
    st.error("❌ 大盘数据获取失败，今日停止交易")
    st.stop()

m = market_df.iloc[-1]
m5 = market_df.iloc[-6]

market_ok = bool(
    float(m["close"]) > float(m["ma20"])
    and float(m["ma20"]) >= float(m5["ma20"])
)

market_20d_return = float(
    (market_df["close"].iloc[-1] / market_df["close"].iloc[-21] - 1) * 100
)

st.subheader("📈 大盘环境")
st.success("🟢 允许交易" if market_ok else "🔴 禁止新开仓")

# ======================
# ETF 池（你确认过的）
# ======================
ETF_POOL = {
    "军工": "512660.SH",
    "半导体": "159995.SZ",
    "计算机": "159998.SZ",
    "人工智能": "159819.SZ",
    "新能源": "159806.SZ",
    "医药": "512010.SH",
    "科创成长": "159218.SZ",
    "机器人": "562500.SH",
    "主题A": "159732.SZ",
    "主题B": "515880.SH",
}

results = []

# ======================
# 主策略逻辑
# ======================
for name, code in ETF_POOL.items():
    df = load_data(code)
    if df is None or len(df) < 30:
        continue

    df = add_indicators(df)
    l, p, p20 = df.iloc[-1], df.iloc[-2], df.iloc[-21]

    try:
        price = float(l["close"])
        ma20 = float(l["ma20"])
        slope = float(l["ma20_slope"])
        ret20 = float((price / float(p20["close"]) - 1) * 100)
    except:
        continue

    if np.isnan(ma20) or np.isnan(slope):
        continue

    strength = ret20 - market_20d_return + slope

    macd_ok = float(l["macd"]) > float(l["signal"])
    macd_keep = float(p["macd"]) > float(p["signal"])
    vol_up = float(l["Volume"]) > float(l["vol_ma5"])
    k_safe = float(l["kdj_k"]) <= 85

    allow_buy = (
        market_ok
        and price > ma20
        and macd_ok
        and macd_keep
        and vol_up
        and k_safe
    )

    if is_close_mode and allow_buy:
        action = "🟢 买入"
    elif not market_ok:
        action = "🔴 空仓 / 卖出"
    else:
        action = "🟡 等待"

    results.append({
        "板块": name,
        "ETF代码": code,
        "强度": round(strength, 2),
        "操作": action
    })

# ======================
# 结果展示
# ======================
df_res = pd.DataFrame(results)

if df_res.empty:
    st.warning("⚠️ 今日无符合条件的板块")
    st.stop()

df_res["强度"] = pd.to_numeric(df_res["强度"], errors="coerce")
df_res = df_res.dropna().sort_values("强度", ascending=False)

st.subheader("🔥 今日最强 Top 3 板块 ETF")
st.dataframe(df_res.head(3), use_container_width=True)

st.subheader("📋 全部板块信号")
st.dataframe(df_res, use_container_width=True)

st.subheader("📌 执行纪律")
st.markdown("""
- 仅 14:45 后执行  
- Top3 以内优先  
- 大盘不允许 → 全部放弃  
- 连续 30 天不改规则
""")

import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, time

# ======================
# 15 分钟自动刷新（官方方式）
# ======================
st.markdown(
    """
    <meta http-equiv="refresh" content="900">
    """,
    unsafe_allow_html=True
)

# ======================
# 时间判断（14:45 收盘模式）
# ======================
now = datetime.now().time()
is_close_mode = now >= time(14, 45)

# ======================
# 页面设置
# ======================
st.set_page_config(
    page_title="板块ETF短线系统（终极版）",
    layout="centered"
)

st.title("📊 板块 ETF 短线交易系统（终极版）")

if is_close_mode:
    st.warning("🕒 当前为 **14:45 收盘确认模式**（信号可执行）")
else:
    st.info("ℹ️ 当前为盘中观察模式（仅供参考，不建议下单）")

# ======================
# 数据获取
# ======================
def load_data(code, period="3mo"):
    try:
        df = yf.download(
            code,
            period=period,
            interval="1d",
            progress=False
        )
        if df is None or df.empty:
            return None

        df = df.reset_index()

        if "Close" in df.columns:
            df.rename(columns={"Close": "close"}, inplace=True)

        if "close" not in df.columns:
            return None

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
        ("沪深300", "000300.SS"),
        ("上证指数", "000001.SS")
    ]:
        df = load_data(code)
        if df is not None and len(df) >= 30:
            return name, add_indicators(df)
    return None, None

market_name, market_df = load_market()

if market_df is None:
    st.error("❌ 大盘数据获取失败，今日不交易")
    st.stop()

m = market_df.iloc[-1]
m5 = market_df.iloc[-6]

market_ok = (
    float(m["close"]) > float(m["ma20"])
    and float(m["ma20"]) >= float(m5["ma20"])
)

market_20d_return = (
    market_df["close"].iloc[-1]
    / market_df["close"].iloc[-21]
    - 1
) * 100

st.subheader("📈 大盘状态")
if market_ok:
    st.success(f"🟢 {market_name}：允许交易")
else:
    st.error(f"🔴 {market_name}：禁止新开仓")

# ======================
# ETF 池（含你新增的）
# ======================
ETF_POOL = {
    "军工": "512660.SS",
    "半导体": "159995.SZ",
    "计算机": "159998.SZ",
    "人工智能": "159819.SZ",
    "新能源": "159806.SZ",
    "医药": "512010.SS",
    "科创成长": "159218.SZ",
    "机器人": "562500.SS",
    "主题ETF-A": "159732.SZ",
    "主题ETF-B": "515880.SS",
}

results = []

# ======================
# 主逻辑
# ======================
for name, code in ETF_POOL.items():
    df = load_data(code)

    if df is None or len(df) < 30:
        continue

    df = add_indicators(df)

    l = df.iloc[-1]
    p = df.iloc[-2]
    p20 = df.iloc[-21]

    price = float(l["close"])
    ma20 = float(l["ma20"])

    etf_20d_return = (price / float(p20["close"]) - 1) * 100

    strength = (
        etf_20d_return
        - market_20d_return
        + float(l["ma20_slope"])
    )

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
        action = "🔴 卖出 / 空仓"
    else:
        action = "🟡 等待"

    results.append({
        "ETF": name,
        "代码": code.replace(".SS", "").replace(".SZ", ""),
        "强度": round(strength, 2),
        "操作": action
    })

# ======================
# 结果展示
# ======================
df_res = pd.DataFrame(results)
df_res = df_res.sort_values("强度", ascending=False)

st.subheader("🔥 Top 3 强度板块 ETF")
st.dataframe(df_res.head(3), use_container_width=True)

st.subheader("📋 全部 ETF 信号")
st.dataframe(df_res, use_container_width=True)

# ======================
# 实盘统计页（结构已预留）
# ======================
st.subheader("📊 实盘胜率统计（封版结构）")
st.info(
    "规则：14:45 买入 → 下一次出现『卖出 / 空仓』信号视为一笔交易\n\n"
    "👉 后续可自动统计胜率、平均收益"
)

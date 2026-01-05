import streamlit as st
import pandas as pd
import yfinance as yf

# ======================
# 页面设置（必须最前）
# ======================
st.set_page_config(
    page_title="ETF 自动交易系统（自动版）",
    layout="centered"
)

st.title("📊 ETF 自动交易系统（自动版）")

# ======================
# 数据获取（统一兜底）
# ======================
def load_data(code, period="3mo"):
    try:
        df = yf.download(code, period=period, interval="1d", progress=False)
        if df is None or df.empty:
            return None

        df = df.reset_index()

        # 统一收盘价字段
        if "Close" in df.columns:
            df.rename(columns={"Close": "close"}, inplace=True)
        elif "close" not in df.columns:
            return None

        return df
    except Exception:
        return None


# ======================
# 技术指标（全部算好）
# ======================
def add_indicators(df):
    df["ma20"] = df["close"].rolling(20).mean()

    # MACD
    df["ema12"] = df["close"].ewm(span=12, adjust=False).mean()
    df["ema26"] = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = df["ema12"] - df["ema26"]
    df["signal"] = df["macd"].ewm(span=9, adjust=False).mean()

    # KDJ（简化版）
    low_n = df["close"].rolling(9).min()
    high_n = df["close"].rolling(9).max()
    rsv = (df["close"] - low_n) / (high_n - low_n) * 100
    df["kdj_k"] = rsv.ewm(com=2).mean()
    df["kdj_d"] = df["kdj_k"].ewm(com=2).mean()

    return df


# ======================
# 大盘指数自动兜底
# ======================
def load_market():
    candidates = [
        ("沪深300指数", "000300.SS"),
        ("上证指数", "000001.SS"),
        ("恒生指数", "^HSI"),
    ]

    for name, code in candidates:
        df = load_data(code)
        if df is not None and len(df) >= 25:
            df = add_indicators(df)
            return name, df

    return None, None


# ======================
# 大盘环境判断
# ======================
st.subheader("📈 大盘环境")

market_name, market_df = load_market()

if market_df is None:
    st.error("❌ 大盘数据不可用（Yahoo 当前异常）")
    st.stop()

m = market_df.iloc[-1]
m_prev = market_df.iloc[-2]

m_close = float(m["close"])
m_ma20 = float(m["ma20"])
m_ma20_prev = float(m_prev["ma20"])

market_ok = (
    m_close > m_ma20
    and m_ma20 >= m_ma20_prev
)

if market_ok:
    st.success(f"🟢 允许建仓（参考：{market_name}）")
else:
    st.error(f"🔴 禁止建仓（参考：{market_name}）")


# ======================
# ETF 池（Yahoo 可用）
# ======================
ETF_LIST = {
    "创业板 ETF": "159915.SZ",
    "沪深300 ETF": "510300.SS",
    "上证50 ETF": "510050.SS",
}

results = []

for name, code in ETF_LIST.items():
    df = load_data(code)
    if df is None or len(df) < 25:
        continue

    df = add_indicators(df)

    l = df.iloc[-1]
    p = df.iloc[-2]

    price = float(l["close"])
    ma20 = float(l["ma20"])
    ma20_prev = float(p["ma20"])

    # 主规则
    base_ok = (
        market_ok
        and price > ma20
        and ma20 >= ma20_prev
    )

    if not base_ok:
        continue

    # === 指标值全部转 float（防炸） ===
    macd = float(l["macd"])
    signal = float(l["signal"])
    kdj_k = float(l["kdj_k"])

    # === 打分（用于排序） ===
    score = (price / ma20 - 1) * 100

    if macd > signal:
        score += 1

    if kdj_k < 80:
        score += 1

    # === 仓位控制（MACD / KDJ 只做降级） ===
    position = 0.3
    note = "正常"

    if kdj_k > 85:
        position = 0.2
        note = "过热降仓"

    if kdj_k > 90:
        position = 0.0
        note = "极端过热，禁仓"

    results.append({
        "name": name,
        "score": score,
        "position": position,
        "note": note
    })


# ======================
# Top3 + 手机 1 屏输出
# ======================
st.subheader("🔥 今日 Top ETF（自动排序）")

if not results:
    st.warning("暂无符合条件的 ETF")
else:
    results = sorted(results, key=lambda x: x["score"], reverse=True)[:3]

    for i, r in enumerate(results, 1):
        st.markdown(f"""
**🥇 第 {i} 名：{r['name']}**  
- 建议仓位：{int(r['position'] * 100)}%  
- 状态：{r['note']}  
- 止损：-4% 或跌破 MA20  
- 止盈：+6% / +10%  
""")

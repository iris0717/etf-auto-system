import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="ETF 自动交易系统", layout="centered")
st.title("📊 ETF 自动交易系统（自动版）")

# ========= 基础工具 =========
def load_data(code, period="3mo"):
    try:
        df = yf.download(code, period=period, interval="1d", progress=False)
        if df is None or df.empty:
            return None
        df = df.reset_index()
        if "Close" in df.columns:
            df.rename(columns={"Close": "close"}, inplace=True)
        return df
    except:
        return None

def add_indicators(df):
    df["ma20"] = df["close"].rolling(20).mean()
    df["ema12"] = df["close"].ewm(span=12).mean()
    df["ema26"] = df["close"].ewm(span=26).mean()
    df["macd"] = df["ema12"] - df["ema26"]
    df["signal"] = df["macd"].ewm(span=9).mean()

    low_n = df["close"].rolling(9).min()
    high_n = df["close"].rolling(9).max()
    rsv = (df["close"] - low_n) / (high_n - low_n) * 100
    df["kdj_k"] = rsv.ewm(com=2).mean()
    df["kdj_d"] = df["kdj_k"].ewm(com=2).mean()
    return df

# ========= 大盘自动兜底 =========
def load_market():
    candidates = [
        ("沪深300", "000300.SS"),
        ("上证指数", "000001.SS"),
        ("恒生指数", "^HSI"),
    ]
    for name, code in candidates:
        df = load_data(code)
        if df is not None and len(df) >= 25:
            df = add_indicators(df)
            return name, df
    return None, None

# ========= 大盘判断 =========
st.subheader("📈 大盘环境")
market_name, market_df = load_market()

if market_df is None:
    st.error("❌ 大盘不可用")
    st.stop()

m = market_df.iloc[-1]
m_prev = market_df.iloc[-2]

market_ok = (
    float(m["close"]) > float(m["ma20"])
    and float(m["ma20"]) >= float(m_prev["ma20"])
)

if market_ok:
    st.success(f"🟢 允许建仓（参考：{market_name}）")
else:
    st.error(f"🔴 禁止建仓（参考：{market_name}）")

# ========= ETF 池 =========
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

    base_ok = market_ok and price > ma20 and ma20 >= ma20_prev
    if not base_ok:
        continue

    score = (price / ma20 - 1) * 100
    if l["macd"] > l["signal"]:
        score += 1
    if l["kdj_k"] < 80:
        score += 1

    # 仓位判断
    position = 0.3
    note = "正常"

    if l["kdj_k"] > 85:
        position = 0.2
        note = "过热降仓"
    if l["kdj_k"] > 90:
        position = 0
        note = "极端过热，禁仓"

    results.append({
        "name": name,
        "score": score,
        "position": position,
        "note": note
    })

# ========= Top3 + 手机 1 屏 =========
st.subheader("🔥 今日 Top ETF")

if not results:
    st.warning("暂无符合条件的 ETF")
else:
    results = sorted(results, key=lambda x: x["score"], reverse=True)[:3]

    for i, r in enumerate(results, 1):
        st.markdown(f"""
**🥇 第 {i} 名：{r['name']}**  
仓位：{int(r['position']*100)}%  
状态：{r['note']}  
止损：-4% / 跌破 MA20  
止盈：+6% / +10%  
""")

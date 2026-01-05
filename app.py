import streamlit as st
import pandas as pd
import yfinance as yf

# ======================
# 页面
# ======================
st.set_page_config(page_title="板块ETF短线系统（封版）", layout="centered")
st.title("📊 板块 ETF 短线交易系统（收盘版 · 封版）")

# ======================
# 数据获取
# ======================
def load_data(code, period="3mo"):
    try:
        df = yf.download(code, period=period, interval="1d", progress=False)
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

    # MACD
    df["ema12"] = df["close"].ewm(span=12, adjust=False).mean()
    df["ema26"] = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = df["ema12"] - df["ema26"]
    df["signal"] = df["macd"].ewm(span=9, adjust=False).mean()

    # 成交量
    df["vol_ma5"] = df["Volume"].rolling(5).mean()

    # KDJ（只用 K）
    low_n = df["close"].rolling(9).min()
    high_n = df["close"].rolling(9).max()
    rsv = (df["close"] - low_n) / (high_n - low_n) * 100
    df["kdj_k"] = rsv.ewm(com=2).mean()

    return df


# ======================
# 大盘（最高优先级）
# ======================
def load_market():
    for name, code in [
        ("沪深300", "000300.SS"),
        ("上证指数", "000001.SS"),
    ]:
        df = load_data(code)
        if df is not None and len(df) >= 30:
            return name, add_indicators(df)
    return None, None


st.subheader("📈 今日市场结论")
market_name, market_df = load_market()

if market_df is None:
    st.error("❌ 大盘数据不可用")
    st.stop()

m = market_df.iloc[-1]
m5 = market_df.iloc[-6]

market_ok = (
    float(m["close"]) > float(m["ma20"])
    and float(m["ma20"]) >= float(m5["ma20"])
)

if market_ok:
    st.success(f"🟢 大盘允许交易（{market_name}）")
else:
    st.error(f"🔴 大盘转弱，禁止新开仓（{market_name}）")

market_20d_return = (
    market_df["close"].iloc[-1] / market_df["close"].iloc[-21] - 1
) * 100


# ======================
# 板块 ETF 池（最终封版）
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
}

signals = []

for name, code in ETF_POOL.items():
    df = load_data(code)
    if df is None or len(df) < 30:
        continue

    df = add_indicators(df)

    l = df.iloc[-1]
    p = df.iloc[-2]
    p2 = df.iloc[-3]
    p20 = df.iloc[-21]

    price = float(l["close"])
    ma20 = float(l["ma20"])

    # ========= 板块强弱 =========
    etf_20d_return = (price / float(p20["close"]) - 1) * 100
    strong_block = price > ma20 and etf_20d_return > market_20d_return

    # ========= 短线行为 =========
    macd_ok = float(l["macd"]) > float(l["signal"])
    macd_dead = float(l["macd"]) < float(l["signal"]) and float(p["macd"]) >= float(p["signal"])

    vol_up = float(l["Volume"]) > float(l["vol_ma5"])
    price_up = price > float(p["close"])
    vol_down_break = price < float(p["close"]) and vol_up

    k = float(l["kdj_k"])
    k_overheat = k > 85
    k_dead = k > 80 and k < float(p["kdj_k"])

    # ========= 当日买入条件 =========
    today_buy = (
        market_ok
        and strong_block
        and macd_ok
        and not k_overheat
        and price_up
        and vol_up
    )

    # ========= 连续 2 天确认 =========
    yesterday_buy = (
        float(p["macd"]) > float(p["signal"])
        and float(p["close"]) > float(p["ma20"])
        and float(p["kdj_k"]) <= 85
    )

    allow_buy = today_buy and yesterday_buy

    # ========= 最终行为 =========
    if not market_ok:
        action = "🔴 卖出" if (price < ma20 or macd_dead) else "🟡 等待"
    else:
        if macd_dead or vol_down_break or price < ma20 or k_dead:
            action = "🔴 卖出"
        elif allow_buy:
            action = "🟢 买入"
        else:
            action = "🟡 等待"

    signals.append({
        "name": name,
        "action": action
    })


# ======================
# 最终输出
# ======================
st.subheader("🧠 今日执行结论")

buy_list = [s["name"] for s in signals if s["action"] == "🟢 买入"]
sell_list = [s["name"] for s in signals if s["action"] == "🔴 卖出"]

if not market_ok:
    st.markdown("### 🔴 今日策略：**空仓 / 只处理卖出**")
elif buy_list:
    st.markdown(f"### 🟢 今日策略：**允许买入 → {', '.join(buy_list)}**")
else:
    st.markdown("### 🟡 今日策略：**等待，不新开仓**")

st.markdown("---")
st.subheader("📋 板块 ETF 执行清单")

for s in signals:
    st.markdown(f"""
**{s['name']}**  
操作：**{s['action']}**  
仓位：{'20–30%' if s['action']=='🟢 买入' else '0%'}  
止损：-4% 或 跌破 MA20  
""")

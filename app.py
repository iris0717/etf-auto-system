import streamlit as st
import pandas as pd
import yfinance as yf

# ======================
# 页面设置（必须最前）
# ======================
st.set_page_config(
    page_title="ETF 自动交易系统（Yahoo 版）",
    layout="centered"
)

st.title("📊 ETF 自动交易系统（Yahoo 版）")

# ======================
# 通用数据获取（兜底）
# ======================
def load_data(code, period="3mo"):
    try:
        df = yf.download(code, period=period, interval="1d", progress=False)
        if df is None or df.empty:
            return None

        df = df.reset_index()

        # 统一收盘价列名
        if "Close" in df.columns:
            df.rename(columns={"Close": "close"}, inplace=True)
        elif "close" not in df.columns:
            return None

        return df
    except Exception:
        return None


def calc_ma20(df):
    df["ma20"] = df["close"].rolling(20).mean()
    return df


# ======================
# 大盘指数自动兜底
# ======================
def load_market_index():
    candidates = [
        ("沪深300指数", "000300.SS"),
        ("上证指数", "000001.SS"),
        ("恒生指数", "^HSI"),
    ]

    for name, code in candidates:
        df = load_data(code)
        if df is not None and len(df) >= 25:
            return name, df

    return None, None


# ======================
# 大盘环境判断
# ======================
st.header("📈 大盘环境")

market_name, index_df = load_market_index()

if index_df is None:
    st.error("❌ 大盘数据全部获取失败（Yahoo 当前不可用）")
    st.stop()

index_df = calc_ma20(index_df)

idx_latest = index_df.iloc[-1]
idx_prev = index_df.iloc[-2]

idx_close = float(idx_latest["close"])
idx_ma20 = float(idx_latest["ma20"])
idx_ma20_prev = float(idx_prev["ma20"])

market_ok = (
    idx_close > idx_ma20
    and idx_ma20 >= idx_ma20_prev
)

if market_ok:
    st.success(f"🟢 大盘环境：允许建仓（参考：{market_name}）")
else:
    st.error(f"🔴 大盘环境：禁止建仓（参考：{market_name}）")


# ======================
# ETF 判断区域
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
    if df is None or len(df) < 25:
        st.warning("⚠️ 数据获取失败 / 数据不足")
        continue

    df = calc_ma20(df)

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    price = float(latest["close"])
    ma20 = float(latest["ma20"])
    ma20_prev = float(prev["ma20"])

    etf_ok = (
        market_ok
        and price > ma20
        and ma20 >= ma20_prev
    )

    if etf_ok:
        st.success("✅ 可建仓")
        st.info("建议仓位：30%｜止损：-4% 或跌破 MA20｜止盈：+6% / +10%")
    else:
        st.warning("❌ 不符合建仓条件")

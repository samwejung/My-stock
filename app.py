import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="내 주식", page_icon="📈", layout="centered")
st.title("📈 내 관심종목")

# 1. 관심종목 입력 (쉼표로 구분)
text = st.text_input("관심종목 (쉼표로 구분)", "AAPL, MSFT, NVDA, TSLA")
tickers = [t.strip().upper() for t in text.split(",") if t.strip()]


@st.cache_data(ttl=300)  # 5분 동안 결과 재사용 (요청 횟수 절약)
def get_history(ticker, period):
    return yf.Ticker(ticker).history(period=period)


# 2. 현재가 / 등락률 표
rows = []
for t in tickers:
    try:
        h = get_history(t, "5d")
        last = h["Close"].iloc[-1]
        prev = h["Close"].iloc[-2]
        rows.append({
            "종목": t,
            "현재가($)": round(last, 2),
            "등락률(%)": round((last / prev - 1) * 100, 2),
        })
    except Exception:
        rows.append({"종목": t, "현재가($)": None, "등락률(%)": None})

if rows:
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

# 3. 차트
if tickers:
    st.subheader("차트")
    pick = st.selectbox("종목 선택", tickers)
    period = st.radio(
        "기간", ["1mo", "3mo", "6mo", "1y", "5y"], index=2, horizontal=True
    )
    try:
        h = get_history(pick, period)
        st.line_chart(h["Close"])
    except Exception:
        st.error("데이터를 불러오지 못했습니다. 종목 코드를 확인해 주세요.")

st.caption("데이터: Yahoo Finance (지연 시세일 수 있음)")

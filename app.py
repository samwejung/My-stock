import streamlit as st
import streamlit.components.v1 as components
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

# 3. 트레이딩뷰 차트
if tickers:
    st.subheader("차트")
    pick = st.selectbox("종목 선택", tickers)

    tv_html = f"""
    <div style="height:600px;width:100%">
      <div id="tv_chart" style="height:100%;width:100%"></div>
    </div>
    <script src="https://s3.tradingview.com/tv.js"></script>
    <script>
      new TradingView.widget({{
        "autosize": true,
        "symbol": "{pick}",
        "interval": "D",
        "timezone": "America/New_York",
        "theme": "light",
        "style": "1",
        "locale": "kr",
        "allow_symbol_change": true,
        "hide_side_toolbar": true,
        "save_image": false,
        "container_id": "tv_chart"
      }});
    </script>
    """
    components.html(tv_html, height=610)

st.caption("표: Yahoo Finance / 차트: TradingView (지연 시세일 수 있음)")

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

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

    period_days = {"1개월": 30, "3개월": 90, "6개월": 180, "1년": 365, "3년": 1095}
    period = st.radio("기간", list(period_days.keys()), index=2, horizontal=True)
    chart_type = st.radio("차트 모양", ["캔들", "라인", "면적"], horizontal=True)
    ma_options = [5, 20, 60, 120]
    mas = st.multiselect("이동평균선 (일)", ma_options, default=[20, 60])

    try:
        # 이동평균 계산을 위해 넉넉히 5년치를 받아서 계산한 뒤, 선택 기간만 잘라 보여줌
        full = get_history(pick, "5y")
        for m in mas:
            full[f"MA{m}"] = full["Close"].rolling(m).mean()
        cutoff = full.index.max() - pd.Timedelta(days=period_days[period])
        h = full[full.index >= cutoff]

        fig = go.Figure()
        if chart_type == "캔들":
            fig.add_trace(go.Candlestick(
                x=h.index, open=h["Open"], high=h["High"],
                low=h["Low"], close=h["Close"], name=pick,
                increasing_line_color="#e53935", decreasing_line_color="#1e88e5",
            ))
        elif chart_type == "라인":
            fig.add_trace(go.Scatter(x=h.index, y=h["Close"], name=pick, mode="lines"))
        else:
            fig.add_trace(go.Scatter(
                x=h.index, y=h["Close"], name=pick, fill="tozeroy", mode="lines"
            ))

        colors = {5: "#fb8c00", 20: "#8e24aa", 60: "#43a047", 120: "#6d4c41"}
        for m in mas:
            fig.add_trace(go.Scatter(
                x=h.index, y=h[f"MA{m}"], name=f"MA{m}",
                mode="lines", line=dict(width=1.5, color=colors[m]),
            ))

        low, high = h["Low"].min(), h["High"].max()
        fig.update_layout(
            height=450,
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis_rangeslider_visible=False,
            legend=dict(orientation="h", y=-0.15),
        )
        fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])  # 주말 빈칸 제거
        if chart_type != "면적":
            fig.update_yaxes(range=[low * 0.98, high * 1.02])
        st.plotly_chart(fig, use_container_width=True)
    except Exception:
        st.error("데이터를 불러오지 못했습니다. 종목 코드를 확인해 주세요.")

st.caption("데이터: Yahoo Finance (지연 시세일 수 있음)")

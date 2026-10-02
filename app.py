import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="내 주식", page_icon="📈", layout="centered")
st.title("📈 내 관심종목")

if st.button("🔄 페이지 전체 새로고침", use_container_width=True):
    st.cache_data.clear()  # 저장된 데이터를 비우고
    # 브라우저 페이지 자체를 다시 불러옴 (차트·스캐너 포함 전부 초기화)
    components.html("<script>window.parent.location.reload();</script>", height=0)

@st.cache_data(ttl=300)  # 5분 동안 결과 재사용 (요청 횟수 절약)
def get_history(ticker, period):
    return yf.Ticker(ticker).history(period=period)


# ── 공포·탐욕 지수 (CNN, 비공식 데이터 주소 사용) ──
@st.cache_data(ttl=600)
def get_fear_greed():
    import requests
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Origin": "https://edition.cnn.com",
        "Referer": "https://edition.cnn.com/",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
    }
    r = requests.get(
        "https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
        headers=headers, timeout=10,
    )
    r.raise_for_status()
    return r.json()["fear_and_greed"]


RATING_KR = {
    "extreme fear": "😱 극단적 공포", "fear": "😨 공포", "neutral": "😐 중립",
    "greed": "😀 탐욕", "extreme greed": "🤑 극단적 탐욕",
}

st.subheader("😨 공포·탐욕 지수 (CNN)")
try:
    fg = get_fear_greed()
    score = fg["score"]
    st.metric(
        RATING_KR.get(str(fg["rating"]).lower(), fg["rating"]),
        f"{score:.0f} / 100",
        f"{score - fg['previous_close']:+.1f} (전일 대비)",
    )
    gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"font": {"size": 44}},
        gauge={
            "axis": {"range": [0, 100], "tickvals": [0, 25, 45, 55, 75, 100]},
            "bar": {"color": "rgba(0,0,0,0)"},  # 막대는 숨기고 바늘(threshold)로 표시
            "steps": [
                {"range": [0, 25], "color": "#d32f2f"},
                {"range": [25, 45], "color": "#f57c00"},
                {"range": [45, 55], "color": "#fbc02d"},
                {"range": [55, 75], "color": "#9ccc65"},
                {"range": [75, 100], "color": "#2e7d32"},
            ],
            "threshold": {"line": {"color": "black", "width": 6},
                          "thickness": 0.9, "value": score},
        },
    ))
    gauge.update_layout(height=250, margin=dict(l=20, r=20, t=30, b=0))
    st.plotly_chart(gauge, use_container_width=True)
    st.caption("🔴 극단적 공포 0-25 · 🟠 공포 25-45 · 🟡 중립 45-55 · 🟢 탐욕 55-75 · 🟢 극단적 탐욕 75-100")
    def _box(label, v):
        return (
            '<div style="flex:1;text-align:center;padding:8px 4px;'
            'border:1px solid rgba(128,128,128,0.3);border-radius:8px;">'
            f'<div style="font-size:0.8rem;opacity:0.7;">{label}</div>'
            f'<div style="font-size:1.4rem;font-weight:600;">{v:.0f}</div></div>'
        )

    st.markdown(
        '<div style="display:flex;flex-direction:row;gap:8px;">'
        + _box("1주 전", fg["previous_1_week"])
        + _box("1개월 전", fg["previous_1_month"])
        + _box("1년 전", fg["previous_1_year"])
        + "</div>",
        unsafe_allow_html=True,
    )
except Exception as e:
    st.warning(f"CNN 공포·탐욕 지수를 불러오지 못했습니다. ({type(e).__name__}: {e})")
    st.link_button("CNN에서 직접 보기", "https://edition.cnn.com/markets/fear-and-greed")
    # 대체 지표: VIX (공포지수) — 높을수록 시장 불안
    try:
        vix = get_history("^VIX", "5d")["Close"]
        st.metric("대신 VIX(변동성 지수)", f"{vix.iloc[-1]:.2f}",
                  f"{vix.iloc[-1] - vix.iloc[-2]:+.2f} (전일 대비)")
        st.caption("VIX는 보통 20 아래면 안정, 30 이상이면 불안 구간으로 봅니다.")
    except Exception:
        pass

# ── 나스닥 100 종목 (구성 종목은 분기마다 바뀔 수 있으니 필요하면 직접 수정) ──
NASDAQ100 = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "TSLA", "AVGO", "COST",
    "NFLX", "ASML", "TMUS", "CSCO", "PEP", "LIN", "AZN", "ADBE", "AMD", "TXN",
    "QCOM", "INTU", "ISRG", "AMGN", "BKNG", "HON", "AMAT", "PDD", "CMCSA", "VRTX",
    "ADP", "PANW", "GILD", "SBUX", "ADI", "MU", "LRCX", "MELI", "INTC", "KLAC",
    "CRWD", "MDLZ", "REGN", "CDNS", "SNPS", "PYPL", "MAR", "ABNB", "CTAS", "ORLY",
    "CSX", "FTNT", "MRVL", "DASH", "WDAY", "ADSK", "PCAR", "ROP", "NXPI", "CPRT",
    "MNST", "CHTR", "AEP", "TTD", "KDP", "FAST", "PAYX", "ODFL", "ROST", "KHC",
    "AXON", "DDOG", "EA", "CTSH", "VRSK", "GEHC", "LULU", "EXC", "XEL", "IDXX",
    "TEAM", "CCEP", "BKR", "FANG", "CSGP", "ON", "DXCM", "ZS", "TTWO", "CDW",
    "GFS", "MDB", "BIIB", "WBD", "ARM", "APP", "PLTR", "CEG", "SHOP", "TRI",
    "MSTR", "DLTR",
]

# 1. 관심종목 입력 (쉼표로 구분)
text = st.text_input("관심종목 (쉼표로 구분)", "AAPL, MSFT, NVDA, TSLA")
tickers = [t.strip().upper() for t in text.split(",") if t.strip()]


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


# 3. 볼린저밴드 하단 스캐너 (나스닥 100, 일봉, 20일/표준편차 2)
@st.cache_data(ttl=1800)  # 30분 캐시
def scan_bb_lower(symbols):
    data = yf.download(
        list(symbols), period="6mo", interval="1d",
        group_by="ticker", auto_adjust=True, progress=False, threads=True,
    )
    out = []
    for t in symbols:
        try:
            close = data[t]["Close"].dropna()
            if len(close) < 20:
                continue
            ma = close.rolling(20).mean()
            sd = close.rolling(20).std(ddof=0)  # 트레이딩뷰와 같은 방식
            lower = (ma - 2 * sd).iloc[-1]
            last = close.iloc[-1]
            out.append({
                "종목": t,
                "종가($)": round(last, 2),
                "하단선($)": round(lower, 2),
                "하단 대비(%)": round((last / lower - 1) * 100, 2),
            })
        except Exception:
            continue
    return pd.DataFrame(out)


st.subheader("🔍 볼린저밴드 하단 스캐너")
st.caption("나스닥 100 · 일봉 · 볼린저밴드(20, 2)")
near = st.slider(
    "하단 대비 % 기준 (이 값 이하인 종목 표시)", -10.0, 5.0, 1.0, 0.5,
    help="예: 1 → 하단선 위 1% 이내 + 하단 이탈 종목 / 0 → 하단 이탈 종목만 / -3 → 하단선보다 3% 이상 아래인 종목만",
)

if st.button("스캔 실행"):
    with st.spinner("100개 종목 분석 중... (1분 정도 걸릴 수 있어요)"):
        st.session_state["scan_df"] = scan_bb_lower(tuple(NASDAQ100))

scan_hits = []
if "scan_df" in st.session_state:
    df = st.session_state["scan_df"]
    hits = df[df["하단 대비(%)"] <= near].copy()
    hits["상태"] = hits["하단 대비(%)"].apply(lambda x: "하단 이탈" if x < 0 else "근접")
    hits = hits.sort_values("하단 대비(%)")
    scan_hits = hits["종목"].tolist()
    st.write(f"분석 {len(df)}개 중 **{len(hits)}개** 해당")
    if len(hits):
        st.caption("👆 종목 행을 누르면 아래 차트에 표시됩니다.")
        event = st.dataframe(
            hits, hide_index=True, use_container_width=True,
            on_select="rerun", selection_mode="single-row", key="scan_table",
        )
        rows_sel = event.selection.rows
        if rows_sel:
            clicked = hits.iloc[rows_sel[0]]["종목"]
            # 새로 클릭했을 때만 차트 종목을 바꿈 (이후 직접 선택도 가능)
            if clicked != st.session_state.get("last_clicked"):
                st.session_state["last_clicked"] = clicked
                st.session_state["pick"] = clicked
        else:
            st.session_state["last_clicked"] = None
    else:
        st.info("조건에 맞는 종목이 없습니다. 기준값을 올려 보세요.")
    st.caption("'하단 대비'가 0 미만이면 하단선 아래, 0 이상이면 하단선 위에 있다는 뜻입니다.")

# 4. 트레이딩뷰 차트
options = tickers + [s for s in scan_hits if s not in tickers]
if options:
    st.subheader("차트")
    if st.session_state.get("pick") not in options:
        st.session_state.pop("pick", None)
    pick = st.selectbox("종목 선택 (스캔 결과 포함)", options, key="pick")

    tv_html = """
    <div class="tradingview-widget-container" style="height:600px;width:100%">
      <div class="tradingview-widget-container__widget" style="height:600px;width:100%"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
      {
        "width": "100%",
        "height": "600",
        "symbol": "__SYM__",
        "interval": "D",
        "timezone": "America/New_York",
        "theme": "light",
        "style": "1",
        "locale": "kr",
        "allow_symbol_change": true,
        "hide_side_toolbar": true,
        "studies": ["STD;Bollinger_Bands"],
        "support_host": "https://www.tradingview.com"
      }
      </script>
    </div>
    """.replace("__SYM__", pick)
    components.html(tv_html, height=620)

st.caption("표·스캐너: Yahoo Finance / 차트: TradingView (지연 시세일 수 있음)")

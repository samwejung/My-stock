import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="내 주식", page_icon="📈", layout="centered")
st.title("📈 내 관심종목")
st.markdown(
    "<style>"
    "div[data-testid='stVerticalBlock']{gap:0.6rem;}"
    "div[data-testid='stVegaLiteChart']{pointer-events:none;}"  # 차트 터치·확대 비활성화
    "</style>",
    unsafe_allow_html=True,
)

if st.button("🔄 페이지 전체 새로고침", use_container_width=True):
    st.cache_data.clear()  # 저장된 데이터를 비우고
    # 브라우저 페이지 자체를 다시 불러옴 (차트·스캐너 포함 전부 초기화)
    components.html("<script>window.parent.location.reload();</script>", height=0)

def section_title(text):
    st.markdown(
        f'<div style="font-size:1.25rem;font-weight:600;margin:0;">{text}</div>',
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=300)  # 5분 동안 결과 재사용 (요청 횟수 절약)
def get_history(ticker, period):
    return yf.Ticker(ticker).history(period=period)


import math


def zone_of(v):
    """점수 → (영문 이름, 한글 이름, 채움색, 테두리색)"""
    if v < 25:
        return ("EXTREME FEAR", "극단적 공포", "#f6c9c4", "#d9534f")
    if v < 45:
        return ("FEAR", "공포", "#f9ddd0", "#d98a4e")
    if v < 55:
        return ("NEUTRAL", "중립", "#ece9d8", "#b5ad7f")
    if v < 75:
        return ("GREED", "탐욕", "#cdeee3", "#5bbfa3")
    return ("EXTREME GREED", "극단적 탐욕", "#b5e6d3", "#2f9e7a")


def make_cnn_html(fg):
    """CNN 스타일 공포·탐욕 게이지 + 전일/1주/1개월/1년 비교 (SVG+HTML)"""
    score = float(fg["score"])
    cx, cy, r_out, r_in, r_tick = 350, 350, 340, 210, 192

    def pt(r, v):
        th = math.pi * (1 - v / 100)
        return cx + r * math.cos(th), cy - r * math.sin(th)

    # 구간: (시작, 끝, 윗줄, 아랫줄, 윗줄 글자폭, 아랫줄 글자폭)
    zones = [
        (0, 25, "EXTREME", "FEAR", 104, 58),
        (25, 45, "FEAR", None, 58, 0),
        (45, 55, "NEUTRAL", None, 76, 0),
        (55, 75, "GREED", None, 72, 0),
        (75, 100, "EXTREME", "GREED", 104, 72),
    ]

    def seg_path(lo, hi):
        x1, y1 = pt(r_out, lo)
        x2, y2 = pt(r_out, hi)
        x3, y3 = pt(r_in, hi)
        x4, y4 = pt(r_in, lo)
        return (
            f"M{x1:.1f},{y1:.1f} A{r_out},{r_out} 0 0 1 {x2:.1f},{y2:.1f} "
            f"L{x3:.1f},{y3:.1f} A{r_in},{r_in} 0 0 0 {x4:.1f},{y4:.1f} Z"
        )

    _, _, act_fill, act_stroke = zone_of(score)
    act_lo, act_hi = {
        0: (0, 25), 1: (25, 45), 2: (45, 55), 3: (55, 75), 4: (75, 100)
    }[0 if score < 25 else 1 if score < 45 else 2 if score < 55 else 3 if score < 75 else 4]

    parts = []
    # 기본 회색 구간 (흰 간격선 포함)
    for lo, hi, *_ in zones:
        parts.append(f'<path d="{seg_path(lo, hi)}" fill="#f4f4f4" stroke="#fff" stroke-width="6"/>')
    # 현재 구간 강조
    parts.append(
        f'<path d="{seg_path(act_lo, act_hi)}" fill="{act_fill}" '
        f'stroke="{act_stroke}" stroke-width="3"/>'
    )

    # 구간 이름 (호를 따라 회전)
    r_mid = (r_out + r_in) / 2
    for lo, hi, l1, l2, w1, w2 in zones:
        mid = (lo + hi) / 2
        rot = 90 - math.degrees(math.pi * (1 - mid / 100))
        is_act = (lo, hi) == (act_lo, act_hi)
        color = "#444" if is_act else "#8a8a8a"
        size = 22 if l1 == "NEUTRAL" else 26
        lines = [(l1, w1)] if not l2 else [(l1, w1), (l2, w2)]
        radii = [r_mid] if not l2 else [r_mid + 17, r_mid - 17]
        for (word, w), rr in zip(lines, radii):
            lx, ly = pt(rr, mid)
            parts.append(
                f'<text x="{lx:.1f}" y="{ly:.1f}" transform="rotate({rot:.1f} {lx:.1f} {ly:.1f})" '
                f'text-anchor="middle" dominant-baseline="central" font-size="{size}" '
                f'font-weight="800" fill="{color}" textLength="{w}" lengthAdjust="spacingAndGlyphs" '
                f'style="font-family:\'Arial Narrow\',\'Avenir Next Condensed\',Impact,sans-serif">{word}</text>'
            )

    # 안쪽 점선 눈금 + 숫자
    for i in range(17):
        v = i * 6.25
        if v % 25 == 0:
            continue
        x, y = pt(r_tick, v)
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.6" fill="#a8a8a8"/>')
    for v in (0, 25, 50, 75, 100):
        x, y = pt(r_tick, v)
        if v in (0, 100):
            y -= 14
        parts.append(
            f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" dominant-baseline="central" '
            f'font-size="25" fill="#8a8a8a">{v}</text>'
        )

    # 바늘 (끝이 뾰족한 검정 삼각형)
    tx, ty = pt(r_mid - 5, score)
    th = math.pi * (1 - score / 100)
    px, py = -math.sin(th), -math.cos(th)  # 바늘과 수직 방향
    half = 11
    parts.append(
        f'<polygon points="{tx:.1f},{ty:.1f} {cx + px * half:.1f},{cy + py * half:.1f} '
        f'{cx - px * half:.1f},{cy - py * half:.1f}" fill="#222"/>'
    )
    # 가운데 허브 + 점수
    parts.append(
        f'<circle cx="{cx}" cy="{cy}" r="66" fill="#fff" filter="url(#sh)"/>'
        f'<text x="{cx}" y="{cy - 24}" text-anchor="middle" dominant-baseline="central" '
        f'font-size="56" font-weight="800" fill="#222">{score:.0f}</text>'
    )
    svg = (
        '<svg viewBox="0 0 700 354" width="100%" xmlns="http://www.w3.org/2000/svg">'
        '<defs><filter id="sh" x="-30%" y="-30%" width="160%" height="160%">'
        '<feDropShadow dx="0" dy="-2" stdDeviation="6" flood-opacity="0.18"/></filter></defs>'
        + "".join(parts) + "</svg>"
    )

    # 전일 종가 / 1주 / 1개월 / 1년 (가로 한 줄)
    def badge(label, v):
        _, kr, fill, stroke = zone_of(v)
        return (
            '<div style="flex:1;min-width:0;text-align:center;">'
            f'<div style="font-size:11px;color:#777;">{label}</div>'
            f'<div style="font-size:13px;font-weight:700;color:#222;margin:2px 0 6px;">{kr}</div>'
            f'<div style="display:inline-flex;align-items:center;justify-content:center;'
            f'width:38px;height:38px;border-radius:50%;background:{fill};'
            f'border:2px solid {stroke};font-size:15px;font-weight:800;color:#222;">{v:.0f}</div>'
            "</div>"
        )

    row = (
        '<div style="display:flex;flex-direction:row;gap:6px;margin-top:6px;'
        'padding:10px 4px 6px;border-top:1px solid #eee;">'
        + badge("전일 종가", fg["previous_close"])
        + badge("1주 전", fg["previous_1_week"])
        + badge("1개월 전", fg["previous_1_month"])
        + badge("1년 전", fg["previous_1_year"])
        + "</div>"
    )
    return (
        '<body style="margin:0;">'
        '<div id="wrap" style="background:#fff;border-radius:12px;padding:10px 8px 8px;'
        'max-width:360px;margin:0 auto;'
        'font-family:-apple-system,Helvetica,Arial,sans-serif;">' + svg + row + "</div>"
        + "</body>"
    )


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

section_title("😨 공포·탐욕 지수 (CNN)")
try:
    fg = get_fear_greed()
    components.html(make_cnn_html(fg), height=318)
except Exception as e:
    st.warning(f"CNN 공포·탐욕 지수를 불러오지 못했습니다. ({type(e).__name__}: {e})")
    st.link_button("CNN에서 직접 보기", "https://edition.cnn.com/markets/fear-and-greed")

# ── VIX 지수 (공포지수, 변동성) ──
section_title("📉 VIX 변동성 지수")
try:
    vix_hist = get_history("^VIX", "3mo")["Close"].dropna()
    v_now, v_prev = float(vix_hist.iloc[-1]), float(vix_hist.iloc[-2])
    diff = v_now - v_prev
    if v_now < 15:
        v_label = "🟢 안정"
    elif v_now < 20:
        v_label = "🟡 보통"
    elif v_now < 30:
        v_label = "🟠 불안"
    else:
        v_label = "🔴 공포"
    d_color = "#e53935" if diff > 0 else "#2e9e5b"  # VIX 상승=불안(빨강), 하락=안정(초록)
    arrow = "▲" if diff > 0 else "▼" if diff < 0 else "–"
    st.markdown(
        '<div style="display:flex;align-items:baseline;gap:10px;white-space:nowrap;">'
        f'<span style="font-size:1.35rem;font-weight:700;">{v_now:.2f}</span>'
        f'<span style="font-size:0.85rem;font-weight:600;color:{d_color};">{arrow} {abs(diff):.2f}</span>'
        '<span style="font-size:0.85rem;opacity:0.4;">|</span>'
        f'<span style="font-size:0.9rem;font-weight:600;">{v_label}</span>'
        "</div>",
        unsafe_allow_html=True,
    )
    st.line_chart(vix_hist, height=150)
    st.caption("최근 3개월 · 15 미만 안정 / 15~20 보통 / 20~30 불안 / 30 이상 공포")
except Exception as e:
    st.warning(f"VIX를 불러오지 못했습니다. ({type(e).__name__}: {e})")

# ── 시장 지표 요약 (10년물 금리 · 원/달러 · 나스닥100/반도체 200일선) ──
section_title("🌐 시장 지표")


def market_row(name, value_txt, chg_txt, up, sub=""):
    color = "#e53935" if up > 0 else "#1e88e5" if up < 0 else "#888"  # 상승 빨강 / 하락 파랑
    sub_html = f'<div style="font-size:0.75rem;opacity:0.75;margin-top:2px;">{sub}</div>' if sub else ""
    return (
        '<div style="display:flex;justify-content:space-between;align-items:center;'
        'padding:8px 2px;border-bottom:1px solid rgba(128,128,128,0.25);">'
        f'<div><div style="font-size:0.9rem;font-weight:600;">{name}</div>{sub_html}</div>'
        '<div style="text-align:right;">'
        f'<div style="font-size:1rem;font-weight:700;">{value_txt}</div>'
        f'<div style="font-size:0.8rem;font-weight:600;color:{color};">{chg_txt}</div>'
        "</div></div>"
    )


def sign_arrow(x):
    return "▲" if x > 0 else "▼" if x < 0 else "–"


market_html = []

# 1) 미국 10년물 금리 (등락은 %p)
try:
    c = get_history("^TNX", "1mo")["Close"].dropna()
    now, prev = float(c.iloc[-1]), float(c.iloc[-2])
    d = now - prev
    market_html.append(market_row(
        "미국 10년물 금리", f"{now:.2f}%", f"{sign_arrow(d)} {abs(d):.2f}%p", d))
except Exception:
    market_html.append(market_row("미국 10년물 금리", "불러오기 실패", "", 0))

# 2) 원/달러 환율
try:
    c = get_history("KRW=X", "1mo")["Close"].dropna()
    now, prev = float(c.iloc[-1]), float(c.iloc[-2])
    d = now - prev
    market_html.append(market_row(
        "원/달러 환율", f"{now:,.2f}원", f"{sign_arrow(d)} {abs(d):.2f}원 ({d / prev * 100:+.2f}%)", d))
except Exception:
    market_html.append(market_row("원/달러 환율", "불러오기 실패", "", 0))

# 3) 나스닥100 / 반도체지수 + 200일 이동평균 위·아래
for name, sym in (("나스닥100", "^NDX"), ("반도체지수 (SOX)", "^SOX")):
    try:
        c = get_history(sym, "2y")["Close"].dropna()
        now, prev = float(c.iloc[-1]), float(c.iloc[-2])
        d = now - prev
        ma200 = float(c.rolling(200).mean().iloc[-1])
        gap = (now / ma200 - 1) * 100
        sub = (
            f"🟢 200일선 위 ({gap:+.1f}%)" if gap >= 0 else f"🔴 200일선 아래 ({gap:+.1f}%)"
        )
        market_html.append(market_row(
            name, f"{now:,.2f}", f"{sign_arrow(d)} {abs(d / prev * 100):.2f}%", d, sub))
    except Exception:
        market_html.append(market_row(name, "불러오기 실패", "", 0))

st.markdown("".join(market_html), unsafe_allow_html=True)
st.caption("200일선 위: 상승 추세 / 아래: 하락 추세로 보는 대표적 기준입니다. (상승 빨강, 하락 파랑)")

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
text = st.text_input("관심종목 (쉼표로 구분)", "TQQQ, SOXL")
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


section_title("🔍 볼린저밴드 하단 스캐너")
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
    section_title("📊 차트")
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

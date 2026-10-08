import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="미국주식 시황", page_icon="📈", layout="centered")
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

# 3. 볼린저밴드 하단 스캐너 (나스닥 100, 일봉, 20일/표준편차 2)
def _live_info(close_1m):
    """1분봉 종가 시리즈 → (미국 현지 날짜, 가장 최근 가격)"""
    s = close_1m.dropna()
    if s.empty:
        return None
    ts = s.index[-1]
    ts_et = ts.tz_convert("America/New_York") if ts.tzinfo is not None else ts
    return ts_et.date(), float(s.iloc[-1])


def _bb_row(t, close, realtime, live):
    """종가 시리즈 → 스캐너 한 줄.
    realtime=False: 마감이 확정된 종가만 사용 (진행 중인 오늘 봉은 제외, 일봉에 빠진 최근 마감일은 1분봉으로 보충)
    realtime=True : 장중이면 현재가를 오늘 봉으로 사용"""
    close = close.dropna().copy()
    if len(close) == 0:
        return None
    idx = close.index
    close.index = (idx.tz_localize(None) if idx.tz is not None else idx).normalize()
    now_et = pd.Timestamp.now(tz="America/New_York")
    minutes = now_et.hour * 60 + now_et.minute
    day_in_progress = now_et.weekday() < 5 and minutes < 16 * 60 + 15

    if live:
        d, price = live
        complete = d < now_et.date() or minutes >= 16 * 60 + 15  # 그 날 장이 끝났는가
        last_d = close.index[-1].date()
        if last_d < d:                       # 일봉에 아직 없는 최근 날짜
            if realtime or complete:
                close.loc[pd.Timestamp(d)] = price
        elif last_d == d and realtime:       # 같은 날이면 더 최신 가격으로 교체
            close.iloc[-1] = price
    if not realtime and day_in_progress and close.index[-1].date() == now_et.date():
        close = close.iloc[:-1]              # 진행 중인 오늘 봉 제외

    if len(close) < 20:
        return None
    ma = close.rolling(20).mean()
    sd = close.rolling(20).std(ddof=0)  # 트레이딩뷰와 같은 방식
    lower = (ma - 2 * sd).iloc[-1]
    last = close.iloc[-1]
    return {
        "종목": t,
        "종가($)": round(float(last), 2),
        "하단선($)": round(float(lower), 2),
        "하단 대비(%)": round(float((last / lower - 1) * 100), 2),
        "기준일": str(close.index[-1].date()),
    }


@st.cache_data(ttl=120)  # 2분 캐시
def scan_bb_lower(symbols, realtime=False):
    # 1단계: 100개 종목의 일봉 + 1분봉(최신가)을 한 번에 받아 후보를 추림
    data = yf.download(
        list(symbols), period="6mo", interval="1d",
        group_by="ticker", auto_adjust=False, progress=False, threads=True,
    )
    lives = {}
    try:
        intra = yf.download(
            list(symbols), period="1d", interval="1m",
            group_by="ticker", auto_adjust=False, progress=False, threads=True,
        )
        for t in symbols:
            try:
                lives[t] = _live_info(intra[t]["Close"])
            except Exception:
                pass
    except Exception:
        pass
    out = []
    for t in symbols:
        try:
            row = _bb_row(t, data[t]["Close"], realtime, lives.get(t))
            if row:
                out.append(row)
        except Exception:
            continue
    # 2단계: 후보(하단선 위 6% 이내)는 종목별로 다시 받아 값을 확정
    for i, row in enumerate(out):
        if row["하단 대비(%)"] <= 6:
            try:
                tk = yf.Ticker(row["종목"])
                h = tk.history(period="6mo", interval="1d", auto_adjust=False)
                live = _live_info(tk.history(period="1d", interval="1m")["Close"])
                fixed = _bb_row(row["종목"], h["Close"], realtime, live)
                if fixed:
                    out[i] = fixed
            except Exception:
                pass
    return pd.DataFrame(out)



def home():
    st.title("📈 미국주식 시황")

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

    st.caption("시세: Yahoo Finance · 공포·탐욕 지수: CNN (무료 데이터라 최대 약 15분 지연될 수 있음)")


def scanner():
    st.title("🔍 볼린저밴드 스캐너")
    st.caption("나스닥 100 · 일봉 · 볼린저밴드(20, 2)")
    near = st.slider(
        "하단 대비 % 기준 (이 값 이하인 종목 표시)", -10.0, 5.0,
        st.session_state.get("saved_near", 1.0), 0.5,
        help="예: 1 → 하단선 위 1% 이내 + 하단 이탈 종목 / 0 → 하단 이탈 종목만 / -3 → 하단선보다 3% 이상 아래인 종목만",
    )

    st.session_state["saved_near"] = near

    mode = st.radio(
        "가격 기준", ["확정 종가", "실시간 현재가 포함"], horizontal=True,
        help="확정 종가: 마감이 끝난 가장 최근 날 종가로 계산합니다. "
             "실시간: 장중이면 지금 가격을 오늘 봉으로 사용해 계산합니다.",
    )
    realtime = mode == "실시간 현재가 포함"
    if st.button("스캔 실행"):
        with st.spinner("100개 종목 분석 중... (1분 정도 걸릴 수 있어요)"):
            st.session_state["scan_df"] = scan_bb_lower(tuple(NASDAQ100), realtime)
            st.session_state["scan_time"] = pd.Timestamp.now(tz="Asia/Seoul")
            st.session_state["scan_mode"] = mode

    scan_hits = []
    if "scan_df" in st.session_state:
        df_all = st.session_state["scan_df"]
        ref_date = df_all["기준일"].max() if len(df_all) else "-"
        df = df_all[df_all["기준일"] == ref_date] if len(df_all) else df_all
        stale = len(df_all) - len(df)  # 날짜가 하루라도 뒤처진 종목은 제외
        missing = len(NASDAQ100) - len(df_all)  # 데이터를 아예 못 받은 종목
        hits = df[df["하단 대비(%)"] <= near].drop(columns=["기준일"]).copy()
        hits["상태"] = hits["하단 대비(%)"].apply(lambda x: "하단 이탈" if x < 0 else "근접")
        hits = hits.sort_values("하단 대비(%)")
        scan_hits = hits["종목"].tolist()
        st_time = st.session_state.get("scan_time")
        if st_time is not None:
            age_min = (pd.Timestamp.now(tz="Asia/Seoul") - st_time).total_seconds() / 60
            st.caption(
                f"🕒 스캔 시각 {st_time.strftime('%m/%d %H:%M')} (한국시간) · {st.session_state.get('scan_mode', '')}"
                + (" · ⚠️ 오래된 결과입니다. 다시 스캔해 주세요." if age_min > 30 else "")
            )
        st.write(f"기준일 **{ref_date}** (미국 현지) · 분석 {len(df)}개 중 **{len(hits)}개** 해당")
        if stale or missing:
            st.caption(f"⚠️ 데이터 문제로 제외: 최신일 아님 {stale}개 · 조회 실패 {missing}개 (잠시 후 다시 스캔해 보세요)")
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

            with st.expander("🔎 계산 검증 (최근 6일 종가·하단선)"):
                chk = st.selectbox("종목", hits["종목"].tolist(), key="chk_sym")
                try:
                    full_h = yf.Ticker(chk).history(period="6mo", auto_adjust=False).dropna(subset=["Close"])
                    hh = full_h["Close"]
                    ma_ = hh.rolling(20).mean()
                    lo_ = ma_ - 2 * hh.rolling(20).std(ddof=0)
                    base_day = df.set_index("종목").loc[chk, "기준일"]
                    detail = pd.DataFrame({
                        "날짜": [d.strftime("%Y-%m-%d") for d in hh.index],
                        "종가": hh.round(2).values,
                        "고가": full_h["High"].round(2).values,
                        "저가": full_h["Low"].round(2).values,
                        "거래량(만)": (full_h["Volume"] / 10000).round(0).values,
                        "중심선": ma_.round(2).values,
                        "하단선": lo_.round(2).values,
                        "하단 대비(%)": ((hh / lo_ - 1) * 100).round(2).values,
                    }).tail(6)
                    detail["스캔 기준"] = ["◀" if d == base_day else "" for d in detail["날짜"]]
                    st.dataframe(detail.iloc[::-1], hide_index=True, use_container_width=True)
                    st.caption("트레이딩뷰 볼린저밴드(20, 2)와 같은 계산입니다. '◀'가 스캐너가 사용한 날짜예요.")
                except Exception as e:
                    st.warning(f"검증 데이터를 불러오지 못했습니다. ({type(e).__name__})")
        else:
            st.info("조건에 맞는 종목이 없습니다. 기준값을 올려 보세요.")
        st.caption("'하단 대비'가 0 미만이면 하단선 아래, 0 이상이면 하단선 위에 있다는 뜻입니다.")

    # 4. 트레이딩뷰 차트
    options = list(scan_hits)
    if options:
        section_title("📊 차트")
        if st.session_state.get("pick") not in options:
            st.session_state.pop("pick", None)
        pick = st.selectbox("종목 선택 (스캔 결과)", options, key="pick")

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
    else:
        st.caption("스캔을 실행하면 결과 종목의 차트를 이 아래에서 볼 수 있습니다.")

    st.caption("시세·스캐너: Yahoo Finance / 차트: TradingView (무료 데이터라 최대 약 15분 지연될 수 있음)")


# ════════════════════════════════════════════════
#  백테스트 페이지
# ════════════════════════════════════════════════
@st.cache_data(ttl=3600)
def load_prices(sym):
    return yf.Ticker(sym).history(period="max", auto_adjust=True)["Close"].dropna()


STRATEGIES = {
    "200일선 위에서만 보유": "ma",
    "골든크로스 (50일선 > 200일선)": "cross",
    "볼린저 하단 매수 → 중심선 매도": "bb",
    "볼린저 하단 분할매수 + 평단 익절": "scale",
}


def make_signal(close, kind, ma_len):
    """종가 기준 보유(1)/현금(0) 신호"""
    if kind == "ma":
        ma = close.rolling(ma_len).mean()
        return ((close > ma) & ma.notna()).astype(float)
    if kind == "cross":
        fast, slow = close.rolling(50).mean(), close.rolling(200).mean()
        return ((fast > slow) & slow.notna()).astype(float)
    ma = close.rolling(20).mean()
    sd = close.rolling(20).std(ddof=0)
    lower = ma - 2 * sd
    pos, out = 0.0, []
    for c, m, lo in zip(close.values, ma.values, lower.values):
        if pos == 0.0 and lo == lo and c < lo:
            pos = 1.0
        elif pos == 1.0 and m == m and c > m:
            pos = 0.0
        out.append(pos)
    return pd.Series(out, index=close.index)


def run_backtest(close, kind, ma_len, cost_pct, years):
    """신호는 종가에 확인하고 다음 거래일부터 반영 (미래 데이터 사용 방지)"""
    sig = make_signal(close, kind, ma_len)
    pos = sig.shift(1).fillna(0.0)
    ret = close.pct_change().fillna(0.0)
    if years:
        cutoff = close.index[-1] - pd.DateOffset(years=years)
        keep = close.index >= cutoff
        pos, ret, sig = pos[keep], ret[keep], sig[keep]
    turn = pos.diff().abs().fillna(pos.abs())
    strat_ret = pos * ret - turn * (cost_pct / 100)
    equity = (1 + strat_ret).cumprod() * 100
    hold = (1 + ret).cumprod() * 100
    entries = int(((pos.diff() == 1) | ((pos.index == pos.index[0]) & (pos == 1))).sum())
    return equity, hold, pos, sig, entries


def run_scale_backtest(close, years, below_pct, buy_pct, tp_pct, max_buys, cost_pct, new_only):
    """볼린저밴드(20, 2) 하단선보다 below_pct% 아래로 내려오면 buy_pct% 매수,
    평단가 대비 tp_pct% 이상 오르면 전량 매도. 매수는 사이클당 최대 max_buys회.
    매수·매도 모두 그날 종가로 체결한 것으로 계산하고, 전량 매도하면 새 사이클을 시작한다."""
    ma = close.rolling(20).mean()
    sd = close.rolling(20).std(ddof=0)
    trigger = (ma - 2 * sd) * (1 - below_pct / 100)
    cond = (close <= trigger) & trigger.notna()
    if years:
        keep = close.index >= close.index[-1] - pd.DateOffset(years=years)
        close, cond = close[keep], cond[keep]

    cost = cost_pct / 100
    cash, shares, basis, n_buys, base = 100.0, 0.0, 0.0, 0, 0.0
    prev_cond, eq, trades = False, [], []
    for date, c, cd in zip(close.index, close.values, cond.values):
        avg = basis / shares if shares > 0 else 0.0
        if shares > 0 and c >= avg * (1 + tp_pct / 100):  # 익절: 전량 매도
            cash += shares * c * (1 - cost)
            trades.append({"날짜": date.date(), "구분": "매도(익절)", "체결가": round(c, 2),
                           "평단": round(avg, 2), "수익률(%)": round((c / avg - 1) * 100, 2),
                           "매수 누적": n_buys})
            shares, basis, n_buys = 0.0, 0.0, 0
        elif cd and n_buys < max_buys and not (new_only and prev_cond):
            if n_buys == 0:
                base = cash  # 사이클 시작 시점 자산을 기준으로 비중 계산
            amt = min(base * buy_pct / 100, cash)
            if amt > 0:
                sh = amt / (c * (1 + cost))
                shares += sh
                basis += sh * c
                cash -= amt
                n_buys += 1
                trades.append({"날짜": date.date(), "구분": f"매수 {n_buys}회", "체결가": round(c, 2),
                               "평단": round(basis / shares, 2), "수익률(%)": None,
                               "매수 누적": n_buys})
        prev_cond = bool(cd)
        eq.append(cash + shares * c)

    equity = pd.Series(eq, index=close.index)
    hold = close / close.iloc[0] * 100
    state = {
        "shares": shares, "n_buys": n_buys, "last": float(close.iloc[-1]),
        "avg": basis / shares if shares > 0 else None, "cash": cash,
    }
    return equity, hold, pd.DataFrame(trades), state


def metrics(eq, entries=None):
    yrs = max((eq.index[-1] - eq.index[0]).days / 365.25, 1e-9)
    total = eq.iloc[-1] / 100 - 1
    cagr = (eq.iloc[-1] / 100) ** (1 / yrs) - 1
    mdd = (eq / eq.cummax() - 1).min()
    return {
        "총수익률": f"{total * 100:+.1f}%",
        "연평균(CAGR)": f"{cagr * 100:+.1f}%",
        "최대낙폭(MDD)": f"{mdd * 100:.1f}%",
        "매수 횟수": "-" if entries is None else f"{entries}회",
    }


def trade_chart(price, buys, sells):
    """종가 라인 위에 매수(▲ 빨강) / 매도(▼ 파랑) 표시. buys/sells: date, price 열을 가진 DataFrame"""
    import altair as alt

    p = price.copy()
    p.index = p.index.tz_localize(None) if p.index.tz is not None else p.index
    line_df = pd.DataFrame({"date": p.index, "price": p.values})

    def prep(df):
        if df is None or len(df) == 0:
            return pd.DataFrame({"date": pd.to_datetime([]), "price": []})
        out = pd.DataFrame({"date": pd.to_datetime(df["date"]), "price": df["price"].astype(float)})
        return out

    x = alt.X("date:T", title=None)
    y = alt.Y("price:Q", title=None, scale=alt.Scale(zero=False))
    base = alt.Chart(line_df).mark_line(color="#9e9e9e", strokeWidth=1.5).encode(x=x, y=y)
    b = alt.Chart(prep(buys)).mark_point(shape="triangle-up", filled=True, size=110, color="#e53935") \
        .encode(x=x, y=y, tooltip=[alt.Tooltip("date:T", title="날짜"), alt.Tooltip("price:Q", title="체결가", format=".2f")])
    sl = alt.Chart(prep(sells)).mark_point(shape="triangle-down", filled=True, size=110, color="#1e88e5") \
        .encode(x=x, y=y, tooltip=[alt.Tooltip("date:T", title="날짜"), alt.Tooltip("price:Q", title="체결가", format=".2f")])
    return (base + b + sl).properties(height=280)


def backtest():
    st.title("🧪 백테스트")
    st.caption("과거 데이터로 전략을 시험해 보는 도구입니다. 과거 성과가 미래 수익을 보장하지 않습니다.")

    section_title("⚙️ 설정")
    # 다른 페이지에 다녀와도 마지막 입력값 유지
    if "bt_sym" not in st.session_state:
        st.session_state["bt_sym"] = st.session_state.get("bt_sym_saved", "TQQQ")

    def _pick_ticker():  # 빠른 선택 버튼을 누르면 입력칸 값을 바꿈
        v = st.session_state.get("bt_pill")
        if v:
            st.session_state["bt_sym"] = v
            st.session_state["bt_pill"] = None

    st.text_input("종목 티커 (직접 입력)", key="bt_sym", placeholder="예: TQQQ, SOXL, NVDA, AAPL")
    quick = ["TQQQ", "SOXL", "QQQ", "SPY", "NVDA", "AAPL"]
    if hasattr(st, "pills"):
        st.pills("빠른 선택", quick, key="bt_pill", on_change=_pick_ticker)
    sym = st.session_state["bt_sym"].strip().upper()
    st.session_state["bt_sym_saved"] = sym
    strat_name = st.selectbox("전략", list(STRATEGIES.keys()))
    kind = STRATEGIES[strat_name]
    ma_len = 200
    if kind == "ma":
        ma_len = st.slider("이동평균 기간 (일)", 20, 250, 200, 10)
    sp = {}
    if kind == "scale":
        sp["below"] = st.number_input("하단선 이탈폭 (%)", 0.0, 10.0, 1.0, 0.5,
                                      help="볼린저 하단선보다 이 % 아래로 내려가면 매수 조건 충족")
        sp["buy_pct"] = st.number_input("1회 매수 비중 (%)", 1.0, 100.0, 20.0, 5.0,
                                        help="사이클 시작 시점 자산 대비 비율")
        sp["tp"] = st.number_input("익절 기준 (평단가 대비 %)", 0.5, 50.0, 3.0, 0.5)
        sp["max_buys"] = st.number_input("최대 매수 횟수", 1, 20, 5, 1)
        sp["new_only"] = st.checkbox("조건이 새로 충족된 날만 매수 (연속 하락일 중복 매수 제외)", value=False)
    period_label = st.radio("기간", ["3년", "5년", "10년", "전체"], index=1, horizontal=True)
    years = {"3년": 3, "5년": 5, "10년": 10, "전체": 0}[period_label]
    cost = st.number_input("거래 비용 (%, 매수·매도 각각)", 0.0, 2.0, 0.1, 0.05)

    if not st.button("▶ 백테스트 실행", use_container_width=True):
        st.info("설정을 고른 뒤 실행 버튼을 눌러주세요.")
        return
    if not sym:
        st.warning("종목을 입력해 주세요.")
        return
    try:
        close = load_prices(sym)
        if len(close) < 300:
            st.warning("데이터가 너무 적어 백테스트하기 어렵습니다.")
            return
        if kind == "scale":
            eq, hold, trades, state = run_scale_backtest(
                close, years, sp["below"], sp["buy_pct"], sp["tp"],
                int(sp["max_buys"]), cost, sp["new_only"])
            entries = int(trades["구분"].str.startswith("매수").sum()) if len(trades) else 0
        else:
            eq, hold, pos, sig, entries = run_backtest(close, kind, ma_len, cost, years)
    except Exception as e:
        st.error(f"데이터를 불러오지 못했습니다. ({type(e).__name__}: {e})")
        return

    section_title("📊 결과")
    st.caption(f"{sym} · {strat_name} · {eq.index[0].date()} ~ {eq.index[-1].date()}")
    res = pd.DataFrame(
        {"전략": metrics(eq, entries), "단순 보유": metrics(hold)}
    )
    st.dataframe(res, use_container_width=True)
    st.line_chart(pd.DataFrame({"전략": eq, "단순 보유": hold}), height=260)
    st.caption("시작을 100으로 맞춘 자산 추이입니다. 신호는 종가 확인 후 다음 거래일에 반영했습니다.")

    # 매수·매도 시점 표시
    px = close.loc[eq.index]
    if kind == "scale":
        if len(trades):
            tdf = trades.assign(date=pd.to_datetime(trades["날짜"]), price=trades["체결가"])
            buys_df = tdf[tdf["구분"].str.startswith("매수")][["date", "price"]]
            sells_df = tdf[tdf["구분"] == "매도(익절)"][["date", "price"]]
        else:
            buys_df = sells_df = None
    else:
        chg = sig.diff()
        chg.iloc[0] = sig.iloc[0]  # 첫날부터 보유 신호면 첫날 매수로 표시
        buys_df = pd.DataFrame({"date": px.index[chg.values > 0], "price": px[chg.values > 0].values})
        sells_df = pd.DataFrame({"date": px.index[chg.values < 0], "price": px[chg.values < 0].values})
    st.markdown("**📍 매수·매도 시점**")
    try:
        st.altair_chart(trade_chart(px, buys_df, sells_df), use_container_width=True)
        nb = 0 if buys_df is None else len(buys_df)
        ns_ = 0 if sells_df is None else len(sells_df)
        st.caption(f"🔺 빨강 = 매수 ({nb}회) · 🔻 파랑 = 매도 ({ns_}회) · 체결가는 해당일 종가")
    except Exception as e:
        st.warning(f"매수·매도 차트를 그리지 못했습니다. ({type(e).__name__}: {e})")

    if kind == "scale":
        wins = int((trades["구분"] == "매도(익절)").sum()) if len(trades) else 0
        st.markdown(f"**익절 {wins}회 · 매수 {entries}회**")
        if state["shares"] > 0:
            gap = (state["last"] / state["avg"] - 1) * 100
            st.markdown(
                f"**현재 상태:** 🟢 보유 중 ({state['n_buys']}/{int(sp['max_buys'])}회 매수) · "
                f"평단 ${state['avg']:.2f} · 현재가 ${state['last']:.2f} ({gap:+.1f}%)"
            )
        else:
            st.markdown("**현재 상태:** ⚪ 현금 대기")
        if len(trades):
            with st.expander(f"거래 내역 ({len(trades)}건)"):
                st.dataframe(trades.iloc[::-1], hide_index=True, use_container_width=True)
    else:
        now_sig = "🟢 보유" if sig.iloc[-1] >= 1 else "⚪ 현금"
        st.markdown(f"**오늘 기준 전략 신호:** {now_sig}")
    st.caption("세금·환율·배당 재투자 방식 등은 반영하지 않은 단순 계산입니다.")


# ════════════════════════════════════════════════
#  페이지 이동 메뉴
# ════════════════════════════════════════════════
pages = [
    st.Page(home, title="시황", icon="📈", url_path="market", default=True),
    st.Page(scanner, title="스캐너", icon="🔍", url_path="scanner"),
    st.Page(backtest, title="백테스트", icon="🧪", url_path="backtest"),
]
try:
    pg = st.navigation(pages, position="top")  # 상단 메뉴 (최신 Streamlit)
except TypeError:
    pg = st.navigation(pages)  # 구버전은 왼쪽 사이드바 메뉴
pg.run()

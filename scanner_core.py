"""볼린저밴드 하단 스캐너: 나스닥100 목록과 계산 로직"""
import streamlit as st
import yfinance as yf
import pandas as pd


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

"""백테스트 계산 로직과 차트"""
import streamlit as st
import yfinance as yf
import pandas as pd


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

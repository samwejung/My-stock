"""🧪 백테스트 페이지"""
import streamlit as st
import pandas as pd

from common import section_title
from backtest_core import (
    STRATEGIES, load_prices, run_backtest, run_scale_backtest, metrics, trade_chart,
)


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

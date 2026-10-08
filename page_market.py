"""📈 시황 페이지"""
import streamlit as st
import streamlit.components.v1 as components

from common import section_title, get_history
from fear_greed import get_fear_greed, make_cnn_html


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

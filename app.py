"""미국주식 시황 — 시작 파일 (메뉴 + 공통 설정만 담당)
페이지별 화면은 page_market.py / page_scanner.py / page_backtest.py 에 있습니다."""
import streamlit as st
import streamlit.components.v1 as components

from page_market import home
from page_scanner import scanner
from page_backtest import backtest

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

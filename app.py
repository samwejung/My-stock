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
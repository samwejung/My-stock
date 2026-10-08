"""공통 도구: 섹션 제목, 가격 조회"""
import streamlit as st
import yfinance as yf


def section_title(text):
    st.markdown(
        f'<div style="font-size:1.25rem;font-weight:600;margin:0;">{text}</div>',
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=300)  # 5분 동안 결과 재사용 (요청 횟수 절약)
def get_history(ticker, period):
    return yf.Ticker(ticker).history(period=period)

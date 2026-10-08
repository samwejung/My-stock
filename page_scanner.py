"""🔍 볼린저밴드 스캐너 페이지"""
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd

from common import section_title
from scanner_core import NASDAQ100, scan_bb_lower


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

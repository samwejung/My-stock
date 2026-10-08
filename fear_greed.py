"""공포·탐욕 지수: 데이터 조회와 CNN 스타일 게이지"""
import streamlit as st


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

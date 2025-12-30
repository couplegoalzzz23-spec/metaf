import streamlit as st
import requests
from datetime import datetime, timezone
import re
import math

# =====================================
# PAGE CONFIG
# =====================================
st.set_page_config(
    page_title="LANUD RSN Tactical METOC",
    page_icon="✈️",
    layout="wide"
)

# =====================================
# SIDEBAR CONTROL
# =====================================
with st.sidebar:
    st.header("OPS CONTROL")
    view_mode = st.radio("Mode Tampilan", ["QAM", "OPS"])
    refresh_min = st.slider("Auto Refresh (menit)", 1, 30, 5)
    auto_refresh = st.checkbox("Auto Refresh", True)
    tz_mode = st.radio("Zona Waktu", ["UTC", "WIB"])

# =====================================
# SAFE AUTO REFRESH
# =====================================
if auto_refresh:
    st.markdown(
        f"<meta http-equiv='refresh' content='{refresh_min * 60}'>",
        unsafe_allow_html=True
    )

# =====================================
# DATA SOURCE
# =====================================
METAR_URL = "https://aviationweather.gov/api/data/metar"

def fetch_metar_taf():
    params = {
        "ids": "WIBB",
        "hours": 0,
        "sep": "true",
        "taf": "true"
    }
    r = requests.get(METAR_URL, params=params, timeout=10)
    r.raise_for_status()
    return r.text.strip().split("\n")

# =====================================
# PARSING
# =====================================
def extract_wind(m):
    x = re.search(r'(\d{3})(\d{2})KT', m)
    return (int(x.group(1)), int(x.group(2))) if x else (None, None)

def extract_visibility(m):
    x = re.search(r' (\d{4}) ', m)
    return int(x.group(1)) if x else None

def extract_ceiling(m):
    if "OVC" in m:
        return "OVC"
    if "BKN" in m:
        return "BKN"
    if "SCT" in m:
        return "SCT"
    return "CLR"

# =====================================
# QAM LOGIC
# =====================================
def qam_assess(m):
    score = 0
    notes = []

    wd, ws = extract_wind(m)
    vis = extract_visibility(m)
    cld = extract_ceiling(m)

    if "TS" in m or "CB" in m:
        score += 2
        notes.append("Thunderstorm / CB")

    if vis:
        if vis < 3000:
            score += 2
            notes.append("Visibility < 3000 m")
        elif vis < 5000:
            score += 1
            notes.append("Visibility marginal")

    if ws:
        if ws > 25:
            score += 2
            notes.append("Strong wind")
        elif ws >= 15:
            score += 1
            notes.append("Moderate wind")

    if cld == "OVC":
        score += 2
        notes.append("Overcast ceiling")
    elif cld == "BKN":
        score += 1
        notes.append("Broken cloud")

    if score == 0:
        return "🟢 GO", "green", ["All parameters within limits"]

    if score <= 2:
        return "🟡 CAUTION", "orange", notes

    return "🔴 NO-GO", "red", notes

# =====================================
# OPS DETAIL
# =====================================
def runway_component(wd, ws, rwy):
    ang = math.radians(wd - rwy)
    return round(ws * math.cos(ang), 1), round(ws * math.sin(ang), 1)

# =====================================
# MAIN
# =====================================
st.title("✈️ Tactical METOC Dashboard")
st.subheader("Lanud Roesmin Nurjadin (WIBB)")

try:
    lines = fetch_metar_taf()
    metar = next(l for l in lines if l.startswith("METAR"))
    taf = next(l for l in lines if l.startswith("TAF"))

    # ===============================
    # QAM MODE
    # ===============================
    if view_mode == "QAM":
        status, color, notes = qam_assess(metar)

        st.markdown(
            f"""
            <div style="padding:25px;border-radius:12px;
            background:{color};color:white;font-size:32px;
            font-weight:bold;text-align:center;">
            {status}
            </div>
            """,
            unsafe_allow_html=True
        )

        st.subheader("Quick Assessment Matrix")
        for n in notes:
            st.warning(n)

        st.divider()
        st.code(metar)

    # ===============================
    # OPS MODE (ASLI ANDA)
    # ===============================
    else:
        status, color, alerts = qam_assess(metar)

        st.markdown(
            f"""
            <div style="padding:12px;border-radius:8px;
            background:{color};color:white;font-size:18px;font-weight:bold;">
            FLIGHT STATUS: {status}
            </div>
            """,
            unsafe_allow_html=True
        )

        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("METAR")
            st.code(metar)
        with col2:
            st.subheader("TAF")
            st.code(taf)

        st.divider()
        st.subheader("Runway Wind Component (RWY 18 / 36)")
        wd, ws = extract_wind(metar)

        if wd:
            h18, c18 = runway_component(wd, ws, 180)
            h36, c36 = runway_component(wd, ws, 360)

            c1, c2 = st.columns(2)
            with c1:
                st.metric("RWY 18 Head/Tailwind", f"{h18} kt")
                st.metric("RWY 18 Crosswind", f"{abs(c18)} kt")
            with c2:
                st.metric("RWY 36 Head/Tailwind", f"{h36} kt")
                st.metric("RWY 36 Crosswind", f"{abs(c36)} kt")

        st.divider()
        st.subheader("Satellite & Radar")

        st.image(
            "https://rammb-slider.cira.colostate.edu/data/imagery/latest/"
            "himawari-9/full_disk/ir/00/000_000.png",
            use_column_width=True
        )

        st.image(
            "https://tilecache.rainviewer.com/v2/radar/nowcast.png",
            use_column_width=True
        )

    now = datetime.now(timezone.utc)
    if tz_mode == "WIB":
        now = now.replace(hour=(now.hour + 7) % 24)

    st.caption(f"Last Update: {now.strftime('%Y-%m-%d %H:%M:%S')} {tz_mode}")

except Exception as e:
    st.error(f"ERROR: {e}")

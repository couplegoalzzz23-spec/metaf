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
    refresh_min = st.slider("Auto Refresh (menit)", 1, 30, 5)
    auto_refresh = st.checkbox("Auto Refresh", True)
    tz_mode = st.radio("Zona Waktu", ["UTC", "WIB"])

# =====================================
# SAFE AUTO REFRESH (NO MODULE)
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
    response = requests.get(METAR_URL, params=params, timeout=10)
    response.raise_for_status()
    return response.text.strip().split("\n")

# =====================================
# WEATHER LOGIC
# =====================================
def extract_wind(metar):
    match = re.search(r'(\d{3})(\d{2})KT', metar)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None, None

def assess_weather(metar):
    alerts = []

    if "TS" in metar or "CB" in metar:
        alerts.append("⛈️ Thunderstorm / CB")
    if "RA" in metar:
        alerts.append("🌧️ Rain")
    if "FG" in metar or "BR" in metar:
        alerts.append("🌫️ Low Visibility")

    _, wind_speed = extract_wind(metar)
    if wind_speed and wind_speed >= 20:
        alerts.append("💨 Strong Wind")

    if not alerts:
        return "🟢 NORMAL", "green", ["No significant weather"]

    if len(alerts) == 1:
        return "🟡 CAUTION", "orange", alerts

    return "🔴 WARNING", "red", alerts

def runway_component(wind_dir, wind_spd, runway_heading):
    angle = math.radians(wind_dir - runway_heading)
    head = round(wind_spd * math.cos(angle), 1)
    cross = round(wind_spd * math.sin(angle), 1)
    return head, cross

# =====================================
# MAIN APP
# =====================================
st.title("✈️ Tactical METOC Dashboard")
st.subheader("Lanud Roesmin Nurjadin (WIBB)")

try:
    lines = fetch_metar_taf()
    metar = next(line for line in lines if line.startswith("METAR"))
    taf = next(line for line in lines if line.startswith("TAF"))

    status, color, alerts = assess_weather(metar)

    # STATUS BAR
    st.markdown(
        f"""
        <div style="padding:12px;border-radius:8px;
        background:{color};color:white;font-size:18px;font-weight:bold;">
        FLIGHT STATUS: {status}
        </div>
        """,
        unsafe_allow_html=True
    )

    for alert in alerts:
        st.warning(alert)

    st.divider()

    # METAR / TAF
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("METAR")
        st.code(metar)
    with col2:
        st.subheader("TAF")
        st.code(taf)

    st.divider()

    # RUNWAY WIND
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
    else:
        st.info("Wind data not available")

    st.divider()

    # SATELLITE & RADAR (IMAGE ONLY)
    st.subheader("Satellite & Radar")

    st.image(
        "https://rammb-slider.cira.colostate.edu/data/imagery/latest/"
        "himawari-9/full_disk/ir/00/000_000.png",
        caption="Himawari-9 Infrared (Cloud Top Temperature)",
        use_column_width=True
    )

    st.image(
        "https://tilecache.rainviewer.com/v2/radar/nowcast.png",
        caption="Global Rain Radar (RainViewer)",
        use_column_width=True
    )

    # TIME
    now = datetime.now(timezone.utc)
    if tz_mode == "WIB":
        now = now.replace(hour=(now.hour + 7) % 24)

    st.caption(f"Last Update: {now.strftime('%Y-%m-%d %H:%M:%S')} {tz_mode}")

except Exception as e:
    st.error(f"ERROR: {e}")

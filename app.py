import streamlit as st
import requests
import re
from datetime import datetime, timezone
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="QAM METOC WIBB — OPERATION",
    page_icon="✈️",
    layout="wide"
)

# =====================================================
# DATA SOURCES (OFFICIAL / TRUSTED)
# =====================================================
METAR_API = "https://aviationweather.gov/api/data/metar"
NOAA_TAF_API = "https://aviationweather.gov/data/metar/"
BMKG_TAF_URL = "https://web-aviation.bmkg.go.id/web/taf.php"

# Satellite & Radar (BMKG)
SAT_IR_RIAU = "http://202.90.198.22/IMAGE/HIMA/H08_RP_Riau.png"
RADAR_RIAU = "https://inderaja.bmkg.go.id/IMAGE/RadarComposite.png"

# =====================================================
# FETCH METAR
# =====================================================
def fetch_metar():
    r = requests.get(METAR_API, params={"ids": "WIBB", "hours": 0}, timeout=10)
    r.raise_for_status()
    return r.text.strip()

# =====================================================
# FETCH TAF — BMKG (PRIMARY)
# =====================================================
def fetch_taf_bmkg(station="WIBB"):
    try:
        r = requests.get(BMKG_TAF_URL, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        match = re.search(rf"(TAF\s+{station}[\s\S]+?)(?:<|$)", r.text)
        if match:
            taf = re.sub(r"<[^>]+>", "", match.group(1))
            return taf.strip()
        return ""
    except Exception:
        return ""

# =====================================================
# FETCH TAF — NOAA (FALLBACK)
# =====================================================
def fetch_taf_noaa(station="WIBB"):
    r = requests.get(NOAA_TAF_API, params={"ids": station, "taf": "1"}, timeout=10)
    r.raise_for_status()
    match = re.search(rf"(TAF\s+{station}[\s\S]*)", r.text)
    return match.group(1).strip() if match else ""

# =====================================================
# METAR PARSERS
# =====================================================
def wind(m):
    x = re.search(r'(\d{3})(\d{2})KT', m)
    return f"{x.group(1)}° / {x.group(2)} kt" if x else "-"

def visibility(m):
    x = re.search(r' (\d{4}) ', m)
    return f"{x.group(1)} m" if x else "-"

def temp_dew(m):
    x = re.search(r' (M?\d{2})/(M?\d{2})', m)
    return f"{x.group(1)} / {x.group(2)} °C" if x else "-"

def qnh(m):
    x = re.search(r' Q(\d{4})', m)
    return f"{x.group(1)} hPa" if x else "-"

# =====================================================
# MAIN HEADER
# =====================================================
st.title("QAM METEOROLOGICAL REPORT")
st.subheader("Lanud Roesmin Nurjadin — WIBB")

now = datetime.now(timezone.utc).strftime("%d %b %Y %H%M UTC")

metar = fetch_metar()
taf = fetch_taf_bmkg("WIBB")
taf_source = "BMKG Web Aviation"

if not taf:
    taf = fetch_taf_noaa("WIBB")
    taf_source = "NOAA AviationWeather (Fallback)"

# =====================================================
# METAR & TAF DISPLAY
# =====================================================
st.markdown("### ✈️ METAR (RAW ICAO)")
st.code(metar)

st.markdown("### ✈️ TAFOR (RAW ICAO)")
st.caption(f"Source: {taf_source}")
st.code(taf if taf else "TAF not available")

# =====================================================
# SATELLITE — IR COLD CLOUD
# =====================================================
st.divider()
st.subheader("🛰️ Weather Satellite — Himawari-8 (Infrared)")
st.caption("Cloud Top Temperature | Reference only — NOT for tactical separation")

st.caption(f"Timestamp UTC: {now}")

try:
    r = requests.get(SAT_IR_RIAU, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()

    st.image(
        r.content,
        caption="Himawari-8 IR — Cold Cloud Detection (Riau)",
        use_container_width=True
    )

    with st.expander("🧭 Satellite Legend — Cloud Top Temperature"):
        st.markdown("""
**IR Cold Cloud Interpretation**
- 🔴 **< -70°C** → Severe convection / Cb mature
- 🟠 **-60 to -70°C** → Deep convective cloud
- 🟡 **-50 to -60°C** → Developing Cb
- 🟢 **> -40°C** → Stratiform / shallow cloud

⚠️ *Colder = higher cloud top = stronger updraft*
""")
except Exception:
    st.warning("Satellite imagery temporarily unavailable.")

# =====================================================
# WEATHER RADAR — RIAU
# =====================================================
st.divider()
st.subheader("📡 Weather Radar — Riau Composite")
st.caption("BMKG Radar Composite | Reflectivity (dBZ)")

try:
    r = requests.get(RADAR_RIAU, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()

    st.image(
        r.content,
        caption="BMKG Radar Composite — Riau",
        use_container_width=True
    )

    with st.expander("🎯 Radar Legend — Reflectivity (dBZ)"):
        st.markdown("""
**Radar Reflectivity**
- 🟢 **5–20 dBZ** → Light rain
- 🟡 **20–35 dBZ** → Moderate rain
- 🟠 **35–45 dBZ** → Heavy rain
- 🔴 **> 45 dBZ** → Severe convective / TS

⚠️ *Radar indicates precipitation intensity, NOT cloud height*
""")
except Exception:
    st.warning("Radar imagery temporarily unavailable.")

# =====================================================
# OPERATIONAL DISCLAIMER
# =====================================================
st.divider()
st.caption("""
🛑 **Operational Notice**
- Satellite & Radar imagery are for **situational awareness**
- Tactical flight decisions **MUST rely on**:
  METAR • TAF • ATC clearance • onboard radar
""")

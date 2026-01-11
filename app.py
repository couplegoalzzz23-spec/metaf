import streamlit as st
import requests
import re
from datetime import datetime, timezone
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# =====================================
# PAGE CONFIG
# =====================================
st.set_page_config(
    page_title="QAM METOC WIBB",
    page_icon="✈️",
    layout="wide"
)

# =====================================
# DATA SOURCES
# =====================================
METAR_API = "https://aviationweather.gov/api/data/metar"
NOAA_TAF_API = "https://aviationweather.gov/data/metar/"
BMKG_TAF_URL = "https://web-aviation.bmkg.go.id/web/taf.php"
SATELLITE_HIMA_RIAU = "http://202.90.198.22/IMAGE/HIMA/H08_RP_Riau.png"

# ECMWF (via Open-Meteo)
ECMWF_API = "https://api.open-meteo.com/v1/ecmwf"

# =====================================
# FETCH METAR (REALTIME)
# =====================================
def fetch_metar():
    r = requests.get(
        METAR_API,
        params={"ids": "WIBB", "hours": 0},
        timeout=10
    )
    r.raise_for_status()
    return r.text.strip()

# =====================================
# FETCH TAF — BMKG (PRIMARY)
# =====================================
def fetch_taf_bmkg(station="WIBB"):
    try:
        r = requests.get(
            BMKG_TAF_URL,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        r.raise_for_status()

        text = r.text
        match = re.search(rf"(TAF\s+{station}[\s\S]+?)(?:<|$)", text)
        if match:
            taf = re.sub(r"<[^>]+>", "", match.group(1))
            return taf.strip()
        return ""
    except Exception:
        return ""

# =====================================
# FETCH TAF — NOAA (FALLBACK)
# =====================================
def fetch_taf_noaa(station="WIBB"):
    r = requests.get(
        NOAA_TAF_API,
        params={"ids": station, "taf": "1"},
        timeout=10
    )
    r.raise_for_status()
    match = re.search(rf"(TAF\s+{station}[\s\S]*)", r.text)
    return match.group(1).strip() if match else ""

# =====================================
# ECMWF FETCH (FORECAST SUPPORT)
# =====================================
def fetch_ecmwf(lat=0.460, lon=101.445):
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "cape,cloudcover_low,cloudcover_mid,cloudcover_high",
        "timezone": "UTC"
    }
    r = requests.get(ECMWF_API, params=params, timeout=10)
    r.raise_for_status()
    return r.json()

# =====================================
# METAR PARSERS
# =====================================
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

# =====================================
# MAIN APP
# =====================================
st.title("QAM METEOROLOGICAL REPORT")
st.subheader("Lanud Roesmin Nurjadin — WIBB")

now = datetime.now(timezone.utc).strftime("%d %b %Y %H%M UTC")

metar = fetch_metar()

taf = fetch_taf_bmkg("WIBB")
taf_source = "BMKG Web Aviation"

if not taf:
    taf = fetch_taf_noaa("WIBB")
    taf_source = "NOAA AviationWeather (Fallback)"

st.code(metar)

st.divider()
st.subheader("✈️ TAFOR — Terminal Aerodrome Forecast (RAW ICAO)")
st.caption(f"Source: {taf_source}")

if taf:
    st.code(taf)
else:
    st.warning("TAF not available from BMKG or NOAA.")

# =====================================
# SATELLITE — HIMAWARI-8
# =====================================
st.divider()
st.subheader("🛰️ Weather Satellite — Himawari-8 (Infrared)")
st.caption("BMKG Himawari-8 | Reference only — not for tactical separation")

try:
    img = requests.get(SATELLITE_HIMA_RIAU, timeout=10).content
    st.image(img, use_container_width=True,
             caption="Himawari-8 IR — Cloud Top Temperature (Riau)")
except Exception:
    st.warning("Satellite imagery temporarily unavailable.")

# =====================================
# ECMWF FORECAST SUPPORT (NON-ICAO)
# =====================================
st.divider()
st.subheader("🧠 ECMWF Forecast Support (NON-ICAO)")
st.caption(
    "Numerical Weather Prediction | Reference only — "
    "NOT a replacement for METAR / TAF / SIGMET"
)

try:
    ecmwf = fetch_ecmwf()
    h = ecmwf["hourly"]

    df_ec = pd.DataFrame({
        "time": pd.to_datetime(h["time"]),
        "CAPE (J/kg)": h["cape"],
        "Low Cloud (%)": h["cloudcover_low"],
        "Mid Cloud (%)": h["cloudcover_mid"],
        "High Cloud (%)": h["cloudcover_high"]
    })

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        subplot_titles=[
            "Convective Available Potential Energy (CAPE)",
            "Cloud Cover (%)"
        ]
    )

    fig.add_trace(
        go.Scatter(x=df_ec["time"], y=df_ec["CAPE (J/kg)"],
                   name="CAPE"), 1, 1
    )

    fig.add_trace(
        go.Scatter(x=df_ec["time"], y=df_ec["Low Cloud (%)"],
                   name="Low Cloud"), 2, 1
    )
    fig.add_trace(
        go.Scatter(x=df_ec["time"], y=df_ec["High Cloud (%)"],
                   name="High Cloud"), 2, 1
    )

    fig.update_layout(
        height=650,
        hovermode="x unified"
    )

    st.plotly_chart(fig, use_container_width=True)

except Exception:
    st.warning("ECMWF forecast data unavailable.")

# =====================================
# OPERATIONAL NOTE
# =====================================
st.info(
    "⚠️ ECMWF data is FORECAST SUPPORT ONLY.\n\n"
    "Operational aviation decisions must rely on:\n"
    "• METAR / SPECI\n"
    "• TAF / TAF AMD\n"
    "• SIGMET / AIRMET\n"
    "• ATC clearance"
)

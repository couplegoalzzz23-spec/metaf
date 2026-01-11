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
BMKG_FORECAST_API = "https://api.bmkg.go.id/publik/prakiraan-cuaca"
SATELLITE_HIMA_RIAU = "http://202.90.198.22/IMAGE/HIMA/H08_RP_Riau.png"

ADM4_WIBB = "14.71.01.1001"  # Pekanbaru (adjust if required)

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
        match = re.search(rf"(TAF\s+{station}[\s\S]+?)(?:<|$)", r.text)
        return re.sub(r"<[^>]+>", "", match.group(1)).strip() if match else ""
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
# FETCH BMKG FORECAST
# =====================================
def fetch_bmkg_forecast(adm4):
    r = requests.get(
        BMKG_FORECAST_API,
        params={"adm4": adm4},
        timeout=15,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    r.raise_for_status()
    return r.json()

def parse_bmkg_forecast(js):
    rows = []
    for area in js.get("data", []):
        for c in area.get("cuaca", []):
            rows.append({
                "time": pd.to_datetime(c["local_datetime"]),
                "weather": c["weather_desc"],
                "temp": c["t"],
                "rh": c["hu"],
                "wind_kts": round(c["ws"] * 1.943, 1),
                "wind_dir": c["wd"]
            })
    return pd.DataFrame(rows)

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

def parse_numeric_metar(m):
    t = re.search(r' (\d{2})(\d{2})(\d{2})Z', m)
    if not t:
        return None

    data = {
        "time": datetime.strptime(t.group(0).strip(), "%d%H%MZ"),
        "wind": None,
        "temp": None,
        "dew": None,
        "qnh": None,
        "vis": None,
        "RA": "RA" in m,
        "TS": "TS" in m,
        "FG": "FG" in m
    }

    if w := re.search(r'(\d{3})(\d{2})KT', m):
        data["wind"] = int(w.group(2))
    if td := re.search(r' (M?\d{2})/(M?\d{2})', m):
        data["temp"] = int(td.group(1).replace("M", "-"))
        data["dew"] = int(td.group(2).replace("M", "-"))
    if q := re.search(r' Q(\d{4})', m):
        data["qnh"] = int(q.group(1))
    if v := re.search(r' (\d{4}) ', m):
        data["vis"] = int(v.group(1))

    return data

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

# =====================================
# TAF DISPLAY
# =====================================
st.divider()
st.subheader("✈️ TAFOR — Terminal Aerodrome Forecast")
st.caption(f"Source: {taf_source}")
st.code(taf if taf else "TAF not available")

# =====================================
# BMKG FORECAST PANEL
# =====================================
st.divider()
st.subheader("🌦️ BMKG Official Weather Forecast — Supplementary")
st.caption("BMKG Public API | Situational Awareness Only")

try:
    bmkg_raw = fetch_bmkg_forecast(ADM4_WIBB)
    bmkg_df = parse_bmkg_forecast(bmkg_raw)

    if not bmkg_df.empty:
        bmkg_df.sort_values("time", inplace=True)
        view = bmkg_df.head(24)
        view["UTC"] = view["time"].dt.strftime("%d %b %H:%M")
        st.dataframe(
            view[["UTC", "weather", "temp", "rh", "wind_kts", "wind_dir"]],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("BMKG forecast data empty.")

except Exception:
    st.warning("BMKG forecast unavailable.")

# =====================================
# SATELLITE
# =====================================
st.divider()
st.subheader("🛰️ Himawari-8 Infrared — Riau")

try:
    r = requests.get(SATELLITE_HIMA_RIAU, timeout=10)
    r.raise_for_status()
    st.image(r.content, use_container_width=True)
except Exception:
    st.warning("Satellite unavailable.")

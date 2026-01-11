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
SATELLITE_HIMA_RIAU = "http://202.90.198.22/IMAGE/HIMA/H08_RP_Riau.png"
BMKG_FORECAST_API = "https://api.bmkg.go.id/publik/prakiraan-cuaca?adm4=31.71.03.1001"

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
# FETCH BMKG FORECAST
# =====================================
def fetch_bmkg_forecast():
    try:
        r = requests.get(
            BMKG_FORECAST_API,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        r.raise_for_status()
        return r.json()
    except Exception:
        return None

# =====================================
# HISTORICAL METAR
# =====================================
def fetch_metar_history(hours=24):
    r = requests.get(
        METAR_API,
        params={"ids": "WIBB", "hours": hours},
        timeout=10
    )
    r.raise_for_status()
    return r.text.strip().splitlines()

def fetch_metar_ogimet(hours=24):
    end = datetime.utcnow()
    start = end - pd.Timedelta(hours=hours)

    url = "https://www.ogimet.com/display_metars2.php"
    params = {
        "lang": "en",
        "lugar": "WIBB",
        "tipo": "ALL",
        "ord": "REV",
        "nil": "NO",
        "fmt": "txt",
        "ano": start.year,
        "mes": start.month,
        "day": start.day,
        "hora": start.hour,
        "anof": end.year,
        "mesf": end.month,
        "dayf": end.day,
        "horaf": end.hour,
        "minf": end.minute
    }

    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    return [l.strip() for l in r.text.splitlines() if l.startswith("WIBB")]

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

    w = re.search(r'(\d{3})(\d{2})KT', m)
    if w:
        data["wind"] = int(w.group(2))

    td = re.search(r' (M?\d{2})/(M?\d{2})', m)
    if td:
        data["temp"] = int(td.group(1).replace("M", "-"))
        data["dew"] = int(td.group(2).replace("M", "-"))

    q = re.search(r' Q(\d{4})', m)
    if q:
        data["qnh"] = int(q.group(1))

    v = re.search(r' (\d{4}) ', m)
    if v:
        data["vis"] = int(v.group(1))

    return data

# =====================================
# MAIN APP
# =====================================
st.title("QAM METEOROLOGICAL REPORT")
st.subheader("Lanud Roesmin Nurjadin — WIBB")

now = datetime.now(timezone.utc).strftime("%d %b %Y %H%M UTC")
metar = fetch_metar()

st.code(metar)

# =====================================
# BMKG FORECAST DISPLAY
# =====================================
st.divider()
st.subheader("🌦️ Prakiraan Cuaca — BMKG (NON-ICAO)")
st.caption("BMKG Official Forecast | Reference only — NOT a replacement for METAR / TAF")

forecast = fetch_bmkg_forecast()

if forecast and "data" in forecast:
    lokasi = forecast["data"][0]
    cuaca = lokasi.get("cuaca", [])

    for slot in cuaca[:6]:  # tampilkan 6 periode ke depan
        waktu = slot.get("local_datetime", "-")
        desc = slot.get("weather_desc", "-")
        temp = slot.get("t", "-")
        rh = slot.get("hu", "-")
        wind = slot.get("ws", "-")

        st.markdown(
            f"""
            **🕒 {waktu}**  
            🌤️ Cuaca: **{desc}**  
            🌡️ Suhu: **{temp}°C**  
            💧 RH: **{rh}%**  
            💨 Angin: **{wind} km/h**
            """
        )
        st.divider()
else:
    st.warning("BMKG forecast data unavailable.")

# =====================================
# SATELLITE
# =====================================
st.divider()
st.subheader("🛰️ Weather Satellite — Himawari-8 (Infrared)")
st.caption("BMKG Himawari-8 | Reference only — not for tactical separation")

try:
    img = requests.get(
        SATELLITE_HIMA_RIAU,
        timeout=10,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    img.raise_for_status()
    st.image(img.content, use_container_width=True)
except Exception:
    st.warning("Satellite imagery temporarily unavailable.")

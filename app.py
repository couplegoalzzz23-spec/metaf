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
# FETCH METAR
# =====================================
def fetch_metar():
    r = requests.get(METAR_API, params={"ids": "WIBB", "hours": 0}, timeout=10)
    r.raise_for_status()
    return r.text.strip()

def fetch_metar_history(hours=24):
    r = requests.get(METAR_API, params={"ids": "WIBB", "hours": hours}, timeout=10)
    r.raise_for_status()
    return r.text.strip().splitlines()

def fetch_metar_ogimet(hours=24):
    end = datetime.utcnow()
    start = end - pd.Timedelta(hours=hours)
    r = requests.get(
        "https://www.ogimet.com/display_metars2.php",
        params={
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
            "minf": end.minute,
        },
        timeout=15
    )
    r.raise_for_status()
    return [l for l in r.text.splitlines() if l.startswith("WIBB")]

# =====================================
# METAR PARSER
# =====================================
def parse_numeric_metar(m):
    t = re.search(r' (\d{2})(\d{2})(\d{2})Z', m)
    if not t:
        return None

    return {
        "time": datetime.strptime(t.group(0).strip(), "%d%H%MZ"),
        "wind": int(re.search(r'(\d{3})(\d{2})KT', m).group(2)) if re.search(r'(\d{3})(\d{2})KT', m) else None,
        "temp": int(re.search(r' (M?\d{2})/', m).group(1).replace("M", "-")) if re.search(r' (M?\d{2})/', m) else None,
        "dew": int(re.search(r'/M?\d{2}', m).group(0).replace("/", "").replace("M", "-")) if re.search(r'/M?\d{2}', m) else None,
        "qnh": int(re.search(r' Q(\d{4})', m).group(1)) if re.search(r' Q(\d{4})', m) else None,
        "vis": int(re.search(r' (\d{4}) ', m).group(1)) if re.search(r' (\d{4}) ', m) else None,
        "RA": "RA" in m,
        "TS": "TS" in m,
        "FG": "FG" in m
    }

# =====================================
# FETCH BMKG FORECAST (SAFE)
# =====================================
def fetch_bmkg_forecast():
    try:
        r = requests.get(BMKG_FORECAST_API, timeout=15)
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, dict) else None
    except Exception:
        return None

# =====================================
# MAIN APP
# =====================================
st.title("QAM METEOROLOGICAL REPORT")
st.subheader("Lanud Roesmin Nurjadin — WIBB")

now = datetime.now(timezone.utc).strftime("%d %b %Y %H%M UTC")
metar = fetch_metar()
st.code(metar)

# =====================================
# SATELLITE
# =====================================
st.divider()
st.subheader("🛰️ Weather Satellite — Himawari-8 (Infrared)")
st.caption("BMKG Himawari-8 | Reference only — not for tactical separation")

try:
    img = requests.get(SATELLITE_HIMA_RIAU, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
    img.raise_for_status()
    st.image(img.content, use_container_width=True)
except Exception:
    st.warning("Satellite imagery temporarily unavailable.")

# =====================================
# BMKG FORECAST (FAIL SAFE)
# =====================================
st.divider()
st.subheader("🌦️ Prakiraan Cuaca — BMKG (NON-ICAO)")
st.caption("BMKG Official Forecast | Reference only — NOT a replacement for METAR / TAF")

forecast = fetch_bmkg_forecast()

if forecast and "data" in forecast and isinstance(forecast["data"], list) and forecast["data"]:
    lokasi = forecast["data"][0]
    cuaca = lokasi.get("cuaca", [])

    if isinstance(cuaca, list) and cuaca:
        for slot in cuaca[:6]:
            st.markdown(
                f"""
                **🕒 {slot.get("local_datetime","-")}**  
                🌤️ Cuaca: **{slot.get("weather_desc","-")}**  
                🌡️ Suhu: **{slot.get("t","-")}°C**  
                💧 RH: **{slot.get("hu","-")}%**  
                💨 Angin: **{slot.get("ws","-")} km/h**
                """
            )
            st.divider()
    else:
        st.info("BMKG forecast tersedia, namun detail cuaca belum dirilis.")
else:
    st.info("BMKG forecast sementara tidak tersedia.")

# =====================================
# METEOGRAM (TIDAK TERGANGGU BMKG)
# =====================================
st.divider()
st.subheader("📊 Historical METAR Meteogram — Last 24h")

raw = fetch_metar_history(24)
if len(raw) < 2:
    raw = fetch_metar_ogimet(24)

df = pd.DataFrame([parse_numeric_metar(m) for m in raw if parse_numeric_metar(m)])

if not df.empty:
    df.sort_values("time", inplace=True)

    fig = make_subplots(rows=5, cols=1, shared_xaxes=True)
    fig.add_trace(go.Scatter(x=df["time"], y=df["temp"], name="Temp"), 1, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["dew"], name="Dew"), 1, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["wind"], name="Wind"), 2, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["qnh"], name="QNH"), 3, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["vis"], name="Visibility"), 4, 1)

    fig.update_layout(height=900, hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

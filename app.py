import streamlit as st
import requests
from datetime import datetime, timezone
import re
import pandas as pd
from bs4 import BeautifulSoup
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
TAF_BMKG_URL = "https://web-aviation.bmkg.go.id/web/taf.php"

# =====================================
# FETCH METAR (NOAA)
# =====================================
def fetch_metar():
    r = requests.get(
        METAR_API,
        params={"ids": "WIBB"},
        timeout=10
    )
    r.raise_for_status()
    for l in r.text.splitlines():
        if l.startswith("METAR") or l.startswith("SPECI") or l.startswith("WIBB"):
            return l.strip()
    return ""

# =====================================
# FETCH TAF FROM BMKG (HTML SCRAPE)
# =====================================
def fetch_taf_bmkg(station="WIBB"):
    try:
        r = requests.get(TAF_BMKG_URL, timeout=15)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text("\n")

        match = re.search(rf"(TAF\s+{station}[\s\S]+?)(?:\n\n|\Z)", text)
        return match.group(1).strip() if match else ""
    except Exception:
        return ""

# =====================================
# FETCH TAF FROM NOAA (FALLBACK)
# =====================================
def fetch_taf_noaa(station="WIBB"):
    r = requests.get(
        "https://aviationweather.gov/data/metar/",
        params={"ids": station, "taf": "1"},
        timeout=10
    )
    r.raise_for_status()
    match = re.search(rf"(TAF\s+{station}[\s\S]*)", r.text)
    return match.group(1).strip() if match else ""

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
    return r.text.splitlines()

# =====================================
# METAR NUMERIC PARSER
# =====================================
def parse_numeric_metar(m):
    t = re.search(r' (\d{2})(\d{2})(\d{2})Z', m)
    if not t:
        return None

    data = {
        "time": datetime.strptime(t.group(0).strip(), "%d%H%MZ"),
        "temp": None,
        "dew": None,
        "wind": None,
        "qnh": None,
        "vis": None
    }

    if td := re.search(r' (M?\d{2})/(M?\d{2})', m):
        data["temp"] = int(td.group(1).replace("M", "-"))
        data["dew"] = int(td.group(2).replace("M", "-"))

    if w := re.search(r'(\d{3})(\d{2})KT', m):
        data["wind"] = int(w.group(2))

    if q := re.search(r' Q(\d{4})', m):
        data["qnh"] = int(q.group(1))

    if v := re.search(r' (\d{4}) ', m):
        data["vis"] = int(v.group(1))

    return data

# =====================================
# MAIN APP
# =====================================
st.title("QAM METEOROLOGICAL REPORT")
st.subheader("Lanud Roesmin Nurjadin (WIBB)")

now = datetime.now(timezone.utc).strftime("%d %b %Y %H%M UTC")
st.caption(f"UTC Time: {now}")

# -------------------------------------
# METAR
# -------------------------------------
metar = fetch_metar()
st.divider()
st.subheader("🟢 CURRENT METAR (RAW)")
st.code(metar)

# -------------------------------------
# TAF (BMKG PRIMARY)
# -------------------------------------
st.divider()
st.subheader("✈️ TAFOR — Terminal Aerodrome Forecast (RAW ICAO)")

taf = fetch_taf_bmkg("WIBB")
source = "BMKG Web Aviation"

if not taf:
    taf = fetch_taf_noaa("WIBB")
    source = "NOAA AviationWeather (Fallback)"

if taf:
    st.caption(f"Source: {source}")
    st.code(taf)
else:
    st.warning("TAF not available from BMKG or NOAA at this time.")

# -------------------------------------
# HISTORICAL METEOGRAM
# -------------------------------------
st.divider()
st.subheader("📊 Historical METAR Meteogram — Last 24h")

raw = fetch_metar_history(24)
records = [parse_numeric_metar(m) for m in raw]
df = pd.DataFrame([r for r in records if r])

if not df.empty:
    df.sort_values("time", inplace=True)

    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True,
        subplot_titles=[
            "Temperature / Dew Point (°C)",
            "Wind Speed (kt)",
            "QNH (hPa)",
            "Visibility (m)"
        ]
    )

    fig.add_trace(go.Scatter(x=df["time"], y=df["temp"], name="Temp"), 1, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["dew"], name="Dew"), 1, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["wind"], name="Wind"), 2, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["qnh"], name="QNH"), 3, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["vis"], name="Visibility"), 4, 1)

    fig.update_layout(height=850, hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

import streamlit as st
import requests
from datetime import datetime, timezone
import re
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# =====================================
# PAGE CONFIG (ONLY ONCE)
# =====================================
st.set_page_config(
    page_title="QAM METOC WIBB",
    page_icon="✈️",
    layout="wide"
)

# =====================================
# DATA SOURCES (OFFICIAL)
# =====================================
METAR_API = "https://aviationweather.gov/api/data/metar"
TAF_LEGACY_API = "https://aviationweather.gov/data/metar/"

# =====================================
# FETCH METAR + TAF (PRIMARY)
# =====================================
def fetch_metar_and_taf():
    r = requests.get(
        METAR_API,
        params={
            "ids": "WIBB",
            "include_taf": "yes"
        },
        timeout=10
    )
    r.raise_for_status()

    lines = [l.strip() for l in r.text.splitlines() if l.strip()]

    metar = ""
    taf_lines = []

    for l in lines:
        if (l.startswith("METAR") or l.startswith("SPECI") or l.startswith("WIBB")) and not metar:
            metar = l
        elif l.startswith("TAF"):
            taf_lines.append(l)
        elif taf_lines:
            taf_lines.append(l)

    taf = "\n".join(taf_lines)
    return metar, taf.strip()

# =====================================
# FETCH TAF ONLY (FALLBACK)
# =====================================
def fetch_taf_only(station="WIBB"):
    r = requests.get(
        TAF_LEGACY_API,
        params={"ids": station, "taf": "1"},
        timeout=10
    )
    r.raise_for_status()

    text = r.text.strip()
    match = re.search(rf"(TAF\s+{station}[\s\S]*)", text)
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
# MAIN APP — QAM METOC
# =====================================
st.title("QAM METEOROLOGICAL REPORT")
st.subheader("Lanud Roesmin Nurjadin (WIBB)")

now = datetime.now(timezone.utc).strftime("%d %b %Y %H%M UTC")

metar, taf_primary = fetch_metar_and_taf()
taf = taf_primary if taf_primary else fetch_taf_only("WIBB")

st.caption(f"UTC Time: {now} | Source: NOAA / AviationWeather.gov")

st.divider()
st.subheader("🟢 CURRENT METAR (RAW)")
st.code(metar)

# =====================================
# TAFOR PANEL (FINAL, VERIFIED)
# =====================================
st.divider()
st.subheader("✈️ TAFOR — Terminal Aerodrome Forecast (RAW ICAO)")

if taf:
    st.caption("Official ICAO TAF | NOAA / FAA")
    st.code(taf)
else:
    st.warning("TAF not issued for WIBB at this time.")

# =====================================
# HISTORICAL METEOGRAM
# =====================================
st.divider()
st.subheader("📊 Historical METAR Meteogram — Last 24h")

raw = fetch_metar_history(24)
source = "AviationWeather.gov"

if not raw or len(raw) < 2:
    raw = fetch_metar_ogimet(24)
    source = "OGIMET Archive"

records = [parse_numeric_metar(m) for m in raw]
df = pd.DataFrame([r for r in records if r])

st.caption(f"Data source: {source} | Records: {len(df)}")

if not df.empty:
    df.sort_values("time", inplace=True)

    fig = make_subplots(
        rows=5, cols=1, shared_xaxes=True,
        subplot_titles=[
            "Temperature / Dew Point (°C)",
            "Wind Speed (kt)",
            "QNH (hPa)",
            "Visibility (m)",
            "Weather Flags (RA / TS / FG)"
        ]
    )

    fig.add_trace(go.Scatter(x=df["time"], y=df["temp"], name="Temp"), 1, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["dew"], name="Dew"), 1, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["wind"], name="Wind"), 2, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["qnh"], name="QNH"), 3, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["vis"], name="Visibility"), 4, 1)

    fig.add_trace(go.Scatter(x=df["time"], y=df["RA"].astype(int), mode="markers", name="RA"), 5, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["TS"].astype(int), mode="markers", name="TS"), 5, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["FG"].astype(int), mode="markers", name="FG"), 5, 1)

    fig.update_layout(height=950, hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

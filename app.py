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

# Satellite sources (Riau focus)
SAT_HIMAWARI_RIAU_BMKG = "http://202.90.198.22/IMAGE/HIMA/H08_RP_Riau.png"
SAT_HIMAWARI_IR_NOAA = "https://rammb-slider.cira.colostate.edu/data/imagery/latest/himawari-8/full_disk/ir/07/20260111/ir_07_20260111_0430.jpg"

HEADERS = {"User-Agent": "Mozilla/5.0"}

# =====================================
# FETCH METAR
# =====================================
def fetch_metar():
    r = requests.get(
        METAR_API,
        params={"ids": "WIBB", "hours": 0},
        timeout=10
    )
    r.raise_for_status()
    return r.text.strip()

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
# HEADER
# =====================================
st.title("✈️ QAM METEOROLOGICAL REPORT")
st.caption("Lanud Roesmin Nurjadin — WIBB | Operational METOC Display")

# =====================================
# MAIN LAYOUT
# =====================================
left, right = st.columns([1.1, 1.4])

# =====================================
# LEFT — METAR BRIEFING
# =====================================
with left:
    st.subheader("🧾 Current METAR Briefing")

    metar = fetch_metar()
    now = datetime.now(timezone.utc).strftime("%d %b %Y %H%M UTC")

    st.markdown(
        f"""
        **Date / Time (UTC)** : {now}  
        **Surface Wind**     : {wind(metar)}  
        **Visibility**       : {visibility(metar)}  
        **Temp / Dew**       : {temp_dew(metar)}  
        **QNH**              : {qnh(metar)}
        """
    )

    st.code(metar)

# =====================================
# RIGHT — SATELLITE RIAU
# =====================================
with right:
    st.subheader("🛰️ Weather Satellite — Riau Sector (Infrared)")
    st.caption("Himawari-8 IR | Cloud Top Temperature | Reference only")

    sat_loaded = False

    try:
        r = requests.get(SAT_HIMAWARI_RIAU_BMKG, timeout=10, headers=HEADERS)
        r.raise_for_status()
        st.image(r.content, caption="BMKG Himawari-8 IR — Riau", use_container_width=True)
        sat_loaded = True
    except Exception:
        pass

    if not sat_loaded:
        try:
            r = requests.get(SAT_HIMAWARI_IR_NOAA, timeout=10, headers=HEADERS)
            r.raise_for_status()
            st.image(r.content, caption="NOAA Himawari-8 IR (Fallback)", use_container_width=True)
        except Exception:
            st.warning("Satellite imagery temporarily unavailable.")

# =====================================
# METEOGRAM
# =====================================
st.divider()
st.subheader("📊 Historical METAR Meteogram — Last 24 Hours")

raw = fetch_metar_history(24)
source = "AviationWeather.gov"

if not raw or len(raw) < 2:
    raw = fetch_metar_ogimet(24)
    source = "OGIMET Archive"

df = pd.DataFrame([parse_numeric_metar(m) for m in raw if parse_numeric_metar(m)])
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

    fig.update_layout(height=900, hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

# =====================================
# EXPORT
# =====================================
st.divider()
st.subheader("📥 Download Historical METAR Data")

if not df.empty:
    df["time"] = df["time"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    st.download_button("⬇️ Download CSV", df.to_csv(index=False), "WIBB_METAR_24H.csv")
    st.download_button("⬇️ Download JSON", df.to_json(orient="records"), "WIBB_METAR_24H.json")

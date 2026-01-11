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
# GLOBAL STYLE
# =====================================
st.markdown("""
<style>
h1, h2, h3 { font-weight: 700; }
.block-container { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)

# =====================================
# DATA SOURCES
# =====================================
METAR_API = "https://aviationweather.gov/api/data/metar"
NOAA_TAF_API = "https://aviationweather.gov/data/metar/"
BMKG_TAF_URL = "https://web-aviation.bmkg.go.id/web/taf.php"
SATELLITE_HIMA_RIAU = "http://202.90.198.22/IMAGE/HIMA/H08_RP_Riau.png"

# =====================================
# FETCH FUNCTIONS
# =====================================
def fetch_metar():
    r = requests.get(METAR_API, params={"ids": "WIBB", "hours": 0}, timeout=10)
    r.raise_for_status()
    return r.text.strip()

def fetch_taf_bmkg(station="WIBB"):
    try:
        r = requests.get(BMKG_TAF_URL, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        match = re.search(rf"(TAF\s+{station}[\s\S]+?)(?:<|$)", r.text)
        return re.sub(r"<[^>]+>", "", match.group(1)).strip() if match else ""
    except Exception:
        return ""

def fetch_taf_noaa(station="WIBB"):
    r = requests.get(NOAA_TAF_API, params={"ids": station, "taf": "1"}, timeout=10)
    r.raise_for_status()
    match = re.search(rf"(TAF\s+{station}[\s\S]*)", r.text)
    return match.group(1).strip() if match else ""

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
            "lang": "en", "lugar": "WIBB", "tipo": "ALL",
            "ord": "REV", "nil": "NO", "fmt": "txt",
            "ano": start.year, "mes": start.month, "day": start.day,
            "hora": start.hour, "anof": end.year, "mesf": end.month,
            "dayf": end.day, "horaf": end.hour, "minf": end.minute
        },
        timeout=15
    )
    r.raise_for_status()
    return [l for l in r.text.splitlines() if l.startswith("WIBB")]

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
        "wind": None, "temp": None, "dew": None,
        "qnh": None, "vis": None,
        "RA": "RA" in m, "TS": "TS" in m, "FG": "FG" in m
    }
    for k, p in {
        "wind": r'(\d{3})(\d{2})KT',
        "qnh": r' Q(\d{4})',
        "vis": r' (\d{4}) '
    }.items():
        x = re.search(p, m)
        if x:
            data[k] = int(x.group(2) if k == "wind" else x.group(1))
    td = re.search(r' (M?\d{2})/(M?\d{2})', m)
    if td:
        data["temp"] = int(td.group(1).replace("M", "-"))
        data["dew"] = int(td.group(2).replace("M", "-"))
    return data

# =====================================
# SIDEBAR MENU
# =====================================
menu = st.sidebar.radio(
    "🧭 MENU",
    ["🏠 Home", "📄 QAM Report", "✈️ METAR & TAF", "🛰️ Satellite", "📊 Meteogram", "📥 Data Export"]
)

# =====================================
# DATA LOAD
# =====================================
now = datetime.now(timezone.utc).strftime("%d %b %Y %H%M UTC")
metar = fetch_metar()
taf = fetch_taf_bmkg() or fetch_taf_noaa()

raw = fetch_metar_history(24)
if len(raw) < 2:
    raw = fetch_metar_ogimet(24)

df = pd.DataFrame([parse_numeric_metar(m) for m in raw if parse_numeric_metar(m)])

# =====================================
# HOME
# =====================================
if menu == "🏠 Home":
    st.title("QAM METOC OPERATIONS DASHBOARD")
    st.subheader("Lanud Roesmin Nurjadin — WIBB")
    st.info("""
**Operational Aviation Weather Information**

✔ METAR / TAF (ICAO)  
✔ Satellite (Situational Awareness)  
✔ Historical Meteogram  
✔ QAM PDF Generator  

⚠️ Tactical decisions must rely on official ICAO products & ATC clearance.
""")

# =====================================
# QAM REPORT
# =====================================
elif menu == "📄 QAM Report":
    st.subheader("📄 QAM Meteorological Report")
    qam = [
        "METEOROLOGICAL REPORT (QAM)",
        f"DATE / TIME (UTC) : {now}",
        "AERODROME        : WIBB",
        f"SURFACE WIND     : {wind(metar)}",
        f"VISIBILITY       : {visibility(metar)}",
        f"TEMP / DEWPOINT  : {temp_dew(metar)}",
        f"QNH              : {qnh(metar)}",
        "", "RAW METAR:", metar
    ]
    st.code("\n".join(qam))

# =====================================
# METAR & TAF
# =====================================
elif menu == "✈️ METAR & TAF":
    st.subheader("✈️ METAR")
    st.code(metar)
    st.subheader("✈️ TAF")
    st.code(taf)

# =====================================
# SATELLITE
# =====================================
elif menu == "🛰️ Satellite":
    st.subheader("🛰️ Himawari-8 Infrared — Riau")
    try:
        img = requests.get(SATELLITE_HIMA_RIAU, timeout=10)
        img.raise_for_status()
        st.image(img.content, use_container_width=True)
    except Exception:
        st.warning("Satellite imagery unavailable.")

# =====================================
# METEOGRAM
# =====================================
elif menu == "📊 Meteogram":
    st.subheader("📊 METAR Meteogram (24h)")
    if not df.empty:
        df.sort_values("time", inplace=True)
        fig = make_subplots(rows=5, cols=1, shared_xaxes=True)
        fig.add_trace(go.Scatter(x=df["time"], y=df["temp"], name="Temp"), 1, 1)
        fig.add_trace(go.Scatter(x=df["time"], y=df["dew"], name="Dew"), 1, 1)
        fig.add_trace(go.Scatter(x=df["time"], y=df["wind"], name="Wind"), 2, 1)
        fig.add_trace(go.Scatter(x=df["time"], y=df["qnh"], name="QNH"), 3, 1)
        fig.add_trace(go.Scatter(x=df["time"], y=df["vis"], name="Vis"), 4, 1)
        st.plotly_chart(fig, use_container_width=True)

# =====================================
# EXPORT
# =====================================
elif menu == "📥 Data Export":
    st.subheader("📥 Download Data")
    if not df.empty:
        df2 = df.copy()
        df2["time"] = df2["time"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        st.download_button("⬇️ CSV", df2.to_csv(index=False), "WIBB_METAR_24H.csv")
        st.download_button("⬇️ JSON", df2.to_json(orient="records"), "WIBB_METAR_24H.json")

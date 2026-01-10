# ==========================================================
# QAM METOC WIBB — OPERATIONAL WEATHER AWARENESS SYSTEM
# ==========================================================

import streamlit as st
import requests
from datetime import datetime, timezone
import re
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from PIL import Image, ImageDraw
import io

# ==========================================================
# PAGE CONFIG
# ==========================================================
st.set_page_config(
    page_title="QAM METOC WIBB — OPS",
    page_icon="✈️",
    layout="wide"
)

# ==========================================================
# CONSTANTS
# ==========================================================
WIBB_LAT = 0.4608
WIBB_LON = 101.4445
RADIUS_NM = 100

METAR_URL = "https://aviationweather.gov/api/data/metar"

# ==========================================================
# IMAGE OVERLAY UTIL
# ==========================================================
def overlay_info(image_bytes, title):
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    draw = ImageDraw.Draw(img)

    ts = datetime.utcnow().strftime("%d %b %Y %H:%M UTC")
    text = (
        f"{title}\n"
        f"{ts}\n"
        f"WIBB ±{RADIUS_NM} NM\n"
        "REFERENCE ONLY"
    )

    draw.rectangle((10, 10, 420, 120), fill=(0, 0, 0, 180))
    draw.text((20, 20), text, fill="white")
    return img

# ==========================================================
# FETCH METAR + TAF (OFFICIAL NOAA)
# ==========================================================
def fetch_metar_and_taf():
    r = requests.get(
        METAR_URL,
        params={"ids": "WIBB", "include_taf": "yes"},
        timeout=10
    )
    r.raise_for_status()

    lines = [l.strip() for l in r.text.splitlines() if l.strip()]
    metar = ""
    taf_lines = []

    for l in lines:
        if not metar and l.startswith("WIBB"):
            metar = l
        elif l.startswith("TAF"):
            taf_lines.append(l)
        elif taf_lines:
            taf_lines.append(l)

    return metar, "\n".join(taf_lines)

# ==========================================================
# HISTORICAL METAR
# ==========================================================
def fetch_metar_history(hours=24):
    r = requests.get(
        METAR_URL,
        params={"ids": "WIBB", "hours": hours},
        timeout=10
    )
    r.raise_for_status()
    return r.text.splitlines()

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
    return [l for l in r.text.splitlines() if l.startswith("WIBB")]

# ==========================================================
# METAR NUMERIC PARSER
# ==========================================================
def parse_numeric_metar(m):
    t = re.search(r' (\d{2})(\d{2})(\d{2})Z', m)
    if not t:
        return None

    d = {
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
        d["wind"] = int(w.group(2))
    if td := re.search(r' (M?\d{2})/(M?\d{2})', m):
        d["temp"] = int(td.group(1).replace("M", "-"))
        d["dew"] = int(td.group(2).replace("M", "-"))
    if q := re.search(r' Q(\d{4})', m):
        d["qnh"] = int(q.group(1))
    if v := re.search(r' (\d{4}) ', m):
        d["vis"] = int(v.group(1))

    return d

# ==========================================================
# OPS CONVECTIVE THREAT ENGINE
# ==========================================================
def assess_convective_threat(metar):
    reasons = []
    threat = "LOW"

    if "TS" in metar:
        threat = "HIGH"
        reasons.append("METAR indicates Thunderstorm")
    elif "RA" in metar:
        threat = "MODERATE"
        reasons.append("METAR indicates Rain")

    reasons.append("Himawari-8 IR cold cloud monitoring")

    return threat, reasons

# ==========================================================
# MAIN UI
# ==========================================================
st.title("QAM METOC — OPERATIONAL WEATHER AWARENESS")
st.subheader("Lanud Roesmin Nurjadin (WIBB)")

metar, taf = fetch_metar_and_taf()
now = datetime.now(timezone.utc).strftime("%d %b %Y %H%M UTC")

st.markdown(f"""
**DATE/TIME (UTC):** {now}  
**AERODROME:** WIBB  
""")

st.code(metar if metar else "METAR unavailable")

st.subheader("✈️ TAFOR — RAW ICAO")
if taf.strip():
    st.code(taf)
else:
    st.info("TAF not issued for WIBB at this time.")

# ==========================================================
# OPS DECISION PANEL
# ==========================================================
st.divider()
st.subheader("🧠 OPS WEATHER DECISION SUPPORT")

cb_threat, cb_reasons = assess_convective_threat(metar)

col1, col2 = st.columns(2)
with col1:
    st.metric("Convective Threat", cb_threat)
with col2:
    if cb_threat == "HIGH":
        st.error("🔴 HIGH WEATHER RISK")
    elif cb_threat == "MODERATE":
        st.warning("🟡 MODERATE WEATHER RISK")
    else:
        st.success("🟢 LOW WEATHER RISK")

with st.expander("Assessment Basis"):
    for r in cb_reasons:
        st.markdown(f"- {r}")

# ==========================================================
# METEOGRAM
# ==========================================================
st.divider()
st.subheader("📊 Historical METAR Meteogram (24h)")

raw = fetch_metar_history(24)
source = "AviationWeather.gov"
if len(raw) < 2:
    raw = fetch_metar_ogimet(24)
    source = "OGIMET Archive"

df = pd.DataFrame([parse_numeric_metar(m) for m in raw if parse_numeric_metar(m)])

st.caption(f"Source: {source} | Records: {len(df)}")

if not df.empty:
    df.sort_values("time", inplace=True)
    fig = make_subplots(rows=5, cols=1, shared_xaxes=True)

    fig.add_trace(go.Scatter(x=df["time"], y=df["temp"], name="Temp"), 1, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["dew"], name="Dew"), 1, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["wind"], name="Wind"), 2, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["qnh"], name="QNH"), 3, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["vis"], name="Vis"), 4, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["TS"].astype(int), mode="markers", name="TS"), 5, 1)

    fig.update_layout(height=900, hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

# ==========================================================
# SATELLITE & RADAR
# ==========================================================
st.divider()
st.subheader("🛰️ Satellite & Radar (Riau)")

SAT_URL = "https://inderaja.bmkg.go.id/IMAGE/HIMA/H08_EH_Indonesia.png"
RADAR_URLS = [
    "https://inderaja.bmkg.go.id/IMAGE/Radar/Radar_Pekanbaru.png",
    "https://inderaja.bmkg.go.id/IMAGE/Radar/Radar_PKU.png"
]

try:
    r = requests.get(SAT_URL, timeout=10)
    st.image(overlay_info(r.content, "Himawari-8 IR Enhanced"), use_container_width=True)
except:
    st.warning("Satellite unavailable")

radar_ok = False
for url in RADAR_URLS:
    try:
        r = requests.get(url, timeout=10)
        if len(r.content) > 5000:
            st.image(overlay_info(r.content, "Weather Radar — Pekanbaru"), use_container_width=True)
            radar_ok = True
            break
    except:
        pass

if not radar_ok:
    st.warning("Weather radar Pekanbaru currently unavailable.")

# ==========================================================
# EXPORT
# ==========================================================
st.divider()
st.subheader("📥 Download Historical METAR Data")

if not df.empty:
    df["time"] = df["time"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    st.download_button("⬇️ CSV", df.to_csv(index=False), "WIBB_METAR_24H.csv")
    st.download_button("⬇️ JSON", df.to_json(orient="records"), "WIBB_METAR_24H.json")

# ==========================================================
# DISCLAIMER
# ==========================================================
st.divider()
st.caption(
    "⚠️ OPERATIONAL NOTICE\n\n"
    "This system provides meteorological situational awareness only.\n"
    "Operational decisions must rely on METAR, TAF, ATC clearance, and pilot judgment.\n"
    "Not for tactical separation."
)

import streamlit as st
import requests
from datetime import datetime, timezone
import re
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from PIL import Image, ImageDraw
import io

# =====================================
# PAGE CONFIG
# =====================================
st.set_page_config(
    page_title="QAM METOC WIBB",
    page_icon="✈️",
    layout="wide"
)

# =====================================
# GEO REFERENCE WIBB
# =====================================
WIBB_LAT = 0.4608
WIBB_LON = 101.4445
RADIUS_NM = 100

# =====================================
# DATA SOURCE
# =====================================
METAR_URL = "https://aviationweather.gov/api/data/metar"

# =====================================
# IMAGE OVERLAY UTIL
# =====================================
def overlay_info(image_bytes, title=""):
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    draw = ImageDraw.Draw(img)
    ts = datetime.utcnow().strftime("%d %b %Y %H:%M UTC")

    text = (
        f"{title}\n"
        f"{ts}\n"
        f"WIBB Radius ±{RADIUS_NM} NM\n"
        "REFERENCE ONLY"
    )

    draw.rectangle((10, 10, 380, 110), fill=(0, 0, 0, 180))
    draw.text((20, 20), text, fill="white")

    return img

# =====================================
# FETCH METAR + TAF
# =====================================
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

# =====================================
# HISTORICAL METAR
# =====================================
def fetch_metar_history(hours=24):
    r = requests.get(
        METAR_URL,
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
    return [l for l in r.text.splitlines() if l.startswith("WIBB")]

# =====================================
# METAR PARSER
# =====================================
def parse_numeric_metar(m):
    t = re.search(r' (\d{2})(\d{2})(\d{2})Z', m)
    if not t:
        return None

    data = {
        "time": datetime.strptime(t.group(0).strip(), "%d%H%MZ"),
        "wind": None,
        "wind_dir": None,
        "temp": None,
        "dew": None,
        "qnh": None,
        "vis": None,
        "RA": "RA" in m,
        "TS": "TS" in m,
        "FG": "FG" in m
    }

    if w := re.search(r'(\d{3})(\d{2})KT', m):
        data["wind_dir"] = int(w.group(1))
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
# MAIN — QAM
# =====================================
st.title("QAM METEOROLOGICAL REPORT")
st.subheader("Lanud Roesmin Nurjadin — WIBB")

metar, taf = fetch_metar_and_taf()
now = datetime.now(timezone.utc).strftime("%d %b %Y %H%M UTC")

st.markdown(f"""
**DATE / TIME (UTC):** {now}  
**AERODROME:** WIBB  
""")

st.code(metar if metar else "METAR not available")

st.subheader("✈️ TAFOR — Terminal Aerodrome Forecast (RAW ICAO)")
if taf.strip():
    st.caption("Official ICAO TAF — AviationWeather.gov")
    st.code(taf)
else:
    st.info("TAF not issued for WIBB at this time.")

# =====================================
# METEOGRAM
# =====================================
st.divider()
st.subheader("📊 Historical METAR Meteogram — Last 24h")

raw = fetch_metar_history(24)
source = "AviationWeather.gov"

if len(raw) < 2:
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

# =====================================
# SATELLITE & RADAR
# =====================================
st.divider()
st.subheader("🛰️ Satellite & Radar — Riau")

HIMAWARI = "https://inderaja.bmkg.go.id/IMAGE/HIMA/H08_EH_Indonesia.png"
RADAR = "https://inderaja.bmkg.go.id/IMAGE/Radar/Radar_Pekanbaru.png"

for title, url in [
    ("Himawari-8 IR Enhanced", HIMAWARI),
    ("Weather Radar — Pekanbaru", RADAR)
]:
    try:
        r = requests.get(url, timeout=10)
        img = overlay_info(r.content, title)
        st.image(img, use_container_width=True)
    except:
        st.warning(f"{title} unavailable")

# =====================================
# EXPORT
# =====================================
st.divider()
st.subheader("📥 Download Historical METAR Data")

if not df.empty:
    df_export = df.copy()
    df_export["time"] = df_export["time"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    st.download_button(
        "⬇️ Download CSV",
        df_export.to_csv(index=False),
        "WIBB_METAR_24H.csv",
        "text/csv"
    )

    st.download_button(
        "⬇️ Download JSON",
        df_export.to_json(orient="records"),
        "WIBB_METAR_24H.json",
        "application/json"
    )

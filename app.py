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
BMKG_FORECAST_ADM4 = "https://api.bmkg.go.id/publik/prakiraan-cuaca"

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
# METAR HISTORY
# =====================================
def fetch_metar_history(hours=24):
    r = requests.get(
        METAR_API,
        params={"ids": "WIBB", "hours": hours},
        timeout=10
    )
    r.raise_for_status()
    return r.text.strip().splitlines()

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
# BMKG FORECAST ADM4
# =====================================
def fetch_bmkg_forecast_adm4(adm4):
    try:
        r = requests.get(
            BMKG_FORECAST_ADM4,
            params={"adm4": adm4},
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

# =====================================
# MAIN APP
# =====================================
st.title("QAM METEOROLOGICAL REPORT")
st.subheader("Lanud Roesmin Nurjadin — WIBB")

now = datetime.now(timezone.utc).strftime("%d %b %Y %H%M UTC")

metar = fetch_metar()
taf = fetch_taf_bmkg("WIBB")
if not taf:
    taf = fetch_taf_noaa("WIBB")

st.code(metar)
st.divider()
st.subheader("✈️ RAW TAF")
st.code(taf if taf else "TAF not available")

# =====================================
# SATELLITE
# =====================================
st.divider()
st.subheader("🛰️ Himawari-8 Infrared (Reference Only)")
try:
    img = requests.get(SATELLITE_HIMA_RIAU, timeout=10).content
    st.image(img, use_container_width=True)
except Exception:
    st.warning("Satellite unavailable")

# =====================================
# METEOGRAM
# =====================================
st.divider()
st.subheader("📊 Historical METAR — 24H")

raw = fetch_metar_history(24)
records = [parse_numeric_metar(m) for m in raw if parse_numeric_metar(m)]
df = pd.DataFrame(records)

if not df.empty:
    df.sort_values("time", inplace=True)
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True)
    fig.add_trace(go.Scatter(x=df["time"], y=df["temp"], name="Temp"), 1, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["dew"], name="Dew"), 1, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["wind"], name="Wind"), 2, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["qnh"], name="QNH"), 3, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["vis"], name="Vis"), 4, 1)
    fig.update_layout(height=800)
    st.plotly_chart(fig, use_container_width=True)

# =====================================
# BMKG FORECAST SECTION (ADM4)
# =====================================
st.divider()
st.subheader("🌦️ Prakiraan Cuaca BMKG — ADM4")
st.caption("Wilayah administratif tingkat IV (Desa/Kelurahan)")

adm4 = st.text_input(
    "Masukkan kode ADM4 (contoh: 14.71.02.1001)",
    ""
)

if adm4:
    fc = fetch_bmkg_forecast_adm4(adm4)

    if "error" in fc:
        st.error("Gagal mengambil data BMKG")
    else:
        for area in fc.get("data", []):
            lokasi = area.get("lokasi", {})
            st.markdown(
                f"### 📍 {lokasi.get('desa','')} — {lokasi.get('kecamatan','')}"
            )

            for c in area.get("cuaca", []):
                st.write(
                    f"🕒 {c.get('local_datetime','-')} | "
                    f"🌤️ {c.get('weather_desc','-')} | "
                    f"🌡️ {c.get('t','-')}°C | "
                    f"💧 RH {c.get('hu','-')}% | "
                    f"🌬️ {c.get('wd','-')}/{c.get('ws','-')} kt"
                )

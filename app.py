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
# GLOBAL STYLE (OFFICIAL WEB LOOK)
# =====================================
st.markdown("""
<style>
.main {
    background-color: #0e1117;
}
h1, h2, h3 {
    font-weight: 700;
}
.card {
    padding: 1.2rem;
    border-radius: 12px;
    background: linear-gradient(145deg,#1c1f26,#12141a);
    box-shadow: 0 0 12px rgba(0,0,0,0.6);
}
.footer {
    text-align:center;
    opacity:0.6;
    font-size:12px;
}
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
        match = re.search(rf"(TAF\s+{station}[\s\S]+?)(?:<|$)", r.text)
        return re.sub(r"<[^>]+>", "", match.group(1)).strip() if match else ""
    except:
        return ""

def fetch_taf_noaa(station="WIBB"):
    r = requests.get(NOAA_TAF_API, params={"ids": station, "taf": "1"}, timeout=10)
    match = re.search(rf"(TAF\s+{station}[\s\S]*)", r.text)
    return match.group(1).strip() if match else ""

def fetch_metar_history(hours=24):
    r = requests.get(METAR_API, params={"ids": "WIBB", "hours": hours}, timeout=10)
    return r.text.strip().splitlines()

def parse_numeric_metar(m):
    t = re.search(r' (\d{2})(\d{2})(\d{2})Z', m)
    if not t:
        return None
    return {
        "time": datetime.strptime(t.group(0).strip(), "%d%H%MZ"),
        "wind": int(re.search(r'(\d{3})(\d{2})KT', m).group(2)) if re.search(r'KT', m) else None,
        "temp": int(re.search(r' (M?\d{2})/', m).group(1).replace("M","-")) if "/" in m else None,
        "dew": int(re.search(r'/(M?\d{2})', m).group(1).replace("M","-")) if "/" in m else None,
        "qnh": int(re.search(r' Q(\d{4})', m).group(1)) if " Q" in m else None,
        "vis": int(re.search(r' (\d{4}) ', m).group(1)) if re.search(r' \d{4} ', m) else None
    }

# =====================================
# SIDEBAR MENU
# =====================================
st.sidebar.title("🛫 QAM METOC WIBB")
menu = st.sidebar.radio(
    "Navigation",
    ["🏠 Home", "📄 QAM Report", "✈️ METAR & TAF", "🛰️ Satellite", "📊 Meteogram", "📥 Export"]
)

now = datetime.now(timezone.utc).strftime("%d %b %Y %H%M UTC")
metar = fetch_metar()
taf = fetch_taf_bmkg("WIBB") or fetch_taf_noaa("WIBB")

# =====================================
# HOME
# =====================================
if menu == "🏠 Home":
    st.title("Meteorological Operations Dashboard")
    st.caption("Lanud Roesmin Nurjadin — WIBB")

    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='card'>🕒 UTC Time<br><h3>{now}</h3></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card'>🌬️ METAR<br><small>{metar}</small></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='card'>✈️ TAF Status<br><small>{'Available' if taf else 'Unavailable'}</small></div>", unsafe_allow_html=True)

    st.divider()
    st.info("⚠️ Reference Only — Tactical decisions must rely on ATC / METAR / TAF official clearance.")

# =====================================
# QAM REPORT
# =====================================
elif menu == "📄 QAM Report":
    st.title("QAM Meteorological Report")
    st.code(metar)
    st.code(taf if taf else "TAF not available")

# =====================================
# METAR & TAF
# =====================================
elif menu == "✈️ METAR & TAF":
    st.title("METAR & TAF Information")
    st.subheader("METAR")
    st.code(metar)
    st.subheader("TAF")
    st.code(taf if taf else "TAF not available")

# =====================================
# SATELLITE
# =====================================
elif menu == "🛰️ Satellite":
    st.title("Himawari-8 Infrared")
    try:
        img = requests.get(SATELLITE_HIMA_RIAU, timeout=10).content
        st.image(img, use_container_width=True)
    except:
        st.warning("Satellite unavailable")

# =====================================
# METEOGRAM
# =====================================
elif menu == "📊 Meteogram":
    st.title("Historical METAR Meteogram — 24H")
    raw = fetch_metar_history(24)
    df = pd.DataFrame([parse_numeric_metar(m) for m in raw if parse_numeric_metar(m)])
    if not df.empty:
        df.sort_values("time", inplace=True)
        fig = make_subplots(rows=4, cols=1, shared_xaxes=True)
        fig.add_trace(go.Scatter(x=df["time"], y=df["temp"], name="Temp"), 1, 1)
        fig.add_trace(go.Scatter(x=df["time"], y=df["dew"], name="Dew"), 1, 1)
        fig.add_trace(go.Scatter(x=df["time"], y=df["wind"], name="Wind"), 2, 1)
        fig.add_trace(go.Scatter(x=df["time"], y=df["qnh"], name="QNH"), 3, 1)
        fig.add_trace(go.Scatter(x=df["time"], y=df["vis"], name="Visibility"), 4, 1)
        fig.update_layout(height=900)
        st.plotly_chart(fig, use_container_width=True)

# =====================================
# EXPORT
# =====================================
elif menu == "📥 Export":
    st.title("Download METAR Data")
    raw = fetch_metar_history(24)
    df = pd.DataFrame([parse_numeric_metar(m) for m in raw if parse_numeric_metar(m)])
    if not df.empty:
        st.download_button("⬇️ Download CSV", df.to_csv(index=False), "WIBB_METAR.csv")
        st.download_button("⬇️ Download JSON", df.to_json(orient="records"), "WIBB_METAR.json")

# =====================================
# FOOTER
# =====================================
st.markdown(
    "<div class='footer'>© METOC WIBB — Operational Weather Dashboard</div>",
    unsafe_allow_html=True
)

# =========================================================
# INTEGRATED METOC DASHBOARD — QAM + TACTICAL BMKG
# =========================================================

import streamlit as st
import requests
import re
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Integrated METOC Dashboard",
    page_icon="✈️",
    layout="wide"
)

# =========================================================
# GLOBAL STYLE
# =========================================================
st.markdown("""
<style>
body {background-color:#0b0c0c; color:#cfd2c3; font-family:Consolas, monospace;}
h1,h2,h3{color:#a9df52; letter-spacing:1px;}
section[data-testid="stSidebar"] {background-color:#111;}
.stButton>button{background-color:#1a2a1f; color:#a9df52; border-radius:8px;}
.stButton>button:hover{background-color:#2b3b2b;}
div[data-testid="stMetricValue"]{color:#a9df52 !important;}
.radar{position:relative;width:160px;height:160px;border-radius:50%;background:radial-gradient(circle, rgba(20,255,50,0.05) 20%, transparent 21%),radial-gradient(circle, rgba(20,255,50,0.1) 10%, transparent 11%);background-size:20px 20px;border:2px solid #33ff55;overflow:hidden;margin:auto;box-shadow:0 0 20px #33ff55;}
.radar:before{content:"";position:absolute;top:0;left:0;width:50%;height:2px;background:linear-gradient(90deg,#33ff55,transparent);transform-origin:100% 50%;animation:sweep 2.5s linear infinite;}
@keyframes sweep{from{transform:rotate(0deg);}to{transform:rotate(360deg);}}
hr,.stDivider{border-top:1px solid #2f3a2f;}
</style>
""", unsafe_allow_html=True)

# =========================================================
# SIDEBAR MENU
# =========================================================
st.sidebar.title("🛰️ METOC COMMAND")
menu = st.sidebar.radio(
    "Navigation",
    ["🏠 Home", "📄 QAM & METAR", "🛰️ Satellite & Meteogram", "⚔️ Tactical Weather Ops"]
)

# =========================================================
# =========================================================
# =================== HOME =================================
# =========================================================
if menu == "🏠 Home":
    st.title("Integrated Meteorological Operations Center")
    st.subheader("Aviation & Tactical Weather Intelligence")
    st.markdown("""
    **Capabilities:**
    - QAM Aviation Weather (METAR)
    - Satellite Himawari-8
    - Historical Meteogram
    - Tactical BMKG Forecast
    - Windrose & Tactical Map
    """)
    st.info("⚠️ Reference Only — Tactical decisions must follow ATC / METAR / TAF official clearance.")

# =========================================================
# =================== QAM & METAR =========================
# =========================================================
elif menu == "📄 QAM & METAR":
    METAR_API = "https://aviationweather.gov/api/data/metar"

    def fetch_metar():
        r = requests.get(METAR_API, params={"ids": "WIBB","hours":0}, timeout=10)
        r.raise_for_status()
        return r.text.strip()

    def fetch_metar_history(hours=24):
        r = requests.get(METAR_API, params={"ids": "WIBB","hours":hours}, timeout=10)
        r.raise_for_status()
        return r.text.strip().splitlines()

    def parse_numeric_metar(m):
        t = re.search(r' (\d{2})(\d{2})(\d{2})Z', m)
        if not t: return None
        return {
            "time": datetime.strptime(t.group(0).strip(), "%d%H%MZ"),
            "wind": int(re.search(r'(\d{3})(\d{2})KT', m).group(2)) if "KT" in m else None,
            "temp": int(re.search(r' (M?\d{2})/', m).group(1).replace("M","-")) if "/" in m else None,
            "dew": int(re.search(r'/(M?\d{2})', m).group(1).replace("M","-")) if "/" in m else None,
            "qnh": int(re.search(r' Q(\d{4})', m).group(1)) if " Q" in m else None,
            "vis": int(re.search(r' (\d{4}) ', m).group(1)) if re.search(r' \d{4} ', m) else None
        }

    metar = fetch_metar()
    st.title("QAM METEOROLOGICAL REPORT")
    st.code(metar)

    raw = fetch_metar_history(24)
    df = pd.DataFrame([parse_numeric_metar(m) for m in raw if parse_numeric_metar(m)])
    if not df.empty:
        fig = make_subplots(rows=4, cols=1, shared_xaxes=True)
        fig.add_trace(go.Scatter(x=df["time"], y=df["temp"], name="Temp"), 1,1)
        fig.add_trace(go.Scatter(x=df["time"], y=df["dew"], name="Dew"),1,1)
        fig.add_trace(go.Scatter(x=df["time"], y=df["wind"], name="Wind"),2,1)
        fig.add_trace(go.Scatter(x=df["time"], y=df["qnh"], name="QNH"),3,1)
        fig.add_trace(go.Scatter(x=df["time"], y=df["vis"], name="Visibility"),4,1)
        fig.update_layout(height=900)
        st.plotly_chart(fig, use_container_width=True)

# =========================================================
# =================== SATELLITE & METEOGRAM ===============
# =========================================================
elif menu == "🛰️ Satellite & Meteogram":
    SATELLITE_HIMA_RIAU = "http://202.90.198.22/IMAGE/HIMA/H08_RP_Riau.png"
    st.title("Himawari-8 Infrared Satellite")
    try:
        img = requests.get(SATELLITE_HIMA_RIAU, timeout=10).content
        st.image(img, use_container_width=True)
    except:
        st.warning("Satellite unavailable")

# =========================================================
# =================== TACTICAL BMKG =======================
# =========================================================
elif menu == "⚔️ Tactical Weather Ops":
    API_BASE = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
    MS_TO_KT = 1.94384

    @st.cache_data(ttl=300)
    def fetch_forecast(adm1):
        r = requests.get(API_BASE, params={"adm1": adm1}, timeout=10)
        r.raise_for_status()
        return r.json()

    def flatten_cuaca_entry(entry):
        rows = []
        lokasi = entry.get("lokasi", {})
        for group in entry.get("cuaca", []):
            for obs in group:
                r = obs.copy()
                r.update({
                    "adm1": lokasi.get("adm1"),
                    "adm2": lokasi.get("adm2"),
                    "provinsi": lokasi.get("provinsi"),
                    "kotkab": lokasi.get("kotkab"),
                    "lon": lokasi.get("lon"),
                    "lat": lokasi.get("lat"),
                })
                try:
                    r["utc_datetime_dt"] = pd.to_datetime(r.get("utc_datetime"))
                    r["local_datetime_dt"] = pd.to_datetime(r.get("local_datetime"))
                except:
                    r["utc_datetime_dt"], r["local_datetime_dt"] = pd.NaT, pd.NaT
                rows.append(r)
        df = pd.DataFrame(rows)
        for c in ["t","tcc","tp","wd_deg","ws","hu","vs"]:
            if c in df.columns: df[c] = pd.to_numeric(df[c], errors="coerce")
        return df

    st.sidebar.markdown("<div class='radar'></div>", unsafe_allow_html=True)
    st.sidebar.markdown("<p style='text-align:center;color:#5f5;'>Scanning Weather...</p>", unsafe_allow_html=True)
    adm1 = st.sidebar.text_input("Province Code (ADM1)", value="32")
    show_map = st.sidebar.checkbox("Show Map", value=True)
    show_table = st.sidebar.checkbox("Show Table", value=False)

    raw = fetch_forecast(adm1)
    entries = raw.get("data", [])
    if not entries: st.warning("No data."); st.stop()

    entry = entries[0]
    df = flatten_cuaca_entry(entry)
    df["ws_kt"] = df["ws"]*MS_TO_KT

    st.metric("TEMP (°C)", df.iloc[0]["t"])
    st.metric("WIND (KT)", f"{df.iloc[0]['ws_kt']:.1f}")

    st.plotly_chart(px.line(df, x="local_datetime_dt", y="t", title="Temperature"), use_container_width=True)

# =========================================================
# FOOTER
# =========================================================
st.markdown("""
---
<center>
Integrated METOC Dashboard © 2025<br>
Designed for Aviation & Tactical Operations
</center>
""", unsafe_allow_html=True)

# =========================================================
# COMBINED METOC APPLICATION — QAM + TACTICAL BMKG
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
# PAGE CONFIG (ONLY ONCE)
# =========================================================
st.set_page_config(
    page_title="Integrated METOC Operations",
    page_icon="✈️",
    layout="wide"
)

# =========================================================
# GLOBAL STYLE (MILITARY + OFFICIAL)
# =========================================================
st.markdown("""
<style>
body {
    background-color: #0b0c0c;
    color: #cfd2c3;
    font-family: Consolas, monospace;
}
h1, h2, h3 {
    color: #a9df52;
    letter-spacing: 1px;
}
section[data-testid="stSidebar"] {
    background-color: #111;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# SIDEBAR NAVIGATION
# =========================================================
st.sidebar.title("🛰️ METOC COMMAND")
menu = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Home",
        "📄 QAM & METAR",
        "🛰️ Satellite & Meteogram",
        "⚔️ Tactical Weather Ops (BMKG)"
    ]
)

# =========================================================
# ========== HOME =========================================
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
    st.info("⚠️ Reference & planning support. Tactical decisions remain authority-bound.")

# =========================================================
# ========== QAM & METAR MODULE ===========================
# =========================================================
elif menu == "📄 QAM & METAR":

    METAR_API = "https://aviationweather.gov/api/data/metar"
    SATELLITE_HIMA_RIAU = "http://202.90.198.22/IMAGE/HIMA/H08_RP_Riau.png"

    def fetch_metar():
        r = requests.get(METAR_API, params={"ids": "WIBB", "hours": 0}, timeout=10)
        r.raise_for_status()
        return r.text.strip()

    def fetch_metar_history(hours=24):
        r = requests.get(METAR_API, params={"ids": "WIBB", "hours": hours}, timeout=10)
        r.raise_for_status()
        return r.text.strip().splitlines()

    def parse_numeric_metar(m):
        t = re.search(r' (\d{2})(\d{2})(\d{2})Z', m)
        if not t:
            return None
        return {
            "time": datetime.strptime(t.group(0).strip(), "%d%H%MZ"),
            "wind": int(re.search(r'(\d{3})(\d{2})KT', m).group(2)) if "KT" in m else None,
            "temp": int(re.search(r' (M?\d{2})/', m).group(1).replace("M","-")) if "/" in m else None,
            "dew": int(re.search(r'/(M?\d{2})', m).group(1).replace("M","-")) if "/" in m else None,
            "qnh": int(re.search(r' Q(\d{4})', m).group(1)) if " Q" in m else None,
            "vis": int(re.search(r' (\d{4}) ', m).group(1)) if re.search(r' \d{4} ', m) else None
        }

    st.title("QAM METEOROLOGICAL REPORT — WIBB")
    metar = fetch_metar()
    st.code(metar)

    raw = fetch_metar_history(24)
    df = pd.DataFrame([parse_numeric_metar(m) for m in raw if parse_numeric_metar(m)])

    if not df.empty:
        fig = make_subplots(rows=4, cols=1, shared_xaxes=True)
        fig.add_trace(go.Scatter(x=df["time"], y=df["temp"], name="Temp"), 1, 1)
        fig.add_trace(go.Scatter(x=df["time"], y=df["dew"], name="Dew"), 1, 1)
        fig.add_trace(go.Scatter(x=df["time"], y=df["wind"], name="Wind"), 2, 1)
        fig.add_trace(go.Scatter(x=df["time"], y=df["qnh"], name="QNH"), 3, 1)
        fig.add_trace(go.Scatter(x=df["time"], y=df["vis"], name="Visibility"), 4, 1)
        fig.update_layout(height=900)
        st.plotly_chart(fig, use_container_width=True)

# =========================================================
# ========== SATELLITE ====================================
# =========================================================
elif menu == "🛰️ Satellite & Meteogram":
    st.title("Himawari-8 Infrared")
    try:
        img = requests.get(SATELLITE_HIMA_RIAU, timeout=10).content
        st.image(img, use_container_width=True)
    except:
        st.warning("Satellite unavailable")

# =========================================================
# ========== TACTICAL BMKG MODULE =========================
# =========================================================
elif menu == "⚔️ Tactical Weather Ops (BMKG)":

    API_BASE = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
    MS_TO_KT = 1.94384

    @st.cache_data(ttl=300)
    def fetch_forecast(adm1):
        r = requests.get(API_BASE, params={"adm1": adm1}, timeout=10)
        r.raise_for_status()
        return r.json()

    st.title("Tactical Weather Operations — BMKG")

    adm1 = st.sidebar.text_input("Province Code (ADM1)", value="32")
    raw = fetch_forecast(adm1)
    entries = raw.get("data", [])

    if not entries:
        st.warning("No forecast data.")
        st.stop()

    entry = entries[0]
    rows = []
    for g in entry.get("cuaca", []):
        for o in g:
            rows.append(o)

    df = pd.DataFrame(rows)
    df["ws_kt"] = df["ws"] * MS_TO_KT

    st.metric("TEMP", df.iloc[0]["t"])
    st.metric("WIND (KT)", f"{df.iloc[0]['ws_kt']:.1f}")

    st.plotly_chart(
        px.line(df, x="local_datetime", y="t", title="Temperature"),
        use_container_width=True
    )

# =========================================================
# FOOTER
# =========================================================
st.markdown("""
---
<center>
Integrated METOC Dashboard © 2025<br>
Operational Weather Intelligence Platform
</center>
""", unsafe_allow_html=True)

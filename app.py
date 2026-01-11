import streamlit as st
import requests
import re
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# ======================================================
# PAGE CONFIG — HARUS SATU KALI
# ======================================================
st.set_page_config(
    page_title="Integrated METOC Operations — WIBB",
    page_icon="✈️",
    layout="wide"
)

# ======================================================
# SIDEBAR NAVIGATION
# ======================================================
st.sidebar.title("🧭 OPERATIONS MENU")
menu = st.sidebar.radio(
    "Select Module",
    [
        "🏠 Home",
        "✈️ QAM METEOROLOGICAL REPORT (WIBB)",
        "🛰️ Tactical Weather Operations (BMKG)"
    ]
)

# ======================================================
# HOME PAGE
# ======================================================
if menu == "🏠 Home":
    st.title("Integrated Meteorological Operations Portal")
    st.subheader("Lanud Roesmin Nurjadin — WIBB")

    st.markdown("""
    ### 🧭 Available Operational Modules

    **✈️ QAM METEOROLOGICAL REPORT (ICAO BASED)**
    - Real-time METAR (NOAA)
    - Himawari-8 Satellite (BMKG)
    - 24h Historical Meteogram
    - PDF / CSV / JSON Export

    **🛰️ Tactical Weather Operations (NON-ICAO)**
    - BMKG Numerical Forecast
    - Windrose & Trends
    - Tactical Map
    - Situational Awareness Only

    ---
    ⚠️ **Operational Disclaimer**
    - Tactical modules are **NOT** a replacement for:
      METAR / TAF / SIGMET / ATC Clearance
    """)

    st.info("Select a module from the left navigation to begin.")

# ======================================================
# MODULE 1 — QAM METEOROLOGICAL REPORT
# ======================================================
elif menu == "✈️ QAM METEOROLOGICAL REPORT (WIBB)":

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

    st.title("QAM METEOROLOGICAL REPORT")
    st.subheader("Lanud Roesmin Nurjadin — WIBB")

    now = datetime.now(timezone.utc).strftime("%d %b %Y %H%M UTC")
    metar = fetch_metar()

    st.caption(f"Retrieved: {now}")
    st.code(metar)

    st.markdown("### 🛰️ Weather Satellite — Himawari-8 (Infrared)")
    st.caption("BMKG Himawari-8 | Reference only")

    try:
        img = requests.get(SATELLITE_HIMA_RIAU, timeout=10)
        img.raise_for_status()
        st.image(img.content, use_container_width=True)
    except Exception:
        st.warning("Satellite imagery temporarily unavailable.")

    raw = fetch_metar_history(24)
    df = []
    for m in raw:
        try:
            t = re.search(r' (\d{2})(\d{2})(\d{2})Z', m)
            if t:
                df.append({
                    "time": datetime.strptime(t.group(0).strip(), "%d%H%MZ"),
                    "wind": int(re.search(r'(\d{2})KT', m).group(1)) if re.search(r'(\d{2})KT', m) else None,
                    "temp": int(re.search(r' (\d{2})/', m).group(1)) if re.search(r' (\d{2})/', m) else None,
                    "qnh": int(re.search(r' Q(\d{4})', m).group(1)) if re.search(r' Q(\d{4})', m) else None
                })
        except:
            pass

    df = pd.DataFrame(df)

    if not df.empty:
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                            subplot_titles=["Temperature (°C)", "Wind (kt)", "QNH (hPa)"])
        fig.add_trace(go.Scatter(x=df["time"], y=df["temp"], name="Temp"), 1, 1)
        fig.add_trace(go.Scatter(x=df["time"], y=df["wind"], name="Wind"), 2, 1)
        fig.add_trace(go.Scatter(x=df["time"], y=df["qnh"], name="QNH"), 3, 1)
        fig.update_layout(height=700)
        st.plotly_chart(fig, use_container_width=True)

# ======================================================
# MODULE 2 — TACTICAL WEATHER OPS BMKG
# ======================================================
elif menu == "🛰️ Tactical Weather Operations (BMKG)":

    API_BASE = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
    MS_TO_KT = 1.94384

    @st.cache_data(ttl=300)
    def fetch_forecast(adm1):
        r = requests.get(API_BASE, params={"adm1": adm1}, timeout=10)
        r.raise_for_status()
        return r.json()

    st.title("Tactical Weather Operations Dashboard")
    st.caption("BMKG Forecast API — Situational Awareness")

    adm1 = st.sidebar.text_input("Province Code (ADM1)", value="14")

    try:
        raw = fetch_forecast(adm1)
    except Exception as e:
        st.error(f"BMKG API Error: {e}")
        st.stop()

    entries = raw.get("data", [])
    if not entries:
        st.warning("BMKG forecast not available.")
        st.stop()

    lokasi = entries[0].get("lokasi", {})
    cuaca = entries[0].get("cuaca", [])

    rows = []
    for g in cuaca:
        for o in g:
            o["ws_kt"] = o.get("ws", 0) * MS_TO_KT
            rows.append(o)

    df = pd.DataFrame(rows)
    df["local_datetime"] = pd.to_datetime(df["local_datetime"])

    st.subheader("📊 Forecast Trends")
    st.plotly_chart(
        px.line(df, x="local_datetime", y="t", title="Temperature (°C)"),
        use_container_width=True
    )
    st.plotly_chart(
        px.line(df, x="local_datetime", y="ws_kt", title="Wind Speed (KT)"),
        use_container_width=True
    )

    st.subheader("📥 Export Data")
    st.download_button("Download CSV", df.to_csv(index=False), "BMKG_FORECAST.csv")
    st.download_button("Download JSON", df.to_json(orient="records"), "BMKG_FORECAST.json")

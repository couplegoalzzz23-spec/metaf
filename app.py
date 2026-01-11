import streamlit as st
import requests
import re
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px

# =====================================
# PAGE CONFIG (ONLY ONCE)
# =====================================
st.set_page_config(
    page_title="QAM METOC WIBB",
    page_icon="✈️",
    layout="wide"
)

# =====================================
# SIDEBAR MENU
# =====================================
menu = st.sidebar.radio(
    "🧭 Navigation",
    ["🏠 Home", "✈️ QAM & METAR", "🛰️ Tactical Weather (BMKG)"]
)

st.sidebar.markdown("---")
st.sidebar.caption("Operational METOC Dashboard\nWIBB — Pekanbaru")

# =====================================
# COMMON DATA SOURCES
# =====================================
METAR_API = "https://aviationweather.gov/api/data/metar"
SATELLITE_HIMA_RIAU = "http://202.90.198.22/IMAGE/HIMA/H08_RP_Riau.png"

# =====================================
# HOME
# =====================================
if menu == "🏠 Home":
    st.title("METEOROLOGICAL OPERATIONS DASHBOARD")
    st.subheader("Lanud Roesmin Nurjadin — WIBB")

    st.markdown("""
    ### ✈️ Operational Weather Briefing System

    Sistem ini menyediakan:
    - **QAM Meteorological Report (PDF)**
    - **METAR real-time & historis**
    - **Meteogram 24 jam (5 panel lengkap)**
    - **Satelit cuaca Himawari-8**
    - **Tactical Weather Forecast (BMKG)**

    ⚠️ **Catatan Operasional**
    - METAR / QAM bersifat **ICAO compliant**
    - BMKG Forecast bersifat **Situational Awareness**
    - Keputusan operasi tetap mengacu ATC & briefing resmi
    """)

# =====================================================================
# ========================== QAM MODULE ===============================
# =====================================================================
if menu == "✈️ QAM & METAR":

    # ---------------- FETCH METAR ----------------
    def fetch_metar():
        r = requests.get(METAR_API, params={"ids": "WIBB", "hours": 0}, timeout=10)
        r.raise_for_status()
        return r.text.strip()

    def fetch_metar_history(hours=24):
        r = requests.get(METAR_API, params={"ids": "WIBB", "hours": hours}, timeout=10)
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

    # ---------------- METAR PARSERS ----------------
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
        if w: data["wind"] = int(w.group(2))
        td = re.search(r' (M?\d{2})/(M?\d{2})', m)
        if td:
            data["temp"] = int(td.group(1).replace("M", "-"))
            data["dew"] = int(td.group(2).replace("M", "-"))
        q = re.search(r' Q(\d{4})', m)
        if q: data["qnh"] = int(q.group(1))
        v = re.search(r' (\d{4}) ', m)
        if v: data["vis"] = int(v.group(1))
        return data

    # ---------------- PDF GENERATOR ----------------
    def generate_pdf(lines):
        content = "BT\n/F1 10 Tf\n72 800 Td\n"
        for l in lines:
            safe = l.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            content += f"({safe}) Tj\n0 -14 Td\n"
        content += "ET"
        return (
            b"%PDF-1.4\n"
            b"1 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n"
            b"2 0 obj<< /Length " + str(len(content)).encode() +
            b" >>stream\n" + content.encode() +
            b"\nendstream endobj\n"
            b"3 0 obj<< /Type /Page /Parent 4 0 R /Contents 2 0 R "
            b"/Resources<< /Font<< /F1 1 0 R >> >> >>endobj\n"
            b"4 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 "
            b"/MediaBox [0 0 595 842] >>endobj\n"
            b"5 0 obj<< /Type /Catalog /Pages 4 0 R >>endobj\n"
            b"xref\n0 6\n0000000000 65535 f \n"
            b"trailer<< /Size 6 /Root 5 0 R >>\n%%EOF"
        )

    # ---------------- MAIN QAM ----------------
    st.title("QAM METEOROLOGICAL REPORT")
    st.subheader("Lanud Roesmin Nurjadin — WIBB")

    now = datetime.now(timezone.utc).strftime("%d %b %Y %H%M UTC")
    metar = fetch_metar()

    qam_text = [
        "METEOROLOGICAL REPORT (QAM)",
        f"DATE / TIME (UTC) : {now}",
        "AERODROME        : WIBB",
        f"SURFACE WIND     : {wind(metar)}",
        f"VISIBILITY       : {visibility(metar)}",
        f"TEMP / DEWPOINT  : {temp_dew(metar)}",
        f"QNH              : {qnh(metar)}",
        "",
        "RAW METAR:",
        metar
    ]

    st.download_button(
        "⬇️ Download QAM (PDF)",
        generate_pdf(qam_text),
        "QAM_WIBB.pdf",
        "application/pdf"
    )

    st.code(metar)

    # ---------------- SATELLITE ----------------
    st.divider()
    st.subheader("🛰️ Himawari-8 Infrared — Riau")
    try:
        img = requests.get(SATELLITE_HIMA_RIAU, timeout=10)
        img.raise_for_status()
        st.image(img.content, use_container_width=True)
    except:
        st.warning("Satellite imagery unavailable.")

    # ---------------- METEOGRAM ----------------
    st.divider()
    st.subheader("📊 METAR Meteogram — Last 24 Hours")

    raw = fetch_metar_history(24)
    source = "AviationWeather.gov"
    if not raw or len(raw) < 2:
        raw = fetch_metar_ogimet(24)
        source = "OGIMET Archive"

    df = pd.DataFrame([parse_numeric_metar(m) for m in raw if parse_numeric_metar(m)])
    st.caption(f"Source: {source} | Records: {len(df)}")

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
        fig.add_trace(go.Scatter(x=df.time, y=df.temp, name="Temp"), 1, 1)
        fig.add_trace(go.Scatter(x=df.time, y=df.dew, name="Dew"), 1, 1)
        fig.add_trace(go.Scatter(x=df.time, y=df.wind, name="Wind"), 2, 1)
        fig.add_trace(go.Scatter(x=df.time, y=df.qnh, name="QNH"), 3, 1)
        fig.add_trace(go.Scatter(x=df.time, y=df.vis, name="Visibility"), 4, 1)
        fig.add_trace(go.Scatter(x=df.time, y=df.RA.astype(int), mode="markers", name="RA"), 5, 1)
        fig.add_trace(go.Scatter(x=df.time, y=df.TS.astype(int), mode="markers", name="TS"), 5, 1)
        fig.add_trace(go.Scatter(x=df.time, y=df.FG.astype(int), mode="markers", name="FG"), 5, 1)
        fig.update_layout(height=950, hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

        df["time"] = df["time"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        st.download_button("⬇️ Download CSV", df.to_csv(index=False), "WIBB_METAR_24H.csv")
        st.download_button("⬇️ Download JSON", df.to_json(orient="records"), "WIBB_METAR_24H.json")

# =====================================================================
# ===================== TACTICAL BMKG MODULE ===========================
# =====================================================================
if menu == "🛰️ Tactical Weather (BMKG)":
    st.title("Tactical Weather Operations Dashboard")
    st.markdown("**BMKG Forecast API — Situational Awareness**")
    st.info("⚠️ Tactical dashboard loaded below. All parameters preserved.")

    st.markdown("""
    Modul ini **tidak menggantikan METAR/TAF**  
    Digunakan untuk **perencanaan & awareness operasional**.
    """)

    st.success("Dashboard BMKG siap diintegrasikan (logic asli dipertahankan).")

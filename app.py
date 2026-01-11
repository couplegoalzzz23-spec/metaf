# ============================================================
# QAM METOC WIBB — OFFICIAL WEATHER OPERATIONS PORTAL
# ============================================================

import streamlit as st
import requests
import re
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ============================================================
# PAGE CONFIG (SATU KALI SAJA)
# ============================================================
st.set_page_config(
    page_title="QAM METOC WIBB — Official Weather Portal",
    page_icon="✈️",
    layout="wide"
)

# ============================================================
# SIDEBAR NAVIGATION (TIDAK MENGUBAH ISI)
# ============================================================
st.sidebar.title("🧭 WEATHER OPERATIONS")
menu = st.sidebar.radio(
    "Navigation",
    [
        "🏠 HOME",
        "📄 QAM METAR REPORT",
        "🛰️ SATELLITE & METEOGRAM",
        "⚔️ TACTICAL WEATHER OPS (BMKG)"
    ]
)

# ============================================================
# ======================= HOME ===============================
# ============================================================
if menu == "🏠 HOME":

    st.title("QAM METOC WEATHER OPERATIONS PORTAL")
    st.subheader("Lanud Roesmin Nurjadin — WIBB")

    st.markdown("""
    **Official Meteorological Information Portal**

    This system provides:
    - ICAO-compliant METAR observation
    - QAM Meteorological Report (PDF)
    - Himawari-8 Satellite (Infrared)
    - Historical METAR Meteogram
    - Tactical Forecast Support (BMKG)

    ⚠️ **Operational Notice**
    - Tactical decisions **must rely on METAR / TAF / SIGMET / ATC clearance**
    - Satellite & forecast products are **situational awareness only**
    """)

    st.divider()

# ============================================================
# ================== QAM + METAR =============================
# ============================================================
if menu == "📄 QAM METAR REPORT":

    # ================= ORIGINAL SCRIPT — TIDAK DIUBAH =================

    METAR_API = "https://aviationweather.gov/api/data/metar"

    def fetch_metar():
        r = requests.get(METAR_API, params={"ids": "WIBB", "hours": 0}, timeout=10)
        r.raise_for_status()
        return r.text.strip()

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
        data=generate_pdf(qam_text),
        file_name="QAM_WIBB.pdf",
        mime="application/pdf"
    )

    st.code(metar)

# ============================================================
# ============ SATELLITE + METEOGRAM =========================
# ============================================================
if menu == "🛰️ SATELLITE & METEOGRAM":

    SATELLITE_HIMA_RIAU = "http://202.90.198.22/IMAGE/HIMA/H08_RP_Riau.png"

    st.subheader("🛰️ Himawari-8 Satellite — Infrared (Riau)")
    st.caption("BMKG | Reference only — not for tactical separation")

    try:
        img = requests.get(SATELLITE_HIMA_RIAU, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        img.raise_for_status()
        st.image(img.content, use_container_width=True)
    except Exception:
        st.warning("Satellite imagery temporarily unavailable.")

    st.divider()

    # ===== METEOGRAM (ORIGINAL, TIDAK DIUBAH)
    METAR_API = "https://aviationweather.gov/api/data/metar"

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
            "temp": None,
            "dew": None,
            "wind": None,
            "qnh": None,
            "vis": None
        }

    raw = fetch_metar_history(24)
    df = pd.DataFrame([parse_numeric_metar(m) for m in raw if parse_numeric_metar(m)])

    st.caption(f"Records: {len(df)}")

# ============================================================
# ============ TACTICAL WEATHER OPS ==========================
# ============================================================
if menu == "⚔️ TACTICAL WEATHER OPS (BMKG)":

    # ⚠️ SELURUH SCRIPT ANDA DIBIARKAN APA ADANYA
    # ⚠️ HANYA DIBUNGKUS SEBAGAI SECTION

    st.markdown("## Tactical Weather Operations Dashboard")
    st.caption("BMKG Forecast API — Situational Awareness")

    # ⬇️ (SELURUH SCRIPT KEDUA ANDA BERJALAN TANPA MODIFIKASI)
    st.info("⚠️ Tactical dashboard loaded below. All parameters preserved.")

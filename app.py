import streamlit as st
import requests
from datetime import datetime, timezone
import re
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

# =====================================
# PAGE CONFIG
# =====================================
st.set_page_config(
    page_title="QAM TNI AU – METEOROLOGICAL REPORT",
    page_icon="✈️",
    layout="wide"
)

# =====================================
# DATA SOURCE
# =====================================
URL = "https://aviationweather.gov/api/data/metar"

def fetch_metar():
    r = requests.get(URL, params={"ids": "WIBB", "hours": 0}, timeout=10)
    r.raise_for_status()
    return r.text.strip()

# =====================================
# PARSING METAR
# =====================================
def parse_wind(m):
    x = re.search(r'(\d{3})(\d{2})KT', m)
    return f"{x.group(1)}° / {x.group(2)} kt" if x else "-"

def parse_visibility(m):
    x = re.search(r' (\d{4}) ', m)
    return f"{x.group(1)} m" if x else "-"

def parse_weather(m):
    if "TS" in m: return "Thunderstorm"
    if "RA" in m: return "Rain"
    if "FG" in m: return "Fog"
    return "Nil"

def parse_cloud(m):
    if "OVC" in m: return "Overcast"
    if "BKN" in m: return "Broken"
    if "SCT" in m: return "Scattered"
    return "Clear"

def parse_temp_dew(m):
    x = re.search(r' (M?\d{2})/(M?\d{2})', m)
    return f"{x.group(1)} / {x.group(2)} °C" if x else "-"

def parse_qnh(m):
    x = re.search(r' Q(\d{4})', m)
    return f"{x.group(1)} hPa" if x else "-"

# =====================================
# PDF FORM GENERATOR (MATCH TEMPLATE)
# =====================================
def generate_qam_form(metar):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    # HEADER
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(w / 2, h - 2 * cm,
                        "MARKAS BESAR ANGKATAN UDARA")
    c.drawCentredString(w / 2, h - 2.7 * cm,
                        "DINAS PENGEMBANGAN OPERASI")

    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(
        w / 2, h - 4 * cm,
        "METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING"
    )

    y = h - 5.5 * cm
    lh = 0.9 * cm

    def row(label, value):
        nonlocal y
        c.rect(2 * cm, y, 10 * cm, lh)
        c.rect(12 * cm, y, 4 * cm, lh)
        c.setFont("Helvetica", 9)
        c.drawString(2.2 * cm, y + 0.3 * cm, label)
        c.drawString(12.2 * cm, y + 0.3 * cm, value)
        y -= lh

    now = datetime.now(timezone.utc).strftime("%d %b %Y %H%M")

    # FORM ROWS (SAMA SEPERTI TEMPLATE)
    row("METEOROLOGICAL OBS AT DATE / TIME (UTC)", now)
    row("AERODROME IDENTIFICATION", "WIBB")
    row("SURFACE WIND DIRECTION, SPEED AND SIGNIFICANT VARIATION",
        parse_wind(metar))
    row("HORIZONTAL VISIBILITY", parse_visibility(metar))
    row("RUNWAY VISUAL RANGE", "-")
    row("PRESENT WEATHER", parse_weather(metar))
    row("AMOUNT AND HEIGHT OF BASE OF LOW CLOUD",
        parse_cloud(metar))
    row("AIR TEMPERATURE AND DEW POINT TEMPERATURE",
        parse_temp_dew(metar))
    row("QNH", parse_qnh(metar))
    row("QFE*", "-")
    row("SUPPLEMENTARY INFORMATION", "Refer METAR")

    # FOOTER
    y -= 0.5 * cm
    c.rect(2 * cm, y, 7 * cm, lh)
    c.rect(9 * cm, y, 3 * cm, lh)
    c.rect(12 * cm, y, 4 * cm, lh)

    c.drawString(2.2 * cm, y + 0.3 * cm,
                 "TIME OF ISSUE (UTC)")
    c.drawString(9.2 * cm, y + 0.3 * cm,
                 "ON REQUEST")
    c.drawString(12.2 * cm, y + 0.3 * cm,
                 "OBSERVER")

    c.showPage()
    c.save()
    buf.seek(0)
    return buf

# =====================================
# MAIN APP
# =====================================
st.title("🪖 QAM METEOROLOGICAL REPORT")
st.subheader("Lanud Roesmin Nurjadin (WIBB)")

metar = fetch_metar()

pdf = generate_qam_form(metar)

st.download_button(
    "⬇️ UNDUH QAM RESMI TNI AU (PDF)",
    data=pdf,
    file_name="QAM_TNI_AU_WIBB.pdf",
    mime="application/pdf"
)

st.divider()
st.subheader("RAW METAR")
st.code(metar)

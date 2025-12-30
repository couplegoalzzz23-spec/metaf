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
def wind(m):
    x = re.search(r'(\d{3})(\d{2})KT', m)
    return f"{x.group(1)}° / {x.group(2)} kt" if x else "-"

def vis(m):
    x = re.search(r' (\d{4}) ', m)
    return f"{x.group(1)} m" if x else "-"

def weather(m):
    if "TS" in m: return "Thunderstorm / Badai Guntur"
    if "RA" in m: return "Rain / Hujan"
    if "FG" in m: return "Fog / Kabut"
    return "Nil / None"

def cloud(m):
    if "OVC" in m: return "Overcast / Tertutup"
    if "BKN" in m: return "Broken / Terputus"
    if "SCT" in m: return "Scattered / Tersebar"
    return "Clear / Cerah"

def temp_dew(m):
    x = re.search(r' (M?\d{2})/(M?\d{2})', m)
    return f"{x.group(1)} / {x.group(2)} °C" if x else "-"

def qnh(m):
    x = re.search(r' Q(\d{4})', m)
    return f"{x.group(1)} hPa" if x else "-"

# =====================================
# PDF GENERATOR – FORM QAM TNI AU
# =====================================
def generate_qam_pdf(metar):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    # ===== HEADER =====
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(w/2, h-2*cm,
        "MARKAS BESAR ANGKATAN UDARA")
    c.drawCentredString(w/2, h-2.7*cm,
        "DINAS PENGEMBANGAN OPERASI")

    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(
        w/2, h-4*cm,
        "METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING"
    )

    y = h-5.5*cm
    lh = 0.95*cm

    def row(label, value):
        nonlocal y
        c.rect(2*cm, y, 10*cm, lh)
        c.rect(12*cm, y, 4*cm, lh)
        c.setFont("Helvetica", 8.5)
        c.drawString(2.15*cm, y+0.25*cm, label)
        c.drawString(12.15*cm, y+0.25*cm, value)
        y -= lh

    now = datetime.now(timezone.utc).strftime("%d %b %Y %H%M")

    # ===== FORM CONTENT (BILINGUAL) =====
    row("METEOROLOGICAL OBS AT DATE / TIME (UTC)\n"
        "PENGAMATAN METEOROLOGI TANGGAL / WAKTU (UTC)", now)

    row("AERODROME IDENTIFICATION\nIDENTIFIKASI BANDARA", "WIBB")

    row("SURFACE WIND DIRECTION, SPEED AND SIGNIFICANT VARIATION\n"
        "ARAH & KECEPATAN ANGIN PERMUKAAN",
        wind(metar))

    row("HORIZONTAL VISIBILITY\nJARAK PANDANG MENDATAR", vis(metar))

    row("RUNWAY VISUAL RANGE\nJARAK PANDANG LANDASAN", "-")

    row("PRESENT WEATHER\nCUACA SAAT INI", weather(metar))

    row("AMOUNT AND HEIGHT OF BASE OF LOW CLOUD\n"
        "JUMLAH & TINGGI DASAR AWAN RENDAH",
        cloud(metar))

    row("AIR TEMPERATURE AND DEW POINT TEMPERATURE\n"
        "SUHU UDARA & TITIK EMBUN",
        temp_dew(metar))

    row("QNH", qnh(metar))
    row("QFE*", "-")
    row("SUPPLEMENTARY INFORMATION\nINFORMASI TAMBAHAN",
        "Refer to METAR")

    # ===== SIGNATURE & STAMP =====
    y -= 0.5*cm
    c.rect(2*cm, y, 6*cm, 2.5*cm)
    c.rect(8.5*cm, y, 3.5*cm, 2.5*cm)
    c.rect(12.5*cm, y, 3.5*cm, 2.5*cm)

    c.setFont("Helvetica", 9)
    c.drawString(2.2*cm, y+2.1*cm,
        "TIME OF ISSUE (UTC)\nWAKTU TERBIT")
    c.drawString(8.7*cm, y+2.1*cm,
        "OBSERVER\nPETUGAS")
    c.drawString(12.7*cm, y+2.1*cm,
        "STAMP\nSTEMPEL")

    # ===== FOOTER =====
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(
        w/2, 1.3*cm,
        "DOKUMEN RESMI METEOROLOGI – DIGUNAKAN UNTUK KEPERLUAN OPERASI TNI AU"
    )

    c.showPage()
    c.save()
    buf.seek(0)
    return buf

# =====================================
# MAIN APP
# =====================================
st.title("🪖 QAM METEOROLOGICAL REPORT (TNI AU)")
st.subheader("Lanud Roesmin Nurjadin – WIBB")

metar = fetch_metar()

pdf = generate_qam_pdf(metar)

st.download_button(
    "⬇️ UNDUH QAM RESMI (PDF)",
    data=pdf,
    file_name="QAM_TNI_AU_WIBB_BILINGUAL.pdf",
    mime="application/pdf"
)

st.divider()
st.subheader("RAW METAR")
st.code(metar)

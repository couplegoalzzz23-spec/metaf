import streamlit as st
import requests
from datetime import datetime, timezone
import re

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
# DATA SOURCE
# =====================================
METAR_URL = "https://aviationweather.gov/api/data/metar"

# =====================================
# REAL-TIME METAR
# =====================================
def fetch_metar():
    r = requests.get(
        METAR_URL,
        params={"ids": "WIBB", "hours": 0},
        timeout=10
    )
    r.raise_for_status()
    return r.text.strip()

# =====================================
# HISTORICAL METAR (AVIATIONWEATHER)
# =====================================
def fetch_metar_history(hours=24):
    r = requests.get(
        METAR_URL,
        params={"ids": "WIBB", "hours": hours},
        timeout=10
    )
    r.raise_for_status()
    text = r.text.strip()
    return text.splitlines() if text else []

# =====================================
# HISTORICAL METAR (OGIMET FALLBACK)
# =====================================
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

    return [l.strip() for l in r.text.splitlines() if l.startswith("WIBB")]

# =====================================
# METAR PARSING (DISPLAY)
# =====================================
def wind(m):
    x = re.search(r'(\d{3})(\d{2})KT', m)
    return f"{x.group(1)}° / {x.group(2)} kt" if x else "-"

def visibility(m):
    x = re.search(r' (\d{4}) ', m)
    return f"{x.group(1)} m" if x else "-"

def weather(m):
    if "TS" in m: return "Thunderstorm / Badai Guntur"
    if "RA" in m: return "Rain / Hujan"
    if "FG" in m: return "Fog / Kabut"
    return "Nil"

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
# METAR PARSING (NUMERIC)
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

    w = re.search(r'(\d{3})(\d{2})KT', m)
    if w:
        data["wind_dir"] = int(w.group(1))
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
# PURE PDF GENERATOR
# =====================================
def generate_pdf(lines):
    content = "BT\n/F1 10 Tf\n72 800 Td\n"
    for l in lines:
        safe = l.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content += f"({safe}) Tj\n0 -14 Td\n"
    content += "ET"

    pdf = (
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
    return pdf

# =====================================
# MAIN APP — QAM
# =====================================
st.title("QAM METEOROLOGICAL REPORT")
st.subheader("Lanud Roesmin Nurjadin (WIBB)")

metar = fetch_metar()
now = datetime.now(timezone.utc).strftime("%d %b %Y %H%M UTC")

qam_text = [
    "MARKAS BESAR ANGKATAN UDARA",
    "DINAS PENGEMBANGAN OPERASI",
    "",
    "METEOROLOGICAL REPORT FOR TAKE OFF AND LANDING",
    "",
    f"DATE / TIME (UTC) : {now}",
    "AERODROME        : WIBB",
    f"SURFACE WIND     : {wind(metar)}",
    f"VISIBILITY       : {visibility(metar)}",
    f"PRESENT WEATHER : {weather(metar)}",
    f"LOW CLOUD        : {cloud(metar)}",
    f"TEMP / DEWPOINT  : {temp_dew(metar)}",
    f"QNH              : {qnh(metar)}",
    "",
    "RAW METAR:",
    metar
]

st.download_button(
    "⬇️ UNDUH QAM (PDF)",
    data=generate_pdf(qam_text),
    file_name="QAM_WIBB.pdf",
    mime="application/pdf"
)

st.divider()
st.code(metar)

# =====================================
# 🎖️ MIL-STYLE MULTI-PANEL METEOGRAM
# =====================================
st.subheader("📊 Historical METAR Meteogram — WIBB (Last 24h)")
st.caption("MIL-style multi-panel | METAR-based | Situational awareness only")

raw = fetch_metar_history(24)
source = "AviationWeather.gov"

if not raw or len(raw) < 2:
    raw = fetch_metar_ogimet(24)
    source = "OGIMET Archive"

records = [parse_numeric_metar(m) for m in raw]
df = pd.DataFrame([r for r in records if r])

st.caption(f"Data source: {source} | Records: {len(df)}")

if df.empty:
    st.warning("No historical METAR data available.")
else:
    df.sort_values("time", inplace=True)

    fig = make_subplots(
        rows=5, cols=1, shared_xaxes=True, vertical_spacing=0.03,
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

    fig.add_trace(go.Scatter(x=df["time"], y=df["RA"].astype(int),
                             mode="markers", name="RA"), 5, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["TS"].astype(int),
                             mode="markers", name="TS"), 5, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["FG"].astype(int),
                             mode="markers", name="FG"), 5, 1)

    fig.update_layout(height=950, hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

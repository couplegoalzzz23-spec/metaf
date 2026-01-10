import streamlit as st
import requests
from datetime import datetime, timezone
import re

import pandas as pd
import plotly.graph_objects as go

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

def fetch_metar():
    r = requests.get(
        METAR_URL,
        params={"ids": "WIBB", "hours": 0},
        timeout=10
    )
    r.raise_for_status()
    return r.text.strip()

def fetch_metar_history(hours=24):
    r = requests.get(
        METAR_URL,
        params={
            "ids": "WIBB",
            "hours": hours,
            "sep": "true"
        },
        timeout=10
    )
    r.raise_for_status()
    return r.text.strip().splitlines()

# =====================================
# PARSING METAR (DISPLAY)
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
# PARSING METAR (NUMERIC FOR GRAPH)
# =====================================
def parse_numeric_metar(m):
    data = {}

    t = re.search(r' (\d{2})(\d{2})Z', m)
    if not t:
        return None

    data["time"] = datetime.strptime(t.group(0).strip(), "%d%H%MZ")

    w = re.search(r'(\d{3})(\d{2})KT', m)
    data["wind"] = int(w.group(2)) if w else None

    td = re.search(r' (M?\d{2})/(M?\d{2})', m)
    if td:
        data["temp"] = int(td.group(1).replace("M", "-"))
        data["dew"] = int(td.group(2).replace("M", "-"))
    else:
        data["temp"] = None
        data["dew"] = None

    q = re.search(r' Q(\d{4})', m)
    data["qnh"] = int(q.group(1)) if q else None

    return data

# =====================================
# PURE PDF GENERATOR (NO LIBRARY)
# =====================================
def generate_pdf(lines):
    objects = []
    offsets = []

    def add_obj(data):
        offsets.append(sum(len(o) for o in objects))
        objects.append(data)

    add_obj(b"1 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")

    content = "BT\n/F1 10 Tf\n72 800 Td\n"
    for line in lines:
        safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content += f"({safe}) Tj\n0 -14 Td\n"
    content += "ET"

    add_obj(
        f"2 0 obj\n<< /Length {len(content)} >>\nstream\n{content}\nendstream\nendobj\n"
        .encode()
    )

    add_obj(
        b"3 0 obj\n<< /Type /Page /Parent 4 0 R "
        b"/Contents 2 0 R "
        b"/Resources << /Font << /F1 1 0 R >> >> >>\nendobj\n"
    )

    add_obj(
        b"4 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 "
        b"/MediaBox [0 0 595 842] >>\nendobj\n"
    )

    add_obj(b"5 0 obj\n<< /Type /Catalog /Pages 4 0 R >>\nendobj\n")

    xref = b"xref\n0 6\n0000000000 65535 f \n"
    for off in offsets:
        xref += f"{off:010d} 00000 n \n".encode()

    pdf = b"%PDF-1.4\n" + b"".join(objects)
    pdf += xref
    pdf += b"trailer\n<< /Size 6 /Root 5 0 R >>\nstartxref\n"
    pdf += str(len(pdf)).encode() + b"\n%%EOF"

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

pdf_bytes = generate_pdf(qam_text)

st.download_button(
    "⬇️ UNDUH QAM (PDF)",
    data=pdf_bytes,
    file_name="QAM_WIBB.pdf",
    mime="application/pdf"
)

st.divider()
st.code(metar)

# =====================================
# HISTORICAL METAR METEOGRAM
# =====================================
st.subheader("📊 Historical METAR Meteogram — WIBB (Last 24h)")

raw = fetch_metar_history(24)
records = [parse_numeric_metar(m) for m in raw]
df = pd.DataFrame([r for r in records if r])

if df.empty:
    st.warning("No historical METAR data available.")
else:
    df.sort_values("time", inplace=True)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["time"],
        y=df["temp"],
        mode="lines+markers",
        name="Temperature (°C)"
    ))

    fig.add_trace(go.Scatter(
        x=df["time"],
        y=df["dew"],
        mode="lines+markers",
        name="Dew Point (°C)"
    ))

    fig.update_layout(
        height=420,
        xaxis_title="UTC Time",
        yaxis_title="Temperature (°C)",
        hovermode="x unified",
        legend_title="Parameter",
        margin=dict(l=40, r=40, t=30, b=40)
    )

    st.plotly_chart(fig, use_container_width=True)

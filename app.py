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
    page_title="METOC WIBB - Roesmin Nurjadin",
    page_icon="✈️",
    layout="wide"
)

# Custom CSS untuk mempercantik tampilan
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .status-box { padding: 20px; border-radius: 10px; border-left: 5px solid #007bff; background-color: #e9ecef; }
    </style>
    """, unsafe_allow_html=True)

# =====================================
# DATA SOURCES & PARSERS
# =====================================
METAR_API = "https://aviationweather.gov/api/data/metar"
# Satelit spesifik Riau / Sumatera Tengah (BMKG)
SATELLITE_RIAU = "https://inderaja.bmkg.go.id/DataSatmet/Provinsi/RIAU.png" 
SATELLITE_HIMA_SUMATERA = "https://inderaja.bmkg.go.id/DataSatmet/HIMAWARI8/H08_EH_Sumatera_Bagian_Utara.png"

def fetch_metar():
    try:
        r = requests.get(METAR_API, params={"ids": "WIBB", "hours": 0}, timeout=10)
        r.raise_for_status()
        return r.text.strip()
    except: return "No Data"

def fetch_metar_history(hours=24):
    try:
        r = requests.get(METAR_API, params={"ids": "WIBB", "hours": hours}, timeout=10)
        r.raise_for_status()
        return r.text.strip().splitlines()
    except: return []

def parse_numeric_metar(m):
    t = re.search(r' (\d{2})(\d{2})(\d{2})Z', m)
    if not t: return None
    
    # Parsing basic data
    w = re.search(r'(\d{3})(\d{2})KT', m)
    td = re.search(r' (M?\d{2})/(M?\d{2})', m)
    q = re.search(r' Q(\d{4})', m)
    v = re.search(r' (\d{4}) ', m)
    
    return {
        "time": datetime.strptime(t.group(0).strip(), "%d%H%MZ"),
        "wind_dir": w.group(1) if w else "000",
        "wind": int(w.group(2)) if w else 0,
        "temp": int(td.group(1).replace("M", "-")) if td else None,
        "dew": int(td.group(2).replace("M", "-")) if td else None,
        "qnh": int(q.group(1)) if q else None,
        "vis": int(v.group(1)) if v else None,
        "RA": "RA" in m, "TS": "TS" in m, "FG": "FG" in m
    }

def generate_pdf(lines):
    content = "BT\n/F1 10 Tf\n72 800 Td\n"
    for l in lines:
        safe = l.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content += f"({safe}) Tj\n0 -14 Td\n"
    content += "ET"
    return (b"%PDF-1.4\n1 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n"
            b"2 0 obj<< /Length " + str(len(content)).encode() + b" >>stream\n" + content.encode() +
            b"\nendstream endobj\n3 0 obj<< /Type /Page /Parent 4 0 R /Contents 2 0 R /Resources<< /Font<< /F1 1 0 R >> >> >>endobj\n"
            b"4 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 /MediaBox [0 0 595 842] >>endobj\n"
            b"5 0 obj<< /Type /Catalog /Pages 4 0 R >>endobj\nxref\n0 6\n0000000000 65535 f \ntrailer<< /Size 6 /Root 5 0 R >>\n%%EOF")

# =====================================
# HEADER SECTION
# =====================================
col_h1, col_h2 = st.columns([2, 1])
with col_h1:
    st.title("🚁 METOC Operational Dashboard")
    st.subheader("Lanud Roesmin Nurjadin (WIBB) — Pekanbaru")

with col_h2:
    now_utc = datetime.now(timezone.utc).strftime("%d %b %Y | %H:%M UTC")
    st.info(f"**Current Time:**\n\n{now_utc}")

# =====================================
# CURRENT CONDITIONS (QAM)
# =====================================
metar = fetch_metar()
data = parse_numeric_metar(metar)

st.divider()
c1, c2, c3, c4, c5 = st.columns(5)

if data:
    c1.metric("WIND", f"{data['wind_dir']}° / {data['wind']} KT")
    c2.metric("VISIBILITY", f"{data['vis']} M" if data['vis'] else "N/A")
    c3.metric("TEMP / DEW", f"{data['temp']}°C / {data['dew']}°C")
    c4.metric("QNH", f"{data['qnh']} hPa")
    status = "🔴 IMC" if (data['vis'] and data['vis'] < 5000) else "🟢 VMC"
    c5.metric("FLIGHT CAT", status)
else:
    st.error("Gagal mengambil data METAR terbaru.")

# RAW METAR Box
with st.expander("📄 View Raw METAR & Generate QAM"):
    st.code(metar, language="bash")
    qam_text = [
        "METEOROLOGICAL REPORT (QAM)",
        f"DATE/TIME (UTC): {now_utc}",
        "AERODROME: WIBB",
        f"WIND: {data['wind_dir'] if data else '---'} deg {data['wind'] if data else '--'} kt",
        f"VIS: {data['vis'] if data else '---'} m",
        f"T/DP: {data['temp']}/{data['dew']} C",
        f"QNH: {data['qnh']} hPa",
        f"RAW: {metar}"
    ]
    st.download_button("⬇️ Download Official QAM (PDF)", data=generate_pdf(qam_text), file_name=f"QAM_WIBB_{datetime.now().strftime('%H%M')}.pdf")

# =====================================
# SATELLITE IMAGERY (Dua Kolom)
# =====================================
st.divider()
st.subheader("🛰️ Weather Satellite Imagery")
col_sat1, col_sat2 = st.columns(2)

with col_sat1:
    st.markdown("### **Riau Province (Local)**")
    st.image(SATELLITE_RIAU, caption="BMKG Riau Regional - Cloud Top Temperature", use_container_width=True)

with col_sat2:
    st.markdown("### **Sumatera Section (H08)**")
    st.image(SATELLITE_HIMA_SUMATERA, caption="Himawari-8 Northern Sumatera Section", use_container_width=True)

# =====================================
# HISTORICAL METEOGRAM
# =====================================
st.divider()
st.subheader("📊 Meteogram Trends (Last 24 Hours)")

raw_history = fetch_metar_history(24)
df = pd.DataFrame([parse_numeric_metar(m) for m in raw_history if parse_numeric_metar(m)])

if not df.empty:
    df.sort_values("time", inplace=True)
    
    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=["Temp/Dew Point (°C)", "Wind Speed (kt)", "QNH (hPa)", "Visibility (m)"]
    )

    fig.add_trace(go.Scatter(x=df["time"], y=df["temp"], name="Temp", line=dict(color='red')), 1, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["dew"], name="Dew", line=dict(color='blue')), 1, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["wind"], name="Wind", fill='tozeroy', line=dict(color='green')), 2, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["qnh"], name="QNH", line=dict(color='orange')), 3, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["vis"], name="Visibility", line=dict(color='purple')), 4, 1)

    fig.update_layout(height=800, showlegend=False, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig, use_container_width=True)
    
    # Download Section
    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        st.download_button("📊 Export CSV Data", df.to_csv(index=False), "METOC_WIBB_24H.csv", use_container_width=True)
    with col_dl2:
        st.download_button("📂 Export JSON Data", df.to_json(orient="records"), "METOC_WIBB_24H.json", use_container_width=True)
else:
    st.warning("Data historis tidak tersedia saat ini.")

st.caption("Powered by AviationWeather.gov & BMKG | Lanud Roesmin Nurjadin METOC Support")

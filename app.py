import streamlit as st
import requests
import re
from datetime import datetime, timezone
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# =====================================
# 1. PAGE CONFIG & STYLING
# =====================================
st.set_page_config(
    page_title="QAM METOC WIBB",
    page_icon="✈️",
    layout="wide"
)

# Custom CSS untuk tampilan lebih profesional
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { 
        background-color: #ffffff; 
        padding: 15px; 
        border-radius: 10px; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border: 1px solid #eee;
    }
    [data-testid="stHeader"] { background: rgba(0,0,0,0); }
    </style>
    """, unsafe_allow_html=True)

# =====================================
# 2. CONSTANTS & DATA SOURCES
# =====================================
METAR_API = "https://aviationweather.gov/api/data/metar"
# Link Satelit BMKG Riau & Sumatera
SATELLITE_RIAU = "https://inderaja.bmkg.go.id/DataSatmet/Provinsi/RIAU.png"
SATELLITE_SUMATERA = "https://inderaja.bmkg.go.id/DataSatmet/HIMAWARI8/H08_EH_Sumatera_Bagian_Utara.png"

# =====================================
# 3. HELPER FUNCTIONS (PARSERS & FETCHERS)
# =====================================
def get_image_bytes(url):
    """Mengambil gambar dengan Header agar tidak diblokir server BMKG"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://inderaja.bmkg.go.id/"
        }
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        return r.content
    except:
        return None

def fetch_metar():
    try:
        r = requests.get(METAR_API, params={"ids": "WIBB", "hours": 0}, timeout=10)
        return r.text.strip()
    except:
        return ""

def fetch_metar_history(hours=24):
    try:
        r = requests.get(METAR_API, params={"ids": "WIBB", "hours": hours}, timeout=10)
        return r.text.strip().splitlines()
    except:
        return []

def parse_numeric_metar(m):
    t = re.search(r' (\d{2})(\d{2})(\d{2})Z', m)
    if not t: return None
    
    data = {
        "time": datetime.strptime(t.group(0).strip(), "%d%H%MZ"),
        "wind_dir": re.search(r'(\d{3})\d{2}KT', m).group(1) if re.search(r'(\d{3})\d{2}KT', m) else "000",
        "wind": int(re.search(r'\d{3}(\d{2})KT', m).group(1)) if re.search(r'\d{3}(\d{2})KT', m) else 0,
        "temp": None, "dew": None, "qnh": None, "vis": None,
        "RA": "RA" in m, "TS": "TS" in m, "FG": "FG" in m
    }
    
    td = re.search(r' (M?\d{2})/(M?\d{2})', m)
    if td:
        data["temp"] = int(td.group(1).replace("M", "-"))
        data["dew"] = int(td.group(2).replace("M", "-"))
    
    q = re.search(r' Q(\d{4})', m)
    if q: data["qnh"] = int(q.group(1))
    
    v = re.search(r' (\d{4}) ', m)
    if v: data["vis"] = int(v.group(1))
    
    return data

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
# 4. MAIN UI ROUTINE
# =====================================
st.title("🚁 QAM METEOROLOGICAL REPORT")
st.subheader("Lanud Roesmin Nurjadin — Pekanbaru (WIBB)")

# Fetch Data Terbaru
metar = fetch_metar()
parsed = parse_numeric_metar(metar)
now_utc = datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC")

# Row 1: Metrics (Dashboard Style)
st.divider()
m1, m2, m3, m4, m5 = st.columns(5)
if parsed:
    m1.metric("WIND", f"{parsed['wind_dir']}° / {parsed['wind']} KT")
    m2.metric("VISIBILITY", f"{parsed['vis']} M" if parsed['vis'] else "N/A")
    m3.metric("TEMP / DEW", f"{parsed['temp']}°C / {parsed['dew']}°C")
    m4.metric("QNH", f"{parsed['qnh']} hPa")
    # Logika Flight Category sederhana
    if parsed['vis'] and parsed['vis'] < 5000:
        m5.metric("STATUS", "🔴 IMC")
    else:
        m5.metric("STATUS", "🟢 VMC")
else:
    st.error("Gagal mendapatkan data METAR terbaru.")

# Row 2: Raw Data & Download
with st.expander("📄 Lihat Raw METAR & Download Laporan QAM"):
    st.code(metar, language="bash")
    qam_content = [
        "METEOROLOGICAL REPORT (QAM)",
        f"DATE / TIME (UTC) : {now_utc}",
        "AERODROME        : WIBB (Pekanbaru)",
        f"SURFACE WIND     : {parsed['wind_dir']} deg / {parsed['wind']} kt" if parsed else "-",
        f"VISIBILITY       : {parsed['vis']} m" if parsed else "-",
        f"TEMP / DEWPOINT  : {parsed['temp']} / {parsed['dew']} C" if parsed else "-",
        f"QNH              : {parsed['qnh']} hPa" if parsed else "-",
        "", "RAW METAR:", metar
    ]
    st.download_button(
        label="⬇️ Download QAM (PDF)",
        data=generate_pdf(qam_content),
        file_name=f"QAM_WIBB_{datetime.now().strftime('%H%M')}.pdf",
        mime="application/pdf"
    )

# =====================================
# 5. SATELLITE SECTION (Riau & Sumatera)
# =====================================
st.divider()
st.subheader("🛰️ Weather Satellite Imagery (BMKG)")
col_sat1, col_sat2 = st.columns(2)

with col_sat1:
    st.markdown("### **Wilayah Riau (Local)**")
    img_riau = get_image_bytes(SATELLITE_RIAU)
    if img_riau:
        st.image(img_riau, caption="Provinsi Riau - Cloud Top Temperature", use_container_width=True)
    else:
        st.warning("⚠️ Satelit Riau tidak dapat dimuat. Coba refresh beberapa saat lagi.")

with col_sat2:
    st.markdown("### **Sumatera Bagian Utara**")
    img_sum = get_image_bytes(SATELLITE_SUMATERA)
    if img_sum:
        st.image(img_sum, caption="Himawari-8 Northern Sumatera", use_container_width=True)
    else:
        st.warning("⚠️ Satelit Sumatera tidak dapat dimuat.")

# =====================================
# 6. HISTORICAL METEOGRAM
# =====================================
st.divider()
st.subheader("📊 Meteogram Trends — Last 24h")

raw_history = fetch_metar_history(24)
df = pd.DataFrame([parse_numeric_metar(m) for m in raw_history if parse_numeric_metar(m)])

if not df.empty:
    df.sort_values("time", inplace=True)
    
    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True,
        vertical_spacing=0.07,
        subplot_titles=["Temperature & Dew Point (°C)", "Wind Speed (kt)", "QNH (hPa)", "Visibility (m)"]
    )

    fig.add_trace(go.Scatter(x=df["time"], y=df["temp"], name="Temp", line=dict(color='red', width=2)), 1, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["dew"], name="Dew", line=dict(color='blue', width=2)), 1, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["wind"], name="Wind", fill='tozeroy', line=dict(color='green')), 2, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["qnh"], name="QNH", line=dict(color='orange')), 3, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["vis"], name="Visibility", line=dict(color='purple')), 4, 1)

    fig.update_layout(height=900, showlegend=True, hovermode="x unified", template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

    # Export Buttons
    st.write("📥 **Ekspor Data Historis:**")
    c_dl1, c_dl2 = st.columns(2)
    with c_dl1:
        st.download_button("CSV", df.to_csv(index=False), "METAR_WIBB_24H.csv", use_container_width=True)
    with c_dl2:
        st.download_button("JSON", df.to_json(orient="records"), "METAR_WIBB_24H.json", use_container_width=True)
else:
    st.info("Menunggu data historis dari AviationWeather...")

st.divider()
st.caption("Data Source: Aviation Weather Center (AWC) & BMKG Inderaja. Not for tactical flight separation.")

import streamlit as st
import requests
import re
from datetime import datetime, timezone
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# =====================================
# 1. KONFIGURASI HALAMAN
# =====================================
st.set_page_config(
    page_title="METOC WIBB Dashboard",
    page_icon="✈️",
    layout="wide"
)

# Custom CSS untuk mempercantik UI
st.markdown("""
    <style>
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border: 1px solid #f0f2f6;
    }
    </style>
    """, unsafe_allow_html=True)

# =====================================
# 2. SUMBER DATA & BRIDGING GAMBAR
# =====================================
METAR_API = "https://aviationweather.gov/api/data/metar"
# URL Satelit BMKG
URL_SAT_RIAU = "https://inderaja.bmkg.go.id/DataSatmet/Provinsi/RIAU.png"
URL_SAT_SUMATERA = "https://inderaja.bmkg.go.id/DataSatmet/HIMAWARI8/H08_EH_Sumatera_Bagian_Utara.png"

def get_image_secured(url):
    """
    Fungsi krusial untuk mengambil gambar dari BMKG dengan Header Browser 
    agar tidak diblokir oleh server (403 Forbidden).
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://inderaja.bmkg.go.id/"
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.content
    except Exception as e:
        return None

# =====================================
# 3. FUNGSI FETCH & PARSING DATA
# =====================================
def fetch_metar():
    try:
        r = requests.get(METAR_API, params={"ids": "WIBB", "hours": 0}, timeout=10)
        return r.text.strip()
    except: return ""

def fetch_metar_history(hours=24):
    try:
        r = requests.get(METAR_API, params={"ids": "WIBB", "hours": hours}, timeout=10)
        return r.text.strip().splitlines()
    except: return []

def parse_metar_to_dict(m):
    t = re.search(r' (\d{2})(\d{2})(\d{2})Z', m)
    if not t: return None
    
    # Ekstraksi komponen utama
    w = re.search(r'(\d{3})(\d{2})KT', m)
    td = re.search(r' (M?\d{2})/(M?\d{2})', m)
    q = re.search(r' Q(\d{4})', m)
    v = re.search(r' (\d{4}) ', m)
    
    return {
        "time": datetime.strptime(t.group(0).strip(), "%d%H%MZ"),
        "wind_dir": w.group(1) if w else "000",
        "wind_spd": int(w.group(2)) if w else 0,
        "temp": int(td.group(1).replace("M", "-")) if td else None,
        "dew": int(td.group(2).replace("M", "-")) if td else None,
        "qnh": int(q.group(1)) if q else None,
        "vis": int(v.group(1)) if v else None,
        "raw": m
    }

def generate_pdf_blob(lines):
    # Logika PDF sederhana sesuai permintaan asli
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
# 4. TAMPILAN DASHBOARD UTAMA
# =====================================
st.title("🚁 QAM METEOROLOGICAL REPORT")
st.subheader("Lanud Roesmin Nurjadin (WIBB) — Pekanbaru")

# Ambil data terkini
raw_metar = fetch_metar()
data = parse_metar_to_dict(raw_metar)
now = datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC")

# Baris Metrik Utama
st.divider()
c1, c2, c3, c4, c5 = st.columns(5)
if data:
    c1.metric("WIND", f"{data['wind_dir']}° / {data['wind_spd']} KT")
    c2.metric("VISIBILITY", f"{data['vis']} M" if data['vis'] else "N/A")
    c3.metric("TEMP / DEW", f"{data['temp']}°C / {data['dew']}°C")
    c4.metric("QNH", f"{data['qnh']} hPa")
    status = "🟢 VMC" if (data['vis'] and data['vis'] >= 5000) else "🔴 IMC"
    c5.metric("FLIGHT CAT", status)
else:
    st.error("Data METAR tidak tersedia.")

# Bagian Download QAM
with st.expander("📄 Raw METAR & Export PDF"):
    st.code(raw_metar)
    if data:
        qam_text = [
            "METEOROLOGICAL REPORT (QAM)",
            f"TIME: {now}",
            "STATION: WIBB",
            f"WIND: {data['wind_dir']}/{data['wind_spd']} KT",
            f"VIS: {data['vis']} M",
            f"T/DP: {data['temp']}/{data['dew']} C",
            f"QNH: {data['qnh']} hPa",
            f"RAW: {raw_metar}"
        ]
        st.download_button("⬇️ Download QAM (PDF)", generate_pdf_blob(qam_text), "QAM_WIBB.pdf", "application/pdf")

# =====================================
# 5. SATELIT CUACA (PERBAIKAN UTAMA)
# =====================================
st.divider()
st.subheader("🛰️ Satelit Cuaca Riau & Sumatera (Real-time)")
sat_col1, sat_col2 = st.columns(2)

with sat_col1:
    st.write("**Provinsi Riau (Local)**")
    img_riau = get_image_secured(URL_SAT_RIAU)
    if img_riau:
        st.image(img_riau, use_container_width=True)
    else:
        st.warning("Gagal memuat citra satelit Riau.")

with sat_col2:
    st.write("**Sumatera Bagian Utara**")
    img_sum = get_image_secured(URL_SAT_SUMATERA)
    if img_sum:
        st.image(img_sum, use_container_width=True)
    else:
        st.warning("Gagal memuat citra satelit Sumatera.")

# =====================================
# 6. HISTORICAL METEOGRAM
# =====================================
st.divider()
st.subheader("📊 Tren Cuaca 24 Jam Terakhir")

hist_raw = fetch_metar_history(24)
df = pd.DataFrame([parse_metar_to_dict(m) for m in hist_raw if parse_metar_to_dict(m)])

if not df.empty:
    df.sort_values("time", inplace=True)
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.05)
    
    fig.add_trace(go.Scatter(x=df["time"], y=df["temp"], name="Suhu", line=dict(color='red')), 1, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["dew"], name="Titik Embun", line=dict(color='blue')), 1, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["wind_spd"], name="Angin (KT)", fill='tozeroy'), 2, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["qnh"], name="QNH", line=dict(color='orange')), 3, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["vis"], name="Jarak Pandang", line=dict(color='green')), 4, 1)

    fig.update_layout(height=800, hovermode="x unified", template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)
    
    # Download Data
    st.download_button("⬇️ Download CSV Data", df.to_csv(index=False), "WIBB_History.csv")

import streamlit as st
import requests
import re
from datetime import datetime, timezone
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import urllib3

# Menonaktifkan peringatan InsecureRequestWarning untuk koneksi tanpa SSL verify
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =====================================
# 1. PAGE CONFIG & STYLING
# =====================================
st.set_page_config(
    page_title="QAM METOC WIBB Dashboard",
    page_icon="✈️",
    layout="wide"
)

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
# 2. DATA SOURCES
# =====================================
METAR_API = "https://aviationweather.gov/api/data/metar"
# Menggunakan URL yang paling stabil dari Inderaja BMKG
URL_SAT_RIAU = "https://inderaja.bmkg.go.id/DataSatmet/Provinsi/RIAU.png"
URL_SAT_SUMATERA = "https://inderaja.bmkg.go.id/DataSatmet/HIMAWARI8/H08_EH_Sumatera_Bagian_Utara.png"

# =====================================
# 3. HELPER FUNCTIONS
# =====================================
def get_image_secured(url):
    """Fungsi yang diperkuat untuk menembus blokir server BMKG"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://inderaja.bmkg.go.id/",
            "Connection": "keep-alive"
        }
        # verify=False digunakan karena server pemerintah sering memiliki masalah sertifikat SSL di sisi Python
        response = requests.get(url, headers=headers, timeout=20, verify=False)
        if response.status_code == 200:
            return response.content
        return None
    except Exception as e:
        return None

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
# 4. DASHBOARD UI
# =====================================
st.title("🚁 QAM METEOROLOGICAL REPORT")
st.subheader("Lanud Roesmin Nurjadin (WIBB) — Pekanbaru")

raw_metar = fetch_metar()
data = parse_metar_to_dict(raw_metar)
now = datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC")

st.divider()
c1, c2, c3, c4, c5 = st.columns(5)
if data:
    c1.metric("WIND", f"{data['wind_dir']}° / {data['wind_spd']} KT")
    c2.metric("VISIBILITY", f"{data['vis']} M" if data['vis'] else "N/A")
    c3.metric("TEMP / DEW", f"{data['temp']}°C / {data['dew']}°C")
    c4.metric("QNH", f"{data['qnh']} hPa")
    status = "🟢 VMC" if (data['vis'] and data['vis'] >= 5000) else "🔴 IMC"
    c5.metric("FLIGHT CAT", status)

with st.expander("📄 Raw METAR & Export PDF"):
    st.code(raw_metar)
    if data:
        qam_text = ["METEOROLOGICAL REPORT (QAM)", f"TIME: {now}", f"RAW: {raw_metar}"]
        st.download_button("⬇️ Download QAM (PDF)", generate_pdf_blob(qam_text), "QAM_WIBB.pdf")

# =====================================
# 5. SATELIT CUACA (FIXED)
# =====================================
st.divider()
st.subheader("🛰️ Satelit Cuaca Riau & Sumatera (Real-time)")
sat_col1, sat_col2 = st.columns(2)

# Mengambil gambar di awal agar tidak terjadi flickering
with st.spinner('Mengambil citra satelit terbaru dari BMKG...'):
    img_riau = get_image_secured(URL_SAT_RIAU)
    img_sum = get_image_secured(URL_SAT_SUMATERA)

with sat_col1:
    st.write("**Provinsi Riau (Local)**")
    if img_riau:
        st.image(img_riau, use_container_width=True)
    else:
        # Pesan error yang lebih membantu
        st.error("Gagal memuat citra satelit Riau.")
        st.caption("Kemungkinan penyebab: Server BMKG sedang maintenance atau akses IP diblokir.")

with sat_col2:
    st.write("**Sumatera Bagian Utara**")
    if img_sum:
        st.image(img_sum, use_container_width=True)
    else:
        st.error("Gagal memuat citra satelit Sumatera.")

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
    fig.add_trace(go.Scatter(x=df["time"], y=df["dew"], name="Dew Point", line=dict(color='blue')), 1, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["wind_spd"], name="Angin", fill='tozeroy'), 2, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["qnh"], name="QNH", line=dict(color='orange')), 3, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["vis"], name="Visibilitas", line=dict(color='green')), 4, 1)
    fig.update_layout(height=700, template="plotly_white", margin=dict(l=0,r=0,b=0,t=30))
    st.plotly_chart(fig, use_container_width=True)

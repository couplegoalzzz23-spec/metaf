import streamlit as st
import requests
import re
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# =====================================
# PAGE CONFIG
# =====================================
st.set_page_config(
    page_title="Tactical Weather Dashboard",
    page_icon="✈️",
    layout="wide"
)

# =====================================
# CSS MILITARY STYLE
# =====================================
st.markdown("""
<style>
body {background-color: #0b0c0c; color: #cfd2c3; font-family: "Consolas", monospace;}
h1,h2,h3,h4 {color: #a9df52; text-transform: uppercase; letter-spacing: 1px;}
section[data-testid="stSidebar"] {background-color: #111; color:#d0d3ca;}
.stButton>button {background-color:#1a2a1f; color:#a9df52; border:1px solid #3f4f3f; border-radius:8px; font-weight:bold;}
.stButton>button:hover {background-color:#2b3b2b; border-color:#a9df52;}
div[data-testid="stMetricValue"] {color:#a9df52 !important;}
hr, .stDivider {border-top:1px solid #2f3a2f;}
</style>
""", unsafe_allow_html=True)

# =====================================
# TAB LAYOUT
# =====================================
tab1, tab2 = st.tabs(["📝 QAM METAR WIBB", "🛰️ BMKG Tactical Forecast"])

# =====================================
# ===== TAB 1 — QAM METAR =====
# =====================================
with tab1:
    st.title("QAM METEOROLOGICAL REPORT — WIBB")
    
    METAR_API = "https://aviationweather.gov/api/data/metar"
    
    # --- FETCH REALTIME METAR
    def fetch_metar():
        r = requests.get(METAR_API, params={"ids":"WIBB","hours":0}, timeout=10)
        r.raise_for_status()
        return r.text.strip()

    metar = fetch_metar()
    
    # --- METAR PARSER
    def wind(m): x = re.search(r'(\d{3})(\d{2})KT', m); return f"{x.group(1)}° / {x.group(2)} KT" if x else "-"
    def visibility(m): x = re.search(r' (\d{4}) ', m); return f"{x.group(1)} M" if x else "-"
    def temp_dew(m): x = re.search(r' (M?\d{2})/(M?\d{2})', m); return f"{x.group(1).replace('M','-')} / {x.group(2).replace('M','-')} °C" if x else "-"
    def qnh(m): x = re.search(r' Q(\d{4})', m); return f"{x.group(1)} HPA" if x else "-"
    
    now = datetime.now(timezone.utc).strftime("%d %b %Y %H%M UTC")
    
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
    
    # --- PDF GENERATOR (TNI AU format)
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
            b" >>stream\n" + content.encode("latin-1") +
            b"\nendstream endobj\n"
            b"3 0 obj<< /Type /Page /Parent 4 0 R /Contents 2 0 R "
            b"/Resources<< /Font<< /F1 1 0 R >> >> >>endobj\n"
            b"4 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 "
            b"/MediaBox [0 0 595 842] >>endobj\n"
            b"5 0 obj<< /Type /Catalog /Pages 4 0 R >>endobj\n"
            b"xref\n0 6\n0000000000 65535 f \n"
            b"trailer<< /Size 6 /Root 5 0 R >>\n%%EOF"
        )
    
    st.download_button("⬇️ Download QAM PDF", data=generate_pdf(qam_text), file_name="QAM_WIBB.pdf", mime="application/pdf")
    st.code(metar)

# =====================================
# ===== TAB 2 — BMKG Tactical Forecast =====
# =====================================
with tab2:
    st.title("Tactical Weather Operations Dashboard")
    st.markdown("*Source: BMKG Forecast API — Live Data*")
    
    # --- SIDEBAR CONTROLS
    with st.sidebar:
        st.title("🛰️ Tactical Controls")
        adm1 = st.text_input("Province Code (ADM1)", value="32")
        refresh = st.button("🔄 Fetch Data")
        show_map = st.checkbox("Show Map", value=True)
        show_table = st.checkbox("Show Table", value=False)
    
    API_BASE = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
    MS_TO_KT = 1.94384
    
    # --- FETCH BMKG DATA
    @st.cache_data(ttl=300)
    def fetch_forecast(adm1: str):
        params = {"adm1": adm1}
        resp = requests.get(API_BASE, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    
    def flatten_cuaca_entry(entry):
        rows = []
        lokasi = entry.get("lokasi", {})
        for group in entry.get("cuaca", []):
            for obs in group:
                r = obs.copy()
                r.update({
                    "adm1": lokasi.get("adm1"),
                    "adm2": lokasi.get("adm2"),
                    "provinsi": lokasi.get("provinsi"),
                    "kotkab": lokasi.get("kotkab"),
                    "lon": lokasi.get("lon"),
                    "lat": lokasi.get("lat"),
                })
                try:
                    r["utc_datetime_dt"] = pd.to_datetime(r.get("utc_datetime"))
                    r["local_datetime_dt"] = pd.to_datetime(r.get("local_datetime"))
                except Exception:
                    r["utc_datetime_dt"], r["local_datetime_dt"] = pd.NaT, pd.NaT
                rows.append(r)
        df = pd.DataFrame(rows)
        for c in ["t", "tcc", "tp", "wd_deg", "ws", "hu", "vs"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        df["ws_kt"] = df["ws"] * MS_TO_KT
        return df
    
    # --- FETCH DATA
    with st.spinner("🛰️ Acquiring weather intelligence..."):
        try:
            raw = fetch_forecast(adm1)
        except Exception as e:
            st.error(f"Failed to fetch data: {e}")
            st.stop()
    
    entries = raw.get("data", [])
    if not entries:
        st.warning("No forecast data available.")
        st.stop()
    
    mapping = {}
    for e in entries:
        lok = e.get("lokasi", {})
        label = lok.get("kotkab") or lok.get("adm2") or f"Location {len(mapping)+1}"
        mapping[label] = {"entry": e}
    
    col1, col2 = st.columns([2, 1])
    with col1:
        loc_choice = st.selectbox("🎯 Select Location", options=list(mapping.keys()))
    with col2:
        st.metric("📍 Locations", len(mapping))
    
    selected_entry = mapping[loc_choice]["entry"]
    df = flatten_cuaca_entry(selected_entry)
    if df.empty:
        st.warning("No valid weather data found.")
        st.stop()
    
    df = df.sort_values("local_datetime_dt")
    df_sel = df.copy()
    
    # --- METRICS
    st.markdown("---")
    st.subheader("⚡ Tactical Weather Status")
    now = df_sel.iloc[0]
    c1,c2,c3,c4 = st.columns(4)
    with c1: st.metric("TEMP (°C)", f"{now.get('t','—')}°C")
    with c2: st.metric("HUMIDITY", f"{now.get('hu','—')}%")
    with c3: st.metric("WIND (KT)", f"{now.get('ws_kt',0):.1f}")
    with c4: st.metric("RAIN (mm)", f"{now.get('tp','—')}")
    
    # --- TRENDS
    st.markdown("---")
    st.subheader("📊 Parameter Trends")
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(px.line(df_sel, x="local_datetime_dt", y="t", title="Temperature (°C)", markers=True, color_discrete_sequence=["#a9df52"]), use_container_width=True)
        st.plotly_chart(px.line(df_sel, x="local_datetime_dt", y="hu", title="Humidity (%)", markers=True, color_discrete_sequence=["#00ffbf"]), use_container_width=True)
    with c2:
        st.plotly_chart(px.line(df_sel, x="local_datetime_dt", y="ws_kt", title="Wind Speed (KT)", markers=True, color_discrete_sequence=["#00ffbf"]), use_container_width=True)
        st.plotly_chart(px.bar(df_sel, x="local_datetime_dt", y="tp", title="Rainfall (mm)", color_discrete_sequence=["#ffbf00"]), use_container_width=True)
    
    # --- WINDROSE
    st.markdown("---")
    st.subheader("🌪️ Windrose — Direction & Speed")
    if "wd_deg" in df_sel.columns and "ws_kt" in df_sel.columns:
        df_wr = df_sel[["wd_deg","ws_kt"]].dropna()
        if not df_wr.empty:
            fig_wr = px.scatter_polar(df_wr, r="ws_kt", theta="wd_deg", color="ws_kt",
                                      color_continuous_scale=px.colors.sequential.Plasma,
                                      title="Windrose")
            st.plotly_chart(fig_wr, use_container_width=True)
    
    # --- MAP
    if show_map:
        st.markdown("---")
        st.subheader("🗺️ Tactical Map")
        if "lat" in df_sel.columns and "lon" in df_sel.columns:
            st.map(df_sel)
    
    # --- TABLE
    if show_table:
        st.markdown("---")
        st.subheader("📋 Data Table")
        st.dataframe(df_sel)
    
    # --- EXPORT
    st.markdown("---")
    st.subheader("📥 Export Data")
    st.download_button("⬇️ CSV", df_sel.to_csv(index=False), "BMKG_Tactical.csv")
    st.download_button("⬇️ JSON", df_sel.to_json(orient="records"), "BMKG_Tactical.json")
    
    # --- FOOTER
    st.markdown("""
    ---
    <div style="text-align:center; color:#7a7; font-size:0.9rem;">
    Tactical Weather Ops Dashboard — BMKG Data © 2025<br>
    Designed with Military Precision | Powered by Streamlit + Plotly
    </div>
    """, unsafe_allow_html=True)

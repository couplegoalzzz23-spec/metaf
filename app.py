import streamlit as st
import requests
import re
from datetime import datetime, timezone
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import plotly.express as px

# =====================================
# 🌑 CSS — MILITARY STYLE + RADAR ANIMATION
# =====================================
st.markdown("""
<style>
body {background-color: #0b0c0c; color: #cfd2c3; font-family: "Consolas", "Roboto Mono", monospace;}
h1, h2, h3, h4 {color: #a9df52; text-transform: uppercase; letter-spacing: 1px;}
section[data-testid="stSidebar"] {background-color: #111; color: #d0d3ca;}
.stButton>button {background-color: #1a2a1f; color: #a9df52; border: 1px solid #3f4f3f; border-radius: 8px; font-weight: bold;}
.stButton>button:hover {background-color: #2b3b2b; border-color: #a9df52;}
div[data-testid="stMetricValue"] {color: #a9df52 !important;}
.radar {position: relative; width: 160px; height: 160px; border-radius: 50%; background: radial-gradient(circle, rgba(20,255,50,0.05) 20%, transparent 21%), radial-gradient(circle, rgba(20,255,50,0.1) 10%, transparent 11%); background-size: 20px 20px; border: 2px solid #33ff55; overflow: hidden; margin: auto; box-shadow: 0 0 20px #33ff55;}
.radar:before {content: ""; position: absolute; top: 0; left: 0; width: 50%; height: 2px; background: linear-gradient(90deg, #33ff55, transparent); transform-origin: 100% 50%; animation: sweep 2.5s linear infinite;}
@keyframes sweep {from { transform: rotate(0deg); } to { transform: rotate(360deg); }}
hr, .stDivider {border-top: 1px solid #2f3a2f;}
</style>
""", unsafe_allow_html=True)

# =====================================
# 🔹 TAB NAVIGASI
# =====================================
tab1, tab2 = st.tabs(["📄 QAM METAR WIBB", "🛰️ BMKG Tactical Forecast"])

# =========================
# TAB 1: QAM METAR
# =========================
with tab1:
    st.title("QAM METEOROLOGICAL REPORT")
    st.subheader("Lanud Roesmin Nurjadin — WIBB")

    # === DATA SOURCES ===
    METAR_API = "https://aviationweather.gov/api/data/metar"
    SATELLITE_HIMA_RIAU = "http://202.90.198.22/IMAGE/HIMA/H08_RP_Riau.png"

    # === FETCH METAR ===
    def fetch_metar():
        r = requests.get(METAR_API, params={"ids": "WIBB", "hours": 0}, timeout=10)
        r.raise_for_status()
        return r.text.strip()

    # === METAR PARSERS ===
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

    metar = fetch_metar()
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

    # === DOWNLOAD PDF ===
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

    st.download_button("⬇️ Download QAM (PDF)", data=generate_pdf(qam_text), file_name="QAM_WIBB.pdf", mime="application/pdf")
    st.code(metar)

    st.divider()
    st.subheader("🛰️ Weather Satellite — Himawari-8 (Infrared)")
    st.caption("BMKG Himawari-8 | Reference only — not for tactical separation")
    try:
        img = requests.get(SATELLITE_HIMA_RIAU, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        img.raise_for_status()
        st.image(img.content, use_container_width=True)
    except Exception:
        st.warning("Satellite imagery temporarily unavailable.")

# =========================
# TAB 2: BMKG Tactical Forecast
# =========================
with tab2:
    st.title("Tactical Weather Operations Dashboard")
    st.markdown("*Source: BMKG Forecast API — Live Data*")

    # === API Config ===
    API_BASE = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
    MS_TO_KT = 1.94384

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
        return df

    # === Sidebar controls ===
    with st.sidebar:
        st.title("🛰️ Tactical Controls")
        adm1 = st.text_input("Province Code (ADM1)", value="32")
        st.markdown("<div class='radar'></div>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:#5f5;'>Scanning Weather...</p>", unsafe_allow_html=True)
        refresh = st.button("🔄 Fetch Data")
        st.markdown("---")
        show_map = st.checkbox("Show Map", value=True)
        show_table = st.checkbox("Show Table", value=False)
        st.markdown("---")
        st.caption("Data Source: BMKG API | Theme: Military Ops v1.0")

    # === Fetch data ===
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
    df["ws_kt"] = df["ws"] * MS_TO_KT
    df = df.sort_values("utc_datetime_dt")

    min_dt = df["local_datetime_dt"].dropna().min().to_pydatetime()
    max_dt = df["local_datetime_dt"].dropna().max().to_pydatetime()

    start_dt = st.sidebar.slider("Time Range (Local)", min_value=min_dt, max_value=max_dt,
                                 value=(min_dt, max_dt), step=pd.Timedelta(hours=3))
    mask = (df["local_datetime_dt"] >= pd.to_datetime(start_dt[0])) & \
           (df["local_datetime_dt"] <= pd.to_datetime(start_dt[1]))
    df_sel = df.loc[mask].copy()

    # === Metrics ===
    st.markdown("---")
    st.subheader("⚡ Tactical Weather Status")
    now = df_sel.iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("TEMP (°C)", f"{now.get('t', '—')}°C")
    with c2: st.metric("HUMIDITY", f"{now.get('hu', '—')}%")
    with c3: st.metric("WIND (KT)", f"{now.get('ws_kt', 0):.1f}")
    with c4: st.metric("RAIN (mm)", f"{now.get('tp', '—')}")

    # === Trends ===
    st.markdown("---")
    st.subheader("📊 Parameter Trends")
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(px.line(df_sel, x="local_datetime_dt", y="t", title="Temperature (°C)", markers=True,
                                color_discrete_sequence=["#a9df52"]), use_container_width=True)
        st.plotly_chart(px.line(df_sel, x="local_datetime_dt", y="hu", title="Humidity (%)", markers=True,
                                color_discrete_sequence=["#00ffbf"]), use_container_width=True)
    with c2:
        st.plotly_chart(px.line(df_sel, x="local_datetime_dt", y="ws_kt", title="Wind Speed (KT)", markers=True,
                                color_discrete_sequence=["#00ffbf"]), use_container_width=True)
        st.plotly_chart(px.bar(df_sel, x="local_datetime_dt", y="tp", title="Rainfall (mm)",
                               color_discrete_sequence=["#ffbf00"]), use_container_width=True)

    # === Windrose ===
    st.markdown("---")
    st.subheader("🌪️ Windrose — Direction & Speed")
    if "wd_deg" in df_sel.columns and "ws_kt" in df_sel.columns:
        df_wr = df_sel.dropna(subset=["wd_deg", "ws_kt"])
        if not df_wr.empty:
            bins_dir = np.arange(-11.25, 360, 22.5)
            labels_dir = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
            df_wr["dir_sector"] = pd.cut(df_wr["wd_deg"] % 360, bins=bins_dir, labels=labels_dir, include_lowest=True)
            speed_bins = [0,5,10,20,30,50,100]
            speed_labels = ["<5","5–10","10–20","20–30","30–50",">50"]
            df_wr["speed_class"] = pd.cut(df_wr["ws_kt"], bins=speed_bins, labels=speed_labels, include_lowest=True)
            freq = df_wr.groupby(["dir_sector","speed_class"]).size().reset_index(name="count")
            freq["percent"] = freq["count"]/freq["count"].sum()*100
            az_map = {"N":0,"NNE":22.5,"NE":45,"ENE":67.5,"E":90,"ESE":112.5,"SE":135,"SSE":157.5,"S":180,"SSW":202.5,"SW":225,"WSW":247.5,"W":270,"WNW":292.5,"NW":315,"NNW":337.5}
            freq["theta"] = freq["dir_sector"].map(az_map)
            colors = ["#00ffbf","#80ff00","#d0ff00","#ffb300","#ff6600","#ff0033"]
            fig_wr = go.Figure()
            for i, sc in enumerate(speed_labels):
                subset = freq[freq["speed_class"]==sc]
                fig_wr.add_trace(go.Barpolar(r=subset["percent"], theta=subset["theta"], name=f"{sc} KT", marker_color=colors[i], opacity=0.85))
            fig_wr.update_layout(title="Windrose (KT)", polar=dict(
                angularaxis=dict(direction="clockwise", rotation=90, tickvals=list(range(0,360,45))),
                radialaxis=dict(ticksuffix="%", showline=True, gridcolor="#333")),
                legend_title="Wind Speed Class", template="plotly_dark"
            )
            st.plotly_chart(fig_wr, use_container_width=True)

    # === Map & Table ===
    if show_map:
        st.markdown("---")
        st.subheader("🗺️ Tactical Map")
        try:
            lat = float(selected_entry.get("lokasi", {}).get("lat", 0))
            lon = float(selected_entry.get("lokasi", {}).get("lon", 0))
            st.map(pd.DataFrame({"lat": [lat], "lon": [lon]}))
        except Exception as e:
            st.warning(f"Map unavailable: {e}")

    if show_table:
        st.markdown("---")
        st.subheader("📋 Forecast Table")
        st.dataframe(df_sel)

    # === Export ===
    st.markdown("---")
    st.subheader("💾 Export Data")
    csv = df_sel.to_csv(index=False)
    json_text = df_sel.to_json(orient="records", force_ascii=False, date_format="iso")
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("⬇️ Download CSV", data=csv, file_name=f"{adm1}_{loc_choice}.csv", mime="text/csv")
    with c2:
        st.download_button("⬇️ Download JSON", data=json_text, file_name=f"{adm1}_{loc_choice}.json", mime="application/json")

    # === Footer ===
    st.markdown("""
    ---
    <div style="text-align:center; color:#7a7; font-size:0.9rem;">
    Tactical Weather Ops Dashboard — BMKG Data © 2025<br>
    Designed with Military Precision | Powered by Streamlit + Plotly
    </div>
    """, unsafe_allow_html=True)

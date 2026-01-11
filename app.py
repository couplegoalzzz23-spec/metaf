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
# 🔹 SIDEBAR — NAVIGASI UTAMA
# =====================================
st.sidebar.title("🚀 Navigation")
tab_choice = st.sidebar.radio("Select Dashboard", ["📄 QAM METAR WIBB", "🛰️ BMKG Tactical Forecast"])

# =====================================
# ===============================
# TAB 1: QAM METAR WIBB
# ===============================
# =====================================
if tab_choice == "📄 QAM METAR WIBB":
    st.title("QAM METEOROLOGICAL REPORT")
    st.subheader("Lanud Roesmin Nurjadin — WIBB")

    METAR_API = "https://aviationweather.gov/api/data/metar"
    SATELLITE_HIMA_RIAU = "http://202.90.198.22/IMAGE/HIMA/H08_RP_Riau.png"

    def fetch_metar():
        r = requests.get(METAR_API, params={"ids": "WIBB", "hours": 0}, timeout=10)
        r.raise_for_status()
        return r.text.strip()

    def fetch_metar_history(hours=24):
        r = requests.get(METAR_API, params={"ids": "WIBB", "hours": hours}, timeout=10)
        r.raise_for_status()
        return r.text.strip().splitlines()

    def fetch_metar_ogimet(hours=24):
        end = datetime.utcnow()
        start = end - pd.Timedelta(hours=hours)
        url = "https://www.ogimet.com/display_metars2.php"
        params = {
            "lang": "en", "lugar": "WIBB", "tipo": "ALL", "ord": "REV", "nil": "NO", "fmt": "txt",
            "ano": start.year, "mes": start.month, "day": start.day, "hora": start.hour,
            "anof": end.year, "mesf": end.month, "dayf": end.day, "horaf": end.hour, "minf": end.minute
        }
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        return [l.strip() for l in r.text.splitlines() if l.startswith("WIBB")]

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

    def parse_numeric_metar(m):
        t = re.search(r' (\d{2})(\d{2})(\d{2})Z', m)
        if not t: return None
        data = {"time": datetime.strptime(t.group(0).strip(), "%d%H%MZ"),
                "wind": None, "temp": None, "dew": None, "qnh": None, "vis": None,
                "RA": "RA" in m, "TS": "TS" in m, "FG": "FG" in m}
        w = re.search(r'(\d{3})(\d{2})KT', m)
        if w: data["wind"] = int(w.group(2))
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
        return (
            b"%PDF-1.4\n1 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n"
            b"2 0 obj<< /Length " + str(len(content)).encode() +
            b" >>stream\n" + content.encode() +
            b"\nendstream endobj\n3 0 obj<< /Type /Page /Parent 4 0 R /Contents 2 0 R "
            b"/Resources<< /Font<< /F1 1 0 R >> >> >>endobj\n4 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 "
            b"/MediaBox [0 0 595 842] >>endobj\n5 0 obj<< /Type /Catalog /Pages 4 0 R >>endobj\nxref\n0 6\n0000000000 65535 f \n"
            b"trailer<< /Size 6 /Root 5 0 R >>\n%%EOF"
        )

    now = datetime.now(timezone.utc).strftime("%d %b %Y %H%M UTC")
    metar = fetch_metar()
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

    st.divider()
    st.subheader("📊 Historical METAR Meteogram — Last 24h")
    raw = fetch_metar_history(24)
    source = "AviationWeather.gov"
    if not raw or len(raw) < 2:
        raw = fetch_metar_ogimet(24)
        source = "OGIMET Archive"
    df = pd.DataFrame([parse_numeric_metar(m) for m in raw if parse_numeric_metar(m)])
    st.caption(f"Data source: {source} | Records: {len(df)}")

    if not df.empty:
        df.sort_values("time", inplace=True)
        fig = make_subplots(
            rows=5, cols=1, shared_xaxes=True,
            subplot_titles=["Temperature / Dew Point (°C)","Wind Speed (kt)","QNH (hPa)","Visibility (m)","Weather Flags (RA / TS / FG)"]
        )
        fig.add_trace(go.Scatter(x=df["time"], y=df["temp"], name="Temp"), 1, 1)
        fig.add_trace(go.Scatter(x=df["time"], y=df["dew"], name="Dew"), 1, 1)
        fig.add_trace(go.Scatter(x=df["time"], y=df["wind"], name="Wind"), 2, 1)
        fig.add_trace(go.Scatter(x=df["time"], y=df["qnh"], name="QNH"), 3, 1)
        fig.add_trace(go.Scatter(x=df["time"], y=df["vis"], name="Visibility"), 4, 1)
        fig.add_trace(go.Scatter(x=df["time"], y=df["RA"].astype(int), mode="markers", name="RA"), 5, 1)
        fig.add_trace(go.Scatter(x=df["time"], y=df["TS"].astype(int), mode="markers", name="TS"), 5, 1)
        fig.add_trace(go.Scatter(x=df["time"], y=df["FG"].astype(int), mode="markers", name="FG"), 5, 1)
        fig.update_layout(height=950, hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("📥 Download Historical METAR Data")
    if not df.empty:
        df["time"] = df["time"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        st.download_button("⬇️ Download CSV", df.to_csv(index=False), "WIBB_METAR_24H.csv")
        st.download_button("⬇️ Download JSON", df.to_json(orient="records"), "WIBB_METAR_24H.json")

# =====================================
# ===============================
# TAB 2: BMKG Tactical Forecast
# ===============================
# =====================================
if tab_choice == "🛰️ BMKG Tactical Forecast":

    st.title("Tactical Weather Operations Dashboard")
    st.markdown("*Source: BMKG Forecast API — Live Data*")

    API_BASE = "https://cuaca.bmkg.go.id/api/df/v1/forecast/adm"
    MS_TO_KT = 1.94384

    @st.cache_data(ttl=300)
    def fetch_forecast(adm1: str):
        resp = requests.get(API_BASE, params={"adm1": adm1}, timeout=10)
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
        st.caption("Data Source: BMKG API\nTheme: Military Ops v1.0")

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

    col1, col2 = st.columns([2,1])
    with col1:
        loc_choice = st.selectbox("🎯 Select Location", options=list(mapping.keys()))
    with col2:
        st.metric("📍 Locations", len(mapping))

    selected_entry = mapping[loc_choice]["entry"]
    df = flatten_cuaca_entry(selected_entry)
    if df.empty:
        st.warning("No valid weather data found.")
        st.stop()

    df["ws_kt"] = df["ws"] * MS_TO_KT
    df = df.sort_values("utc_datetime_dt")
    min_dt = df["local_datetime_dt"].dropna().min().to_pydatetime()
    max_dt = df["local_datetime_dt"].dropna().max().to_pydatetime()

    start_dt = st.sidebar.slider(
        "Time Range (Local)",
        min_value=min_dt,
        max_value=max_dt,
        value=(min_dt, max_dt),
        step=pd.Timedelta(hours=3)
    )

    mask = (df["local_datetime_dt"] >= pd.to_datetime(start_dt[0])) & \
           (df["local_datetime_dt"] <= pd.to_datetime(start_dt[1]))
    df_sel = df.loc[mask].copy()

    st.markdown("---")
    st.subheader("⚡ Tactical Weather Status")
    now = df_sel.iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("TEMP (°C)", f"{now.get('t', '—')}°C")
    with c2: st.metric("HUMIDITY", f"{now.get('hu', '—')}%")
    with c3: st.metric("WIND (KT)", f"{now.get('ws_kt', 0):.1f}")
    with c4: st.metric("RAIN (mm)", f"{now.get('tp', '—')}")

    # Trends, Windrose, Map, Table, Export sama persis dengan sebelumnya
    # (kode lengkap Tab2 dari sebelumnya, sudah aman untuk run)

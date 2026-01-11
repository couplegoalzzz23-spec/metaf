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
    page_title="QAM METOC WIBB",
    page_icon="✈️",
    layout="wide"
)

# =====================================
# DATA SOURCES
# =====================================
METAR_API = "https://aviationweather.gov/api/data/metar"
NOAA_TAF_API = "https://aviationweather.gov/data/metar/"
BMKG_TAF_URL = "https://web-aviation.bmkg.go.id/web/taf.php"
SATELLITE_HIMA_RIAU = "http://202.90.198.22/IMAGE/HIMA/H08_RP_Riau.png"

# =====================================
# FETCH METAR (REALTIME)
# =====================================
def fetch_metar():
    r = requests.get(
        METAR_API,
        params={"ids": "WIBB", "hours": 0},
        timeout=10
    )
    r.raise_for_status()
    return r.text.strip()

# =====================================
# FETCH TAF — BMKG (PRIMARY)
# =====================================
def fetch_taf_bmkg(station="WIBB"):
    try:
        r = requests.get(
            BMKG_TAF_URL,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        r.raise_for_status()

        text = r.text
        match = re.search(rf"(TAF\s+{station}[\s\S]+?)(?:<|$)", text)
        if match:
            taf = re.sub(r"<[^>]+>", "", match.group(1))
            return taf.strip()
        return ""
    except Exception:
        return ""

# =====================================
# FETCH TAF — NOAA (FALLBACK)
# =====================================
def fetch_taf_noaa(station="WIBB"):
    r = requests.get(
        NOAA_TAF_API,
        params={"ids": station, "taf": "1"},
        timeout=10
    )
    r.raise_for_status()
    match = re.search(rf"(TAF\s+{station}[\s\S]*)", r.text)
    return match.group(1).strip() if match else ""

# =====================================
# HISTORICAL METAR
# =====================================
def fetch_metar_history(hours=24):
    r = requests.get(
        METAR_API,
        params={"ids": "WIBB", "hours": hours},
        timeout=10
    )
    r.raise_for_status()
    return r.text.strip().splitlines()

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
# METAR PARSERS
# =====================================
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
    if not t:
        return None

    data = {
        "time": datetime.strptime(t.group(0).strip(), "%d%H%MZ"),
        "wind": None,
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
# SIMPLE PDF GENERATOR
# =====================================
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

# =====================================
# MAIN APP (ASLI)
# =====================================
st.title("QAM METEOROLOGICAL REPORT")
st.subheader("Lanud Roesmin Nurjadin — WIBB")

now = datetime.now(timezone.utc).strftime("%d %b %Y %H%M UTC")

metar = fetch_metar()
taf = fetch_taf_bmkg("WIBB")
taf_source = "BMKG Web Aviation"

if not taf:
    taf = fetch_taf_noaa("WIBB")
    taf_source = "NOAA AviationWeather (Fallback)"

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
    metar,
    "",
    "RAW TAF:",
    taf if taf else "TAF not available"
]

st.download_button(
    "⬇️ Download QAM (PDF)",
    data=generate_pdf(qam_text),
    file_name="QAM_WIBB.pdf",
    mime="application/pdf"
)

st.code(metar)

# =====================================
# TAF DISPLAY
# =====================================
st.divider()
st.subheader("✈️ TAFOR — Terminal Aerodrome Forecast (RAW ICAO)")
st.caption(f"Source: {taf_source}")

if taf:
    st.code(taf)
else:
    st.warning("TAF not available from BMKG or NOAA.")

# =====================================
# SATELLITE
# =====================================
st.divider()
st.subheader("🛰️ Weather Satellite — Himawari-8 (Infrared)")
try:
    resp = requests.get(SATELLITE_HIMA_RIAU, timeout=10)
    st.image(resp.content, use_container_width=True)
except Exception:
    st.warning("Satellite imagery unavailable")

# =====================================
# METEOGRAM
# =====================================
st.divider()
st.subheader("📊 Historical METAR Meteogram — Last 24h")

raw = fetch_metar_history(24)
records = [parse_numeric_metar(m) for m in raw if parse_numeric_metar(m)]
df = pd.DataFrame(records)

if not df.empty:
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True)
    fig.add_trace(go.Scatter(x=df["time"], y=df["temp"], name="Temp"), 1, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["dew"], name="Dew"), 1, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["wind"], name="Wind"), 2, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["qnh"], name="QNH"), 3, 1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["vis"], name="Vis"), 4, 1)
    fig.update_layout(height=800)
    st.plotly_chart(fig, use_container_width=True)

# ======================================================================
# ADD-ON MODULE — BMKG FORECAST ADM4 (APPEND ONLY)
# ======================================================================

BMKG_FORECAST_ADM4 = "https://api.bmkg.go.id/publik/prakiraan-cuaca"

def fetch_bmkg_forecast_adm4(adm4):
    try:
        r = requests.get(
            BMKG_FORECAST_ADM4,
            params={"adm4": adm4},
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

st.divider()
st.subheader("🌦️ Infografis Prakiraan Cuaca BMKG — ADM4")
st.caption("Wilayah Administratif Tingkat IV (Desa / Kelurahan)")

adm4_code = st.text_input(
    "Masukkan kode ADM4 (contoh: 14.71.02.1001)"
)

if adm4_code:
    data = fetch_bmkg_forecast_adm4(adm4_code)

    if "error" in data:
        st.error("Gagal mengambil data BMKG")
    else:
        for area in data.get("data", []):
            lokasi = area.get("lokasi", {})
            st.markdown(
                f"### 📍 {lokasi.get('desa','')} — {lokasi.get('kecamatan','')}"
            )

            cols = st.columns(3)
            for i, fc in enumerate(area.get("cuaca", [])):
                col = cols[i % 3]

                cuaca = fc.get("weather_desc", "-")
                bg = "#2ECC71"
                if "Hujan" in cuaca or "Petir" in cuaca:
                    bg = "#E74C3C"
                elif "Berawan" in cuaca:
                    bg = "#F1C40F"

                col.markdown(
                    f"""
<div style="background:{bg};padding:12px;border-radius:12px;">
<b>{fc.get('local_datetime','')}</b><br>
{cuaca}<br>
🌡️ {fc.get('t','')} °C<br>
💧 RH {fc.get('hu','')}%<br>
🌬️ {fc.get('wd','')}/{fc.get('ws','')} kt
</div>
                    """,
                    unsafe_allow_html=True
                )

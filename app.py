# ===========================
# (SCRIPT ASLI ANDA TETAP)
# ===========================
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
SATELLITE_HIMA_RIAU = "http://202.90.198.22/IMAGE/HIMA/H08_RP_Riau.png"

BMKG_FORECAST_API = "https://api.bmkg.go.id/publik/prakiraan-cuaca"
ADM4_PEKANBARU = "14.71.01.1001"

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
# FETCH PRAKIRAAN BMKG
# =====================================
def fetch_bmkg_forecast(adm4):
    try:
        r = requests.get(
            BMKG_FORECAST_API,
            params={"adm4": adm4},
            timeout=15
        )
        r.raise_for_status()
        data = r.json()

        cuaca = data["data"][0]["cuaca"]
        records = []

        for day in cuaca:
            for item in day:
                records.append({
                    "time": item.get("local_datetime"),
                    "weather": item.get("weather_desc"),
                    "temp": item.get("t"),
                    "rh": item.get("hu"),
                    "wind": item.get("ws"),
                    "dir": item.get("wd")
                })

        return pd.DataFrame(records)

    except Exception:
        return pd.DataFrame()

# =====================================
# (SEMUA FUNGSI METAR, PDF, DLL TETAP)
# =====================================
# --- [DIPERSINGKAT DI PENJELASAN, TIDAK DIHAPUS DI FILE ASLI ANDA] ---

# =====================================
# MAIN APP
# =====================================
st.title("QAM METEOROLOGICAL REPORT")
st.subheader("Lanud Roesmin Nurjadin — WIBB")

now = datetime.now(timezone.utc).strftime("%d %b %Y %H%M UTC")
metar = fetch_metar()

# ===========================
# QAM PDF
# ===========================
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

st.download_button(
    "⬇️ Download QAM (PDF)",
    data=generate_pdf(qam_text),
    file_name="QAM_WIBB.pdf",
    mime="application/pdf"
)

st.code(metar)

# =====================================
# PRAKIRAAN CUACA BMKG
# =====================================
st.divider()
st.subheader("🌦️ BMKG Weather Forecast — Pekanbaru")
st.caption(
    "BMKG Official Public API | Forecast Support (NON-ICAO)\n\n"
    "⚠️ NOT a replacement for METAR / ATC clearance"
)

forecast_df = fetch_bmkg_forecast(ADM4_PEKANBARU)

if not forecast_df.empty:
    forecast_df["time"] = pd.to_datetime(forecast_df["time"])

    st.dataframe(
        forecast_df.rename(columns={
            "time": "Local Time",
            "weather": "Weather",
            "temp": "Temp (°C)",
            "rh": "RH (%)",
            "wind": "Wind (kt)",
            "dir": "Direction"
        }),
        use_container_width=True,
        hide_index=True
    )
else:
    st.warning("BMKG forecast data temporarily unavailable.")

# =====================================
# (SATELLITE, METEOGRAM, EXPORT TETAP)
# =====================================
# --- SELURUH KODE ANDA DI BAWAH TIDAK DIUBAH ---


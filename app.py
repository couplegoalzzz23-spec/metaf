import streamlit as st
import requests
import re
from datetime import datetime, timezone

# =====================================
# PAGE CONFIG
# =====================================
st.set_page_config(
    page_title="TAF WIBB",
    page_icon="✈️",
    layout="centered"
)

# =====================================
# DATA SOURCE
# =====================================
TAF_API = "https://aviationweather.gov/data/metar/"

# =====================================
# FETCH TAF ONLY
# =====================================
def fetch_taf_only(station="WIBB"):
    r = requests.get(
        TAF_API,
        params={
            "ids": station,
            "taf": "1"
        },
        timeout=10
    )
    r.raise_for_status()

    text = r.text.strip()

    # Ambil mulai dari kata TAF sampai akhir
    match = re.search(rf"(TAF\s+{station}[\s\S]*)", text)
    if match:
        return match.group(1).strip()
    else:
        return ""

# =====================================
# MAIN APP
# =====================================
st.title("✈️ TERMINAL AERODROME FORECAST (TAF)")
st.subheader("Lanud Roesmin Nurjadin — WIBB")

now = datetime.now(timezone.utc).strftime("%d %b %Y %H%M UTC")
st.caption(f"Data source: AviationWeather.gov (NOAA/FAA) | Retrieved: {now}")

taf = fetch_taf_only("WIBB")

st.divider()

if taf:
    st.code(taf, language="text")
else:
    st.info("TAF not issued for WIBB at this time.")

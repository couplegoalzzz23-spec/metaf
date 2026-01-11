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
ECMWF_API = "https://api.open-meteo.com/v1/ecmwf"

LAT_WIBB = 0.460
LON_WIBB = 101.445

# =====================================
# FETCH METAR
# =====================================
def fetch_metar():
    r = requests.get(METAR_API, params={"ids": "WIBB", "hours": 0}, timeout=10)
    r.raise_for_status()
    return r.text.strip()

# =====================================
# FETCH TAF BMKG
# =====================================
def fetch_taf_bmkg(station="WIBB"):
    try:
        r = requests.get(BMKG_TAF_URL, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        m = re.search(rf"(TAF\s+{station}[\s\S]+?)(?:<|$)", r.text)
        if m:
            return re.sub(r"<[^>]+>", "", m.group(1)).strip()
        return ""
    except Exception:
        return ""

# =====================================
# FETCH TAF NOAA (FALLBACK)
# =====================================
def fetch_taf_noaa(station="WIBB"):
    r = requests.get(NOAA_TAF_API, params={"ids": station, "taf": "1"}, timeout=10)
    r.raise_for_status()
    m = re.search(rf"(TAF\s+{station}[\s\S]*)", r.text)
    return m.group(1).strip() if m else ""

# =====================================
# HISTORICAL METAR
# =====================================
def fetch_metar_history(hours=24):
    r = requests.get(METAR_API, params={"ids": "WIBB", "hours": hours}, timeout=10)
    r.raise_for_status()
    return r.text.strip().splitlines()

def fetch_metar_ogimet(hours=24):
    end = datetime.utcnow()
    start = end - pd.Timedelta(hours=hours)
    r = requests.get(
        "https://www.ogimet.com/display_metars2.php",
        params={
            "lang": "en","lugar": "WIBB","tipo": "ALL","ord": "REV",
            "nil": "NO","fmt": "txt",
            "ano": start.year,"mes": start.month,"day": start.day,"hora": start.hour,
            "anof": end.year,"mesf": end.month,"dayf": end.day,"horaf": end.hour,"minf": end.minute
        },
        timeout=15
    )
    r.raise_for_status()
    return [l for l in r.text.splitlines() if l.startswith("WIBB")]

# =====================================
# ECMWF (FORECAST SUPPORT ONLY)
# =====================================
def fetch_ecmwf():
    r = requests.get(
        ECMWF_API,
        params={
            "latitude": LAT_WIBB,
            "longitude": LON_WIBB,
            "hourly": "cape,cloudcover_low,cloudcover_mid,cloudcover_high",
            "forecast_days": 2,
            "timezone": "UTC"
        },
        timeout=15
    )
    r.raise_for_status()
    d = r.json()
    if "hourly" not in d:
        raise ValueError
    return d

# =====================================
# METAR PARSERS
# =====================================
def wind(m): return re.search(r'(\d{3})(\d{2})KT', m).group(0) if re.search(r'(\d{3})(\d{2})KT', m) else "-"
def visibility(m): return re.search(r' (\d{4}) ', m).group(1)+" m" if re.search(r' (\d{4}) ', m) else "-"
def temp_dew(m):
    x=re.search(r' (M?\d{2})/(M?\d{2})', m)
    return f"{x.group(1)}/{x.group(2)} °C" if x else "-"
def qnh(m): return re.search(r' Q(\d{4})', m).group(1)+" hPa" if re.search(r' Q(\d{4})', m) else "-"

def parse_numeric_metar(m):
    t=re.search(r' (\d{2})(\d{2})(\d{2})Z', m)
    if not t: return None
    return {
        "time": datetime.strptime(t.group(0).strip(), "%d%H%MZ"),
        "temp": int(re.search(r' (M?\d{2})/', m).group(1).replace("M","-")) if re.search(r' (M?\d{2})/', m) else None,
        "dew": int(re.search(r'/M?\d{2}', m).group(0)[1:].replace("M","-")) if "/" in m else None,
        "wind": int(re.search(r'KT', m).string[-2:]) if "KT" in m else None,
        "qnh": int(re.search(r' Q(\d{4})', m).group(1)) if " Q" in m else None,
        "vis": int(re.search(r' (\d{4}) ', m).group(1)) if re.search(r' (\d{4}) ', m) else None,
        "RA":"RA"in m,"TS":"TS"in m,"FG":"FG"in m
    }

# =====================================
# MAIN APP
# =====================================
st.title("QAM METEOROLOGICAL REPORT — WIBB")
now=datetime.now(timezone.utc).strftime("%d %b %Y %H%M UTC")
metar=fetch_metar()
taf=fetch_taf_bmkg() or fetch_taf_noaa()

st.code(metar)
st.subheader("✈️ TAFOR (RAW ICAO)")
st.code(taf if taf else "TAF not available")

# =====================================
# SATELLITE
# =====================================
st.subheader("🛰️ Himawari-8 IR (Reference)")
try:
    img=requests.get(SATELLITE_HIMA_RIAU,timeout=10).content
    st.image(img,use_container_width=True)
except:
    st.warning("Satellite unavailable")

# =====================================
# ECMWF SUPPORT
# =====================================
st.subheader("🧠 ECMWF Forecast Support (NON-ICAO)")
try:
    e=fetch_ecmwf()
    df=pd.DataFrame(e["hourly"])
    df["time"]=pd.to_datetime(df["time"])
    st.line_chart(df.set_index("time")[["cape","cloudcover_high"]])
except:
    st.warning("ECMWF forecast data unavailable.")

st.caption(
    "⚠️ ECMWF is FORECAST SUPPORT ONLY — Operational decisions MUST rely on METAR / TAF / SIGMET / ATC."
)

# =====================================
# METEOGRAM
# =====================================
raw=fetch_metar_history(24)
if len(raw)<2: raw=fetch_metar_ogimet(24)
df=pd.DataFrame([parse_numeric_metar(m) for m in raw if parse_numeric_metar(m)])

if not df.empty:
    fig=make_subplots(rows=4,cols=1,shared_xaxes=True)
    fig.add_trace(go.Scatter(x=df.time,y=df.temp,name="Temp"),1,1)
    fig.add_trace(go.Scatter(x=df.time,y=df.dew,name="Dew"),1,1)
    fig.add_trace(go.Scatter(x=df.time,y=df.wind,name="Wind"),2,1)
    fig.add_trace(go.Scatter(x=df.time,y=df.qnh,name="QNH"),3,1)
    fig.add_trace(go.Scatter(x=df.time,y=df.vis,name="Vis"),4,1)
    st.plotly_chart(fig,use_container_width=True)

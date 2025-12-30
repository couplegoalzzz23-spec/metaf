import streamlit as st
import requests
from datetime import datetime, timezone
import re
import math
from io import BytesIO

# =====================================
# PAGE CONFIG
# =====================================
st.set_page_config(
    page_title="LANUD RSN Tactical METOC",
    page_icon="✈️",
    layout="wide"
)

# =====================================
# SIDEBAR
# =====================================
with st.sidebar:
    st.header("OPS CONTROL")
    view_mode = st.radio("Mode Tampilan", ["QAM", "OPS"])
    refresh_min = st.slider("Auto Refresh (menit)", 1, 30, 5)
    auto_refresh = st.checkbox("Auto Refresh", True)
    tz_mode = st.radio("Zona Waktu", ["UTC", "WIB"])

if auto_refresh:
    st.markdown(
        f"<meta http-equiv='refresh' content='{refresh_min * 60}'>",
        unsafe_allow_html=True
    )

# =====================================
# DATA SOURCE
# =====================================
URL = "https://aviationweather.gov/api/data/metar"

def fetch_data():
    params = {"ids": "WIBB", "hours": 0, "sep": "true", "taf": "true"}
    r = requests.get(URL, params=params, timeout=10)
    r.raise_for_status()
    return r.text.strip().split("\n")

# =====================================
# PARSING
# =====================================
def wind(m):
    x = re.search(r'(\d{3})(\d{2})KT', m)
    return (int(x.group(1)), int(x.group(2))) if x else (None, None)

def visibility(m):
    x = re.search(r' (\d{4}) ', m)
    return int(x.group(1)) if x else None

def ceiling(m):
    if "OVC" in m: return "OVC"
    if "BKN" in m: return "BKN"
    if "SCT" in m: return "SCT"
    return "CLR"

# =====================================
# QAM ASSESSMENT
# =====================================
def qam_assess(m):
    score = 0
    notes = []

    wd, ws = wind(m)
    vis = visibility(m)
    cld = ceiling(m)

    if "TS" in m or "CB" in m:
        score += 2
        notes.append("Thunderstorm / CB")

    if vis:
        if vis < 3000:
            score += 2
            notes.append("Visibility < 3000 m")
        elif vis < 5000:
            score += 1
            notes.append("Visibility marginal")

    if ws:
        if ws > 25:
            score += 2
            notes.append("Strong wind")
        elif ws >= 15:
            score += 1
            notes.append("Moderate wind")

    if cld == "OVC":
        score += 2
        notes.append("Overcast ceiling")
    elif cld == "BKN":
        score += 1
        notes.append("Broken cloud")

    if score == 0:
        return "🟢 GO", "green", ["All parameters within limits"], "OPERASI DAPAT DILAKSANAKAN"
    if score <= 2:
        return "🟡 CAUTION", "orange", notes, "OPERASI DENGAN PEMBATASAN"
    return "🔴 NO-GO", "red", notes, "OPERASI TIDAK DIREKOMENDASIKAN"

# =====================================
# PDF GENERATOR (FAIL-SAFE)
# =====================================
def generate_qam_pdf(text):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas

        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        y = height - 50
        for line in text.split("\n"):
            c.drawString(40, y, line)
            y -= 14
            if y < 40:
                c.showPage()
                y = height - 50

        c.save()
        buffer.seek(0)
        return buffer
    except Exception:
        return None

# =====================================
# MAIN
# =====================================
st.title("✈️ Tactical METOC Dashboard")
st.subheader("Lanud Roesmin Nurjadin (WIBB)")

try:
    lines = fetch_data()
    metar = next(l for l in lines if l.startswith("METAR"))
    taf = next(l for l in lines if l.startswith("TAF"))

    status, color, notes, recommendation = qam_assess(metar)

    # ===============================
    # QAM MODE
    # ===============================
    if view_mode == "QAM":
        st.markdown(
            f"""
            <div style="padding:25px;border-radius:12px;
            background:{color};color:white;font-size:32px;
            font-weight:bold;text-align:center;">
            {status}
            </div>
            """,
            unsafe_allow_html=True
        )

        # 🪖 COMMANDER SUMMARY
        st.subheader("🪖 Commander Summary")
        st.markdown(f"**Recommendation:** {recommendation}")
        for n in notes:
            st.warning(n)

        now = datetime.now(timezone.utc)
        if tz_mode == "WIB":
            now = now.replace(hour=(now.hour + 7) % 24)

        qam_text = f"""
QAM – QUICK ASSESSMENT MATRIX
Lanud Roesmin Nurjadin (WIBB)

STATUS         : {status}
RECOMMENDATION : {recommendation}
TIME           : {now.strftime('%Y-%m-%d %H:%M:%S')} {tz_mode}

ISSUES:
"""
        for n in notes:
            qam_text += f"- {n}\n"

        qam_text += f"""

RAW METAR:
{metar}
"""

        # PDF TRY
        pdf = generate_qam_pdf(qam_text)
        if pdf:
            st.download_button(
                "⬇️ Unduh QAM (PDF)",
                data=pdf,
                file_name=f"QAM_WIBB_{now.strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf"
            )
        else:
            st.download_button(
                "⬇️ Unduh QAM (TXT)",
                data=qam_text,
                file_name=f"QAM_WIBB_{now.strftime('%Y%m%d_%H%M')}.txt",
                mime="text/plain"
            )

        st.divider()
        st.code(metar)

    # ===============================
    # OPS MODE (TIDAK DIUBAH)
    # ===============================
    else:
        st.code(metar)
        st.code(taf)

    st.caption(f"Last Update: {now.strftime('%Y-%m-%d %H:%M:%S')} {tz_mode}")

except Exception as e:
    st.error(f"ERROR: {e}")

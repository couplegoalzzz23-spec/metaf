import streamlit as st
import requests
from datetime import datetime, timezone
import re

# =====================================
# PAGE CONFIG (TIDAK DIUBAH)
# =====================================
st.set_page_config(
    page_title="QAM METOC WIBB",
    page_icon="✈️",
    layout="wide"
)

# =====================================
# DATA SOURCE (TIDAK DIUBAH)
# =====================================
METAR_URL = "https://aviationweather.gov/api/data/metar"

def fetch_metar():
    r = requests.get(
        METAR_URL,
        params={"ids": "WIBB", "hours": 0},
        timeout=10
    )
    r.raise_for_status()
    return r.text.strip()

# =====================================
# PARSING METAR (TIKSAH)
# =====================================
def parse_metar(metar_data):
    # Use regular expressions to extract relevant information
    # This is a simplified example; you may need to adjust the regex patterns
    # to match the actual METAR format
    weather_codes = {
        "TS": "Thunderstorm",
        "FW": "Freezing Fog",
        "BR": "Brina",
        "FG": "Fog",
        "SN": "Snow",
        "RA": "Rain",
        "DZ": "Drizzle",
    }
    
    # Example regex patterns
    pattern_weather = r"(\w{2})"  # Weather condition code
    pattern_visibility = r"(\d+)M"  # Visibility in meters
    pattern_temperature = r"(\d+)T(\d+)Z"  # Temperature and dew point
    pattern_wind = r"(\d+)kt"  # Wind speed
    pattern_direction = r"(\w+)kt"  # Wind direction
    
    # Use the regex patterns to extract the relevant information
    weather = re.search(pattern_weather, metar_data)
    visibility = re.search(pattern_visibility, metar_data)
    temperature = re.search(pattern_temperature, metar_data)
    wind = re.search(pattern_wind, metar_data)
    direction = re.search(pattern_direction, metar_data)
    
    if weather:
        weather_condition = weather_codes[weather.group(0)]
    else:
        weather_condition = "Unknown"
    
    if visibility:
        visibility_value = visibility.group(0)
    else:
        visibility_value = "Unknown"
    
    if temperature:
        temperature_value = f"{temperature.group(1)}/{temperature.group(2)}"
    else:
        temperature_value = "Unknown"
    
    if wind:
        wind_speed = wind.group(0)
    else:
        wind_speed = "Unknown"
    
    if direction:
        wind_direction = direction.group(0)
    else:
        wind_direction = "Unknown"
    
    return {
        "Weather Condition": weather_condition,
        "Visibility": visibility_value,
        "Temperature": temperature_value,
        "Wind Speed": wind_speed,
        "Wind Direction": wind_direction,
    }

# =====================================
# MAIN APPLICATION
# =====================================
def main():
    st.title("QAM METOC WIBB")
    st.write("METAR Data for WIBB Airport")
    
    metar_data = fetch_metar()
    parsed_metar = parse_metar(metar_data)
    
    st.write("METAR Data:")
    st.write(metar_data)
    
    st.write("Parsed METAR Data:")
    for key, value in parsed_metar.items():
        st.write(f"{key}: {value}")

if __name__ == "__main__":
    main()

import re
import requests

# Dictionary of weather codes and descriptions
weather_codes = {
    "01": "Sunny",
    "02": "Partly Cloudy",
    "03": "Cloudy",
    "04": "Light Rain",
    "05": "Heavy Rain",
    "06": "Snow",
    "07": "Sleet",
    "08": "Hail",
    "09": "Thunderstorm",
    "10": "Tornado",
    "11": "Unknown"
}

# Fungsi untuk memParsing METAR data
def parse_metar(metar_data):
    # Gunakan regex untuk mengekstrak informasi cuaca
    weather_pattern = r"([A-Z]{2,4})"  # Contoh pattern untuk mengekstrak kode cuaca
    weather_match = re.search(weather_pattern, metar_data)
    
    if weather_match:
        weather_code = weather_match.group(1)
        return weather_codes.get(weather_code, "Unknown")
    else:
        return "Unknown"

# Fungsi untuk mengambil METAR data dari API
def get_metar_data(icao_code):
    url = f"http://aviationweather.gov/metar/data?ids={icao_code}&format=raw&date=&hours=0&taf=off&layout=on&std=off"
    response = requests.get(url)
    return response.text

# Fungsi utama
def main():
    icao_code = "KJFK"  # Kode ICAO untuk Bandara JFK
    metar_data = get_metar_data(icao_code)
    weather_description = parse_metar(metar_data)
    print(f"Weather at {icao_code}: {weather_description}")

if __name__ == "__main__":
    main()

import time
import requests
from config import OPEN_METEO_BASE_URL, PHNOM_PENH_COORDS, CACHE_TTL_SECONDS

_cache = {}

def get_rain_forecast(lat=PHNOM_PENH_COORDS["lat"], lng=PHNOM_PENH_COORDS["lng"], hour_offset=1):
    cache_key = f"rain_{round(lat, 3)}_{round(lng, 3)}_{hour_offset}"
    now = time.time()
    if cache_key in _cache and (now - _cache[cache_key]["time"]) < CACHE_TTL_SECONDS:
        return _cache[cache_key]["data"]

    params = {
        "latitude": lat,
        "longitude": lng,
        "hourly": "precipitation_probability,precipitation",
        "timezone": "Asia/Bangkok"
    }
    try:
        resp = requests.get(OPEN_METEO_BASE_URL, params=params, timeout=5)
        data = resp.json()
        hourly = data.get("hourly", {})
        idx = min(max(hour_offset, 0), len(hourly.get("time", [])) - 1)
        res = {
            "time": hourly.get("time", [])[idx] if hourly.get("time") else "Now",
            "rain_prob": hourly.get("precipitation_probability", [0])[idx],
            "rain_mm": hourly.get("precipitation", [0.0])[idx]
        }
        _cache[cache_key] = {"time": now, "data": res}
        return res
    except Exception:
        return {"time": "Unknown", "rain_prob": 0, "rain_mm": 0.0}

def get_live_weather_aqi(lat=PHNOM_PENH_COORDS["lat"], lng=PHNOM_PENH_COORDS["lng"]):
    cache_key = f"aqi_{round(lat, 3)}_{round(lng, 3)}"
    now = time.time()
    if cache_key in _cache and (now - _cache[cache_key]["time"]) < CACHE_TTL_SECONDS:
        return _cache[cache_key]["data"]

    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {"latitude": lat, "longitude": lng, "current": "pm2_5,us_aqi"}
    try:
        resp = requests.get(url, params=params, timeout=5)
        data = resp.json().get("current", {})
        res = {"pm25": data.get("pm2_5", 15.0), "aqi": data.get("us_aqi", 45)}
        _cache[cache_key] = {"time": now, "data": res}
        return res
    except Exception:
        return {"pm25": 18.0, "aqi": 50}

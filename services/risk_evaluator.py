import json
import math
from pathlib import Path
from services.weather import get_rain_forecast, get_live_weather_aqi
from services.traffic import check_traffic

def _load_flood_zones():
    path = Path(__file__).resolve().parent.parent / "data" / "flood_zones.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def _distance_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2)**2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def evaluate_route_risk(route_coords, hour_offset=1):
    flood_zones = _load_flood_zones()
    hit_zones = []

    for pt in route_coords[::5]:
        lng, lat = pt[0], pt[1]
        for z in flood_zones:
            c = z["center"]
            if _distance_km(lat, lng, c["lat"], c["lng"]) <= z["radius_km"]:
                if z["sangkat"] not in hit_zones:
                    hit_zones.append(z["sangkat"])

    weather = get_rain_forecast(hour_offset=hour_offset)
    aqi_data = get_live_weather_aqi()
    traffic = check_traffic(route_coords)

    rain_prob = weather.get("rain_prob", 0)
    reasons = []

    if rain_prob >= 50 and hit_zones:
        risk_level = "High"
        reasons.append(f"High rain chance ({rain_prob}%) over flood-prone {', '.join(hit_zones)}")
    elif traffic["speed_ratio"] < 0.55:
        risk_level = "High"
        reasons.append(f"Severe congestion detected along path ({traffic['status']})")
    elif rain_prob >= 40 or hit_zones or traffic["speed_ratio"] < 0.75:
        risk_level = "Moderate"
        if hit_zones:
            reasons.append(f"Passes historical flood zones ({', '.join(hit_zones)})")
        if rain_prob >= 40:
            reasons.append(f"Scattered rain predicted ({rain_prob}%)")
        if traffic["speed_ratio"] < 0.75:
            reasons.append(f"Traffic slowdown ({traffic['status']})")
    else:
        risk_level = "Low"
        reasons.append("Optimal conditions; normal traffic flow and dry weather")

    return {
        "risk_level": risk_level,
        "reasons": reasons,
        "hit_flood_zones": hit_zones,
        "weather": weather,
        "aqi": aqi_data,
        "traffic": traffic
    }

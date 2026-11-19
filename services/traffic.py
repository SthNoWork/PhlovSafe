import requests
from config import TOMTOM_API_KEY

def check_traffic(coordinates):
    if not TOMTOM_API_KEY or not coordinates:
        return {
            "status": "Normal Flow",
            "speed_ratio": 0.95,
            "source": "Traffic Flow Baseline"
        }

    sample_pts = [coordinates[0], coordinates[len(coordinates) // 2], coordinates[-1]]
    total_ratio = 0.0
    count = 0

    for pt in sample_pts:
        lng, lat = pt[0], pt[1]
        url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/relative0/10/json"
        params = {"point": f"{lat},{lng}", "key": TOMTOM_API_KEY}
        try:
            resp = requests.get(url, params=params, timeout=5)
            data = resp.json().get("flowSegmentData", {})
            current_spd = data.get("currentSpeed", 30)
            free_spd = max(data.get("freeFlowSpeed", 35), 1)
            total_ratio += (current_spd / free_spd)
            count += 1
        except Exception:
            continue

    if count == 0:
        return {"status": "Normal Flow", "speed_ratio": 0.95, "source": "TomTom Traffic Flow API (Fallback)"}

    avg_ratio = round(total_ratio / count, 2)
    if avg_ratio < 0.55:
        status = "Heavy Congestion"
    elif avg_ratio < 0.75:
        status = "Moderate Slowdown"
    else:
        status = "Normal Flow"

    return {"status": status, "speed_ratio": avg_ratio, "source": "TomTom Traffic Flow API"}

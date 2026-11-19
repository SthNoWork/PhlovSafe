import requests
from config import OSRM_HOST

def get_route(origin_lat, origin_lng, dest_lat, dest_lng):
    url = f"{OSRM_HOST}/route/v1/driving/{origin_lng},{origin_lat};{dest_lng},{dest_lat}"
    params = {
        "overview": "full",
        "geometries": "geojson",
        "steps": "true",
        "alternatives": "true"
    }
    try:
        resp = requests.get(url, params=params, timeout=8)
        data = resp.json()
        if data.get("code") != "Ok" or not data.get("routes"):
            return None

        routes = []
        for r in data["routes"]:
            steps = []
            for leg in r.get("legs", []):
                for step in leg.get("steps", []):
                    name = step.get("name") or "unnamed road"
                    maneuver = step.get("maneuver", {}).get("type", "continue")
                    dist = round(step.get("distance", 0))
                    if dist > 0:
                        steps.append(f"{maneuver.capitalize()} onto {name} ({dist}m)")
            routes.append({
                "distance_km": round(r.get("distance", 0) / 1000, 2),
                "duration_min": round(r.get("duration", 0) / 60, 1),
                "coordinates": r.get("geometry", {}).get("coordinates", []),
                "steps": steps[:6]
            })
        return {
            "primary": routes[0],
            "alternate": routes[1] if len(routes) > 1 else None
        }
    except Exception:
        return None

def format_navigation_link(origin_lat, origin_lng, dest_lat, dest_lng):
    return f"https://www.google.com/maps/dir/?api=1&origin={origin_lat},{origin_lng}&destination={dest_lat},{dest_lng}&travelmode=two_wheeler"

def search_places(query):
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": f"{query}, Phnom Penh",
        "format": "json",
        "limit": 5,
        "countrycodes": "kh"
    }
    headers = {"User-Agent": "PhnomPenhCommuteApp/1.0"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=5)
        return [{"name": item.get("display_name"), "lat": float(item["lat"]), "lng": float(item["lon"])} for item in resp.json()]
    except Exception:
        return []


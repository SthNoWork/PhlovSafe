import subprocess
import sys
from pathlib import Path

req_file = Path(__file__).resolve().parent / "requirements.txt"
if req_file.exists():
    try:
        import flask
        import requests
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(req_file)])

import json
from flask import Flask, request, jsonify, send_from_directory
from services.routing import get_route, search_places, format_navigation_link
from services.risk_evaluator import evaluate_route_risk

app = Flask(__name__, static_folder="static")

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/api/flood-zones")
def flood_zones():
    path = Path(__file__).resolve().parent / "data" / "flood_zones.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    return jsonify([])

@app.route("/api/search")
def search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify([])
    return jsonify(search_places(query))

@app.route("/api/route-risk")
def route_risk():
    try:
        orig_lat = float(request.args.get("orig_lat"))
        orig_lng = float(request.args.get("orig_lng"))
        dest_lat = float(request.args.get("dest_lat"))
        dest_lng = float(request.args.get("dest_lng"))
        hour_offset = int(float(request.args.get("hour_offset", 0)))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid coordinates or hour_offset"}), 400

    routes = get_route(orig_lat, orig_lng, dest_lat, dest_lng)
    if not routes or not routes.get("primary"):
        return jsonify({"error": "Unable to calculate route"}), 404

    primary = routes["primary"]
    risk = evaluate_route_risk(primary["coordinates"], hour_offset=hour_offset)
    nav_link = format_navigation_link(orig_lat, orig_lng, dest_lat, dest_lng)

    return jsonify({
        "primary": primary,
        "alternate": routes.get("alternate"),
        "risk": risk,
        "navigation_url": nav_link
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

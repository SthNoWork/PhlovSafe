import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY", "")
DATAEF_API_KEY = os.getenv("DATAEF_API_KEY", "")
OSRM_HOST = os.getenv("OSRM_HOST", "https://router.project-osrm.org")
OPEN_METEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"
PHNOM_PENH_COORDS = {"lat": 11.5564, "lng": 104.9282}
CACHE_TTL_SECONDS = 600
WEB_APP_URL = os.getenv("WEB_APP_URL", "http://localhost:5000")


# Workspace Summary

### 1. Stack & Purpose
- Proactive Phnom Penh Commute & Route Risk Assistant Telegram bot.
- Python 3, `python-telegram-bot`, `requests`, `python-dotenv`.

### 2. Map & Flow
- `config.py`: Configuration constants and env vars (L1-13).
- `requirements.txt`: Project dependencies (L1-4).
- `data/flood_zones.json`: ODC flood-prone Sangkat coordinates and radiuses (L1-28).
- `services/weather.py`: In-memory cached Open-Meteo rain & AQI client (L1-53).
- `services/routing.py`: OSRM routing client and Nominatim place search (L1-56).
- `services/traffic.py`: TomTom traffic flow check with fallback (L1-40).
- `services/risk_evaluator.py`: Multi-factor risk evaluator fusing weather, flood zones, traffic (L1-67).
- `server.py`: Flask web and API server (L1-66).
- `.github/workflows/deploy.yml`: Automated GitHub Pages deploy workflow (L1-31).
- `index.html`: Root website entry for repository hosting (L1-150).
- `static/index.html`: Leaflet GPS web dashboard and risk overlay (L1-150).
- `bot.py`: Dynamic `/plan <origin> to <dest> [mins]`, interactive map link, persistent commands (L1-160).
- Flow: Browser GPS / Map Click -> `server.py` (`/api/route-risk`) -> `services/routing.py` + `services/risk_evaluator.py` -> Leaflet UI overlay.

### 3. Data & Conventions
- Config via environment variables in root.
- Coordinates format: `{"lat": float, "lng": float}`.
- Cache TTL: 600s.

### 4. Decisions
- Open-Meteo & public OSRM require no auth; TomTom/DataEF require optional keys with fallback.

### 5. State
- Done: Part 1 (config, env setup), Part 2 (flood zones, weather, routing), Part 3 (traffic check, risk evaluator, Telegram bot).
- In-progress: Complete.
- Next: None.

### 6. Commands
- Run bot: `python bot.py`
- Install dependencies: `pip install -r requirements.txt`

### 7. Verified Working
- None yet.

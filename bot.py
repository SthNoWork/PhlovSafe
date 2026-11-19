import subprocess
import sys
from pathlib import Path

req_file = Path(__file__).resolve().parent / "requirements.txt"
if req_file.exists():
    try:
        import telegram
        import requests
        import dotenv
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(req_file)])

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from config import TELEGRAM_BOT_TOKEN, WEB_APP_URL
from services.routing import get_route, search_places, format_navigation_link
from services.risk_evaluator import evaluate_route_risk

logging.basicConfig(level=logging.INFO)

def _build_telemetry_card(route_name, route_data, risk_data, departure_label):
    lvl = risk_data["risk_level"]
    icon = {"Low": "🟢", "Moderate": "🟡", "High": "🔴"}.get(lvl, "⚪")
    reasons_text = "\n".join([f"• {r}" for r in risk_data["reasons"]])
    steps_preview = "\n".join([f"  › {s}" for s in route_data.get("steps", [])[:3]])

    return (
        f"{icon} *Trip Risk Analysis: {lvl.upper()}*\n"
        f"📍 *Route:* {route_name}\n"
        f"⏱ *Departure:* {departure_label}\n"
        f"📏 *Distance:* {route_data['distance_km']} km | ~{route_data['duration_min']} min\n\n"
        f"🔍 *Telemetry & Open Data Sources:*\n"
        f"• Rain Forecast: {risk_data['weather']['rain_prob']}% ({risk_data['weather']['rain_mm']} mm) _[Open-Meteo API]_\n"
        f"• AQI & PM2.5: {risk_data['aqi']['aqi']} AQI ({risk_data['aqi']['pm25']} µg/m³) _[DataEF/Open-Meteo]_\n"
        f"• Live Traffic: {risk_data['traffic']['status']} _[{risk_data['traffic']['source']}]_\n"
        f"• Flood Overlay: {len(risk_data['hit_flood_zones'])} zones intersected _[ODC GeoJSON]_\n\n"
        f"⚠️ *Key Assessment:*\n{reasons_text}\n\n"
        f"🧭 *Key Directions Preview:*\n{steps_preview}"
    )

def _is_local_url(url):
    return "localhost" in url or "127.0.0.1" in url

def _build_webapp_btn(text, url):
    if url.startswith("https://"):
        return InlineKeyboardButton(text, web_app=WebAppInfo(url=url))
    return InlineKeyboardButton(text, url=url)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "👋 *សូមស្វាគមន៍ / Welcome to Phnom Penh Commute Co-Pilot!*\n\n"
        "I provide automated pre-departure alerts for rain, flooding, and traffic jams across Phnom Penh.\n\n"
        "Commands:\n"
        "• /plan - Select preset routes & departure times\n"
        "• /map - Open live interactive GPS & route risk map\n"
        "• /reload - Refresh bot menu commands"
    )
    if _is_local_url(WEB_APP_URL):
        msg += f"\n\n🌐 *Web Map (Local):* {WEB_APP_URL}"
        markup = None
    else:
        markup = InlineKeyboardMarkup([[_build_webapp_btn("🌐 Open Live GPS & Route Map", WEB_APP_URL)]])

    await update.message.reply_text(msg, reply_markup=markup, parse_mode="Markdown")

async def map_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if _is_local_url(WEB_APP_URL):
        msg = f"📍 *Interactive GPS Route Planner:* {WEB_APP_URL}"
        markup = None
    else:
        msg = "📍 Click below to launch the live interactive GPS route planner:"
        markup = InlineKeyboardMarkup([[_build_webapp_btn("🗺 Open Fullscreen Risk Map", WEB_APP_URL)]])

    await update.message.reply_text(msg, reply_markup=markup, parse_mode="Markdown")

async def reload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await setup_bot_commands(context.application)
    await update.message.reply_text("✅ Persistent menu commands reloaded successfully.")

async def setup_bot_commands(app):
    commands = [
        BotCommand("start", "Start assistant & view info"),
        BotCommand("plan", "Custom route risk check"),
        BotCommand("map", "Open live GPS & risk map"),
        BotCommand("reload", "Reload persistent menu")
    ]
    await app.bot.set_my_commands(commands)

async def plan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        map_btn = None
        if not _is_local_url(WEB_APP_URL):
            map_btn = InlineKeyboardMarkup([[_build_webapp_btn("🗺 Open Interactive Map", WEB_APP_URL)]])
        await update.message.reply_text(
            "📍 *Dynamic Route Planning:*\n\n"
            "1. Use the interactive map to place your start and destination markers and set departure delay.\n"
            "2. Or type directly:\n`/plan <Origin> to <Destination> [mins]`\n"
            "_Example:_ `/plan RUPP to BKK1 30`",
            reply_markup=map_btn,
            parse_mode="Markdown"
        )
        return

    text = " ".join(args)
    mins = 0
    if " to " in text.lower():
        parts = text.lower().split(" to ")
        orig_query = parts[0].strip()
        dest_part = parts[1].strip()
        dest_tokens = dest_part.split()
        if dest_tokens[-1].isdigit():
            mins = int(dest_tokens[-1])
            dest_query = " ".join(dest_tokens[:-1])
        else:
            dest_query = dest_part
    else:
        orig_query = "Phnom Penh"
        dest_query = text

    orig_matches = search_places(orig_query)
    dest_matches = search_places(dest_query)
    if not orig_matches or not dest_matches:
        await update.message.reply_text("❌ Could not resolve specified location names. Please try again or use /map.")
        return

    o = orig_matches[0]
    d = dest_matches[0]
    routes = get_route(o["lat"], o["lng"], d["lat"], d["lng"])
    if not routes or not routes.get("primary"):
        await update.message.reply_text("❌ Unable to calculate route for the given points.")
        return

    primary = routes["primary"]
    hrs = mins / 60.0
    risk = evaluate_route_risk(primary["coordinates"], hour_offset=int(hrs))
    dep_label = f"In {mins} minutes" if mins > 0 else "Immediate departure"
    route_name = f"{o['name'].split(',')[0]} ➔ {d['name'].split(',')[0]}"
    card = _build_telemetry_card(route_name, primary, risk, dep_label)
    nav_link = format_navigation_link(o["lat"], o["lng"], d["lat"], d["lng"])

    btns = [[InlineKeyboardButton("🗺 Open Navigation", url=nav_link)]]
    await update.message.reply_text(card, reply_markup=InlineKeyboardMarkup(btns), parse_mode="Markdown")

def main():
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN is not configured in .env")
        return

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(setup_bot_commands).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("plan", plan_command))
    app.add_handler(CommandHandler("map", map_command))
    app.add_handler(CommandHandler("reload", reload_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling()

if __name__ == "__main__":
    main()

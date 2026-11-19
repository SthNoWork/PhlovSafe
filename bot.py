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
from services.routing import get_route, format_navigation_link
from services.risk_evaluator import evaluate_route_risk

logging.basicConfig(level=logging.INFO)

PRESET_ROUTES = {
    "1": {"name": "RUPP (Toul Kork) -> BKK1", "orig": (11.5694, 104.8918), "dest": (11.5492, 104.9255)},
    "2": {"name": "Riverside (Daun Penh) -> Aeon 3 (Mean Chey)", "orig": (11.5670, 104.9304), "dest": (11.4988, 104.9247)},
    "3": {"name": "Russian Market (TTP) -> Chroy Changvar", "orig": (11.5375, 104.9142), "dest": (11.5916, 104.9351)}
}

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
        BotCommand("plan", "Select preset commute route"),
        BotCommand("map", "Open live GPS & risk map"),
        BotCommand("reload", "Reload persistent menu")
    ]
    await app.bot.set_my_commands(commands)

async def plan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(f"1. {PRESET_ROUTES['1']['name']}", callback_data="route_1")],
        [InlineKeyboardButton(f"2. {PRESET_ROUTES['2']['name']}", callback_data="route_2")],
        [InlineKeyboardButton(f"3. {PRESET_ROUTES['3']['name']}", callback_data="route_3")]
    ]
    await update.message.reply_text(
        "📍 *Select your commute route / សូមជ្រើសរើសផ្លូវធ្វើដំណើរ:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("route_"):
        route_id = data.split("_")[1]
        context.user_data["selected_route"] = route_id
        time_kb = [
            [
                InlineKeyboardButton("Now (ភ្លាមៗ)", callback_data="time_0"),
                InlineKeyboardButton("In 30m (30 នាទី)", callback_data="time_0.5")
            ],
            [
                InlineKeyboardButton("In 1h (1 ម៉ោង)", callback_data="time_1"),
                InlineKeyboardButton("In 2h (2 ម៉ោង)", callback_data="time_2")
            ]
        ]
        await query.edit_message_text(
            f"Selected: *{PRESET_ROUTES[route_id]['name']}*\n\n"
            f"🕒 *When do you plan to depart? / តើអ្នកគ្រោងចេញដំណើរពេលណា?*",
            reply_markup=InlineKeyboardMarkup(time_kb),
            parse_mode="Markdown"
        )
    elif data.startswith("time_"):
        hours = float(data.split("_")[1])
        route_id = context.user_data.get("selected_route", "1")
        route_info = PRESET_ROUTES[route_id]
        orig, dest = route_info["orig"], route_info["dest"]

        routes = get_route(orig[0], orig[1], dest[0], dest[1])
        if not routes or not routes.get("primary"):
            await query.edit_message_text("❌ Unable to calculate route at this moment.")
            return

        primary = routes["primary"]
        risk = evaluate_route_risk(primary["coordinates"], hour_offset=int(hours))
        dep_label = "Immediate departure" if hours == 0 else f"In {int(hours * 60)} minutes"
        card = _build_telemetry_card(route_info["name"], primary, risk, dep_label)
        map_url = format_navigation_link(orig[0], orig[1], dest[0], dest[1])

        buttons = [[InlineKeyboardButton("🗺 Open Two-Wheeler Navigation", url=map_url)]]
        if routes.get("alternate"):
            alt = routes["alternate"]
            card += f"\n\n💡 *Side-Street Detour Available:* {alt['distance_km']} km (~{alt['duration_min']} min)"

        await query.edit_message_text(card, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

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

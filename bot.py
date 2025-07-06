import os
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = "https://wgtodobot.onrender.com/webhook"

# ===== HANDLER COMMANDS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot aktif via webhook!")

def setup_bot():
    bot = Application.builder().token(BOT_TOKEN).build()
    bot.add_handler(CommandHandler("start", start))
    return bot

# ===== FLASK ROUTES =====
@app.route('/')
def home():
    return "Bot siap!", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    bot = setup_bot()
    update = Update.de_json(request.get_json(), bot.bot)
    bot.process_update(update)
    return "OK", 200

if __name__ == '__main__':
    bot = setup_bot()
    bot.run_webhook(
        listen="0.0.0.0",
        port=10000,
        webhook_url=WEBHOOK_URL
    )

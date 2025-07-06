import os
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
)

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ===== BOT LOGIC =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Bot berhasil merespon via webhook!")

# ===== WEBHOOK SETUP =====
@app.route('/webhook', methods=['POST'])
async def webhook():
    bot = Application.builder().token(BOT_TOKEN).build()
    bot.add_handler(CommandHandler("start", start))
    
    update = Update.de_json(request.get_json(), bot.bot)
    await bot.process_update(update)
    return '', 200

@app.route('/')
def home():
    return "🤖 Bot Ready! Send /start to test", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

import os
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Handler command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎉 Bot berhasil terhubung!")

# Setup bot
def create_app():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    return app

# Webhook route
@app.route('/webhook', methods=['POST'])
async def handle_webhook():
    bot = create_app()
    update = Update.de_json(request.get_json(), bot.bot)
    await bot.process_update(update)
    return '', 200

@app.route('/')
def home():
    return "Bot aktif! Kirim /start di Telegram", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

import os
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Handler command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 BOT PRODUKSI AKTIF!")

def setup_bot():
    bot = Application.builder().token(BOT_TOKEN).build()
    bot.add_handler(CommandHandler("start", start))
    return bot

@app.route('/webhook', methods=['POST'])
async def webhook():
    bot = setup_bot()
    update = Update.de_json(request.get_json(), bot.bot)
    await bot.process_update(update)
    return '', 200

@app.route('/')
def home():
    return "PRODUCTION READY", 200

def run_production():
    from waitress import serve
    serve(app, host="0.0.0.0", port=10000)

if __name__ == '__main__':
    run_production()

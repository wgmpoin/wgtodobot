import os
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Handler sederhana
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Bot berhasil terhubung!")

# Inisialisasi bot
def init_bot():
    bot = Application.builder().token(BOT_TOKEN).build()
    bot.add_handler(CommandHandler("start", start))
    return bot

# Webhook route
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        bot = init_bot()
        update = Update.de_json(request.get_json, bot.bot)
        bot.process_update(update)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        print(f"ERROR: {str(e)}")  # Log error
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/')
def home():
    return "🟢 Webhook Ready", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

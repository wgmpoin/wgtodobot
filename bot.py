import os
from flask import Flask
from telegram.ext import Application, CommandHandler

app = Flask(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")

async def start(update, context):
    await update.message.reply_text("🔧 BOT DALAM PERBAIKAN")

def setup_bot():
    bot = Application.builder().token(BOT_TOKEN).build()
    bot.add_handler(CommandHandler("start", start))
    return bot

@app.route('/')
def home():
    return "SEDANG DIPERBAIKI", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

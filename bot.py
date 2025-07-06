import os
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OWNER_ID = int(os.getenv("OWNER_ID"))

app = Flask(__name__)
app_bot = Application.builder().token(BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot aktif. Gunakan /add untuk tambah tugas.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/start - Mulai bot\n/help - Bantuan")

@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), app_bot.bot)
    app_bot.process_update(update)
    return "OK"

if __name__ == "__main__":
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("help", help_command))
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))

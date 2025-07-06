import os
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes
)
from supabase import create_client
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = "/webhook"
PORT = int(os.getenv("PORT", "5000"))
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
app_bot = Application.builder().token(BOT_TOKEN).build()

ASK_DESC, ASK_DEADLINE, ASK_RECEIVER = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    user = supabase.table("users").select("*").eq("id", telegram_id).execute().data
    if user:
        await update.message.reply_text(f"Halo {user[0]['alias']}, kamu sudah terdaftar.\nGunakan /add untuk tambah tugas.")
    else:
        await update.message.reply_text("⚠️ Kamu belum terdaftar, hubungi admin untuk didaftarkan.")

async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    user = supabase.table("users").select("*").eq("id", telegram_id).execute().data
    if not user or not user[0].get("can_assign", False):
        await update.message.reply_text("❌ Kamu tidak punya izin menambah tugas.")
        return ConversationHandler.END
    await update.message.reply_text("✏️ Masukkan deskripsi tugas:")
    return ASK_DESC

async def ask_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["description"] = update.message.text.strip()
    await update.message.reply_text("📅 Masukkan deadline (YYYY-MM-DD):")
    return ASK_DEADLINE

async def ask_receiver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    deadline_str = update.message.text.strip()
    try:
        datetime.strptime(deadline_str, "%Y-%m-%d")
    except ValueError:
        await update.message.reply_text("❌ Format deadline salah, harus YYYY-MM-DD. Coba lagi:")
        return ASK_DEADLINE
    context.user_data["deadline"] = deadline_str
    await update.message.reply_text("👤 Masukkan alias penerima tugas:")
    return ASK_RECEIVER

async def save_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    alias = update.message.text.strip()
    receiver = supabase.table("users").select("*").eq("alias", alias).execute().data
    if not receiver:
        await update.message.reply_text("❌ Alias penerima tidak ditemukan. Batal.")
        return ConversationHandler.END

    task = {
        "giver_id": update.effective_user.id,
        "receiver_id": receiver[0]["id"],
        "description": context.user_data["description"],
        "deadline": context.user_data["deadline"],
        "created_at": datetime.utcnow().isoformat()
    }
    supabase.table("tasks").insert(task).execute()

    await update.message.reply_text("✅ Tugas berhasil ditambahkan.")
    return ConversationHandler.END

async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    tasks = supabase.table("tasks").select("*").or_(
        f"giver_id.eq.{telegram_id},receiver_id.eq.{telegram_id}"
    ).execute().data

    if not tasks:
        await update.message.reply_text("📭 Tidak ada tugas untukmu.")
        return

    pesan = "📋 Daftar Tugas:\n\n"
    for t in tasks:
        pesan += f"- {t['description']}\n  Deadline: {t['deadline']}\n\n"

    await update.message.reply_text(pesan)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pesan = (
        "/start - Mulai bot\n"
        "/add - Tambah tugas\n"
        "/list - Lihat tugas\n"
        "/help - Bantuan\n"
    )
    await update.message.reply_text(pesan)

@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), app_bot.bot)
    app_bot.process_update(update)
    return "OK"

def main():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add", add_start)],
        states={
            ASK_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_deadline)],
            ASK_DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_receiver)],
            ASK_RECEIVER: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_task)],
        },
        fallbacks=[],
    )

    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(conv_handler)
    app_bot.add_handler(CommandHandler("list", list_tasks))
    app_bot.add_handler(CommandHandler("help", help_command))

    app.run(host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()

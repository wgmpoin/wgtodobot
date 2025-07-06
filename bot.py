import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters,
    ContextTypes, ConversationHandler
)
from supabase import create_client
from datetime import date, timedelta

BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OWNER_ID = int(os.getenv("OWNER_ID"))

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# === Start Command ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    telegram_id = update.effective_user.id
    user = supabase.table("users").select("*").eq("id", telegram_id).execute().data

    if user:
        await update.message.reply_text("✅ Kamu sudah terdaftar.\nGunakan /add untuk tambah tugas.")
    else:
        await update.message.reply_text("🔒 Kamu belum terdaftar di sistem. Hubungi admin.")

# === Add Task ===
ASK_DESCRIPTION, ASK_DEADLINE, ASK_RECEIVER = range(3)

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    user = supabase.table("users").select("*").eq("id", telegram_id).execute().data

    if not user or not user[0]["can_assign"]:
        await update.message.reply_text("❌ Kamu tidak punya izin untuk menambah tugas.")
        return ConversationHandler.END

    context.user_data["giver_id"] = telegram_id
    await update.message.reply_text("📝 Masukkan deskripsi tugas:")
    return ASK_DESCRIPTION

async def ask_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["description"] = update.message.text
    await update.message.reply_text("📅 Masukkan deadline (YYYY-MM-DD):")
    return ASK_DEADLINE

async def ask_receiver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["deadline"] = update.message.text
    await update.message.reply_text("👤 Masukkan alias penerima tugas:")
    return ASK_RECEIVER

async def save_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    alias = update.message.text.strip()
    receiver = supabase.table("users").select("*").eq("alias", alias).execute().data
    if not receiver:
        await update.message.reply_text("❌ Alias tidak ditemukan.")
        return ConversationHandler.END

    supabase.table("tasks").insert({
        "giver_id": context.user_data["giver_id"],
        "receiver_id": receiver[0]["id"],
        "description": context.user_data["description"],
        "deadline": context.user_data["deadline"]
    }).execute()

    await update.message.reply_text("✅ Tugas berhasil ditambahkan.")
    return ConversationHandler.END

# === List Task ===
async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    tasks = supabase.table("tasks").select("*").or_(
        f"giver_id.eq.{telegram_id},receiver_id.eq.{telegram_id}"
    ).execute().data

    if not tasks:
        await update.message.reply_text("📭 Tidak ada tugas.")
        return

    message = "📋 Daftar Tugas:\n\n"
    for task in tasks:
        message += (
            f"📝 {task['description']}\n"
            f"📅 {task['deadline']}\n\n"
        )

    await update.message.reply_text(message)

# === Help ===
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start - Mulai bot\n"
        "/add - Tambah tugas\n"
        "/list - Lihat tugas\n"
        "/help - Bantuan"
    )

# === Main ===
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add", add)],
        states={
            ASK_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_deadline)],
            ASK_DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_receiver)],
            ASK_RECEIVER: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_task)],
        },
        fallbacks=[],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("list", list_tasks))
    app.add_handler(CommandHandler("help", help_command))

    app.run_polling()

if __name__ == "__main__":
    main()

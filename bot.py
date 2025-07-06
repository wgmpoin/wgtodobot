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

    await update.message.reply_text("✅ Tugas berhas_

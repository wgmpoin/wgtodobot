# === FILE: bot.py ===
# FINAL VERSION: Telegram To-Do List Bot (Private, Role-Based, Auto .env)

import os
TOKEN = os.environ["BOT_TOKEN"]
import logging
from datetime import datetime, timedelta
from telegram import Update, ForceReply
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

import sqlite3

# === Load .env ===
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# === Logging ===
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# === Database Setup ===
conn = sqlite3.connect("tasks.db")
cursor = conn.cursor()
cursor.execute(
    """CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task TEXT,
        deadline TEXT,
        assigned_to TEXT
    )"""
)
conn.commit()

# === Command Handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("✅ Bot aktif. Gunakan /add untuk tambah tugas.")

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("📌 Masukkan tugas:")
    return 1

async def add_task_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["task"] = update.message.text
    await update.message.reply_text("📅 Masukkan deadline (YYYY-MM-DD):")
    return 2

async def add_task_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["deadline"] = update.message.text
    await update.message.reply_text("👤 Tugas ini untuk siapa?")
    return 3

async def add_task_assignee(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    task = context.user_data["task"]
    deadline = context.user_data["deadline"]
    assigned_to = update.message.text

    cursor.execute(
        "INSERT INTO tasks (task, deadline, assigned_to) VALUES (?, ?, ?)",
        (task, deadline, assigned_to),
    )
    conn.commit()

    await update.message.reply_text(f"✅ Tugas ditambahkan:\n\n📌 {task}\n📅 {deadline}\n👤 {assigned_to}")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Proses dibatalkan.")
    return ConversationHandler.END

async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cursor.execute("SELECT task, deadline, assigned_to FROM tasks")
    tasks = cursor.fetchall()

    if not tasks:
        await update.message.reply_text("📭 Tidak ada tugas.")
        return

    message = "📋 Daftar Tugas:\n\n"
    for task, deadline, assigned_to in tasks:
        message += f"📌 {task}\n📅 {deadline}\n👤 {assigned_to}\n\n"

    await update.message.reply_text(message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "/start - Mulai bot\n"
        "/add - Tambah tugas\n"
        "/list - Lihat semua tugas\n"
        "/cancel - Batalkan proses"
    )

# === Main Function ===
def main() -> None:
    app = Application.builder().token(TOKEN).build()

    # Conversation Handler untuk tambah tugas
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add", add)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_task_description)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_task_deadline)],
            3: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_task_assignee)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("list", list_tasks))
    app.add_handler(CommandHandler("help", help_command))

    app.run_polling()

if __name__ == "__main__":
    main()

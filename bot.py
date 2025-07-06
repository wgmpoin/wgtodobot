import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
OWNER_ID = int(os.environ["OWNER_ID"])

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot aktif ✅")


async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Format: /add <tugas>")
        return
    task = " ".join(context.args)
    supabase.table("tasks").insert({
        "user_id": user_id,
        "task": task
    }).execute()
    await update.message.reply_text("Tugas disimpan 📝")


async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = supabase.table("tasks").select("*").eq("user_id", user_id).execute()
    tasks = data.data
    if not tasks:
        await update.message.reply_text("Belum ada tugas 📭")
    else:
        text = "\n".join(f"- {t['task']}" for t in tasks)
        await update.message.reply_text(f"Tugas kamu:\n{text}")


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("list", list_tasks))

    # === WAJIB WEBHOOK (untuk Render) ===
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        webhook_url=WEBHOOK_URL
    )


if __name__ == "__main__":
    main()

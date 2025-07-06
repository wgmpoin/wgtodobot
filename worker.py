import asyncio
import os
from supabase import create_client
from telegram import Bot

BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
OWNER_ID = int(os.getenv("OWNER_ID"))

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
bot = Bot(token=BOT_TOKEN)

async def send_reminders():
    tasks = supabase.table("tasks").select("*").execute().data
    for task in tasks:
        # Contoh kirim reminder ke owner
        await bot.send_message(chat_id=OWNER_ID, text=f"Reminder: {task['title']}")

if __name__ == "__main__":
    asyncio.run(send_reminders())

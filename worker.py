import asyncio
import os
from supabase import create_client
from telegram import Bot
from datetime import date, timedelta

BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
bot = Bot(token=BOT_TOKEN)

async def send_reminders():
    today = date.today()
    tasks = supabase.table("tasks").select("*").gte("deadline", str(today)).lte("deadline", str(today + timedelta(days=7))).execute().data
    if not tasks:
        return

    for task in tasks:
        receiver_id = task["receiver_id"]
        deadline = task["deadline"]
        description = task["description"]
        await bot.send_message(
            chat_id=receiver_id,
            text=f"📌 *Reminder Tugas*\n\n📝 {description}\n📅 Deadline: {deadline}",
            parse_mode="Markdown"
        )

if __name__ == "__main__":
    asyncio.run(send_reminders())

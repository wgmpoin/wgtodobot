import os
import asyncio
from datetime import datetime, timedelta
from telegram import Bot
import db

BOT_TOKEN = os.environ.get("BOT_TOKEN")

async def send_reminders():
    bot = Bot(token=BOT_TOKEN)
    users = await db.get_all_users()

    for user in users:
        tasks = await db.fetch_active_tasks_for_user(user["id"])
        for task in tasks:
            deadline = datetime.strptime(task["deadline"], "%Y-%m-%d").date()
            today = datetime.now().date()
            remaining_days = (deadline - today).days

            if 0 <= remaining_days <= 7:
                try:
                    await bot.send_message(
                        user["id"],
                        f"⚠️ *Reminder Tugas*\n"
                        f"Deskripsi: {task['description']}\n"
                        f"Deadline: {task['deadline']}\n"
                        f"Sisa waktu: {remaining_days} hari.",
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    print(f"Gagal kirim reminder ke {user['alias']}: {e}")

if __name__ == "__main__":
    asyncio.run(send_reminders())

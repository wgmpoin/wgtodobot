import os
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = "https://wgtodobot.onrender.com/webhook"  # Your Render URL

async def set_webhook():
    bot = Bot(token=BOT_TOKEN)
    result = await bot.set_webhook(WEBHOOK_URL)
    print(f"Webhook set: {result}")

if __name__ == '__main__':
    import asyncio
    asyncio.run(set_webhook())

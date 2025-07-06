import os
from telegram.ext import Application, CommandHandler

BOT_TOKEN = "7861471571:AAFVzhbHBpktOdRisstI8hK_y6H3saKasxQ"  # PASTIKAN INI TOKEN ASLI ANDA

async def start(update, context):
    await update.message.reply_text("🔥 POLLING MODE AKTIF!")

if __name__ == '__main__':
    print("=== STARTING BOT ===")
    bot = Application.builder().token(BOT_TOKEN).build()
    bot.add_handler(CommandHandler("start", start))
    print("Bot is polling...")
    bot.run_polling()

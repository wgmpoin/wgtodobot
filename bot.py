# === FILE: bot.py ===
import os
import asyncio
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
import db

# === SETUP ===
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")
APP_NAME = "wgtodobot"  # Ganti nama Fly.io kamu di sini
WEBHOOK_URL = f"https://{APP_NAME}.fly.dev/webhook"
PORT = int(os.getenv("PORT", "8080"))

# === HANDLERS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await db.fetch_user(update.effective_user.id)
    if user:
        await update.message.reply_text(f"Halo {user['alias']}, selamat datang!")
    else:
        pending = await db.fetch_pending_users()
        exist = any(u["id"] == update.effective_user.id for u in pending)
        if exist:
            await update.message.reply_text("Permintaan kamu sedang menunggu persetujuan.")
        else:
            await db.register_pending_user(update.effective_user)
            await update.message.reply_text(
                "Permintaan kamu dikirim ke owner. Tunggu persetujuan."
            )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Ini adalah bot To-Do List.\nPerintah dasar:\n/start\n/help")


async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    tasks = await db.fetch_tasks(user_id)
    if not tasks:
        await update.message.reply_text("Tidak ada tugas.")
    else:
        msgs = []
        for task in tasks:
            deadline = datetime.strptime(task["deadline"], "%Y-%m-%d").strftime("%d-%m-%Y")
            msgs.append(
                f"📌 Dari: {task['giver_alias']}\nTugas: {task['description']}\nDeadline: {deadline}"
            )
        await update.message.reply_text("\n\n".join(msgs))


async def approve_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await db.fetch_user(user_id)
    if not user or user["alias"] != "owner":
        await update.message.reply_text("Kamu tidak punya akses.")
        return

    pending = await db.fetch_pending_users()
    if not pending:
        await update.message.reply_text("Tidak ada user pending.")
        return

    keyboard = []
    for u in pending:
        name = f"{u['first_name']} {u['last_name'] or ''}".strip()
        keyboard.append(
            [InlineKeyboardButton(name, callback_data=f"approve_{u['id']}")]
        )
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("User pending:", reply_markup=reply_markup)


async def handle_approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("approve_"):
        user_id = int(data.split("_")[1])
        context.user_data["pending_user_id"] = user_id
        await query.message.reply_text("Ketik alias baru (1 kata):")
        return 1  # NEXT STEP: alias


async def handle_alias_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    alias = update.message.text.strip()
    context.user_data["alias"] = alias
    await update.message.reply_text("Ketik divisi user:")
    return 2  # NEXT STEP: division


async def handle_division_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    division = update.message.text.strip()
    context.user_data["division"] = division
    keyboard = [
        [InlineKeyboardButton("✅ Boleh", callback_data="assign_yes"),
         InlineKeyboardButton("❌ Tidak Boleh", callback_data="assign_no")]
    ]
    await update.message.reply_text(
        "Boleh kasih tugas?", reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return 3  # NEXT STEP: can_assign


async def handle_assign_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data
    can_assign = choice == "assign_yes"

    user_id = context.user_data["pending_user_id"]
    alias = context.user_data["alias"]
    division = context.user_data["division"]

    await db.approve_user(user_id, alias, division, can_assign)
    await query.message.reply_text("User berhasil disetujui & ditambahkan.")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Dibatalkan.")
    return ConversationHandler.END


# === MAIN FUNCTION ===
async def main():
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("list", list_tasks))
    application.add_handler(CommandHandler("approve", approve_menu))

    approve_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_approve_callback, pattern="^approve_")],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_alias_input)],
            2: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_division_input)],
            3: [CallbackQueryHandler(handle_assign_choice, pattern="^(assign_yes|assign_no)$")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(approve_conv)

    # Set webhook otomatis
    webhook_info = await application.bot.get_webhook_info()
    if webhook_info.url != WEBHOOK_URL:
        await application.bot.set_webhook(url=WEBHOOK_URL)
        logger.info("Webhook berhasil disetel.")

    logger.info("Bot jalan di webhook mode.")
    await application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path="webhook",
        webhook_url=WEBHOOK_URL,
    )


if __name__ == "__main__":
    asyncio.run(main())

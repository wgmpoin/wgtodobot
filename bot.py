import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import timedelta, timezone
import db
import os

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("BOT_TOKEN")
OWNER_ID = int(os.environ.get("OWNER_ID"))

(ADD_ALIAS, ADD_DESC, ADD_DEADLINE) = range(3)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = db.fetch_user(user_id)
    if user:
        await update.message.reply_text(
            "Bot aktif. Gunakan /menu untuk lihat perintah."
        )
    else:
        db.add_pending_user(update.effective_user)
        await update.message.reply_text(
            "Permintaan akses dikirim. Tunggu persetujuan."
        )
        # Notifikasi ke owner
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=(
                f"Ada user baru minta akses:\n"
                f"ID: {update.effective_user.id}\n"
                f"Nama: {update.effective_user.first_name} {update.effective_user.last_name}"
            ),
        )


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "/add - Tambah tugas\n"
        "/list - Lihat tugas\n"
        "/listuser - Daftar user\n"
        "/pending - Lihat pending user\n"
        "/approve - Approve user\n"
        "/remove_user - Hapus user\n"
        "/delete_task - Hapus tugas\n"
        "/info - Info bot\n"
        "/help - Bantuan"
    )
    await update.message.reply_text(text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await menu(update, context)


async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Untuk hapus perintah, hubungi owner.")


async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = db.fetch_all_users()
    available = [u for u in users if u["id"] != update.effective_user.id]
    if not available:
        await update.message.reply_text("Tidak ada user lain untuk diberi tugas.")
        return ConversationHandler.END
    buttons = [[u["alias"]] for u in available]
    context.user_data["users"] = available
    await update.message.reply_text(
        "Pilih penerima tugas:",
        reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True),
    )
    return ADD_ALIAS


async def add_alias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    alias = update.message.text.strip().lower()
    users = context.user_data["users"]
    for user in users:
        if user["alias"].lower() == alias:
            context.user_data["receiver"] = user["id"]
            await update.message.reply_text("Isi deskripsi tugas:")
            return ADD_DESC
    await update.message.reply_text("Alias tidak valid.")
    return ConversationHandler.END


async def add_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["desc"] = update.message.text
    await update.message.reply_text("Isi deadline tugas (YYYY-MM-DD):")
    return ADD_DEADLINE


async def add_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    deadline = update.message.text
    db.add_task(
        giver_id=update.effective_user.id,
        receiver_id=context.user_data["receiver"],
        description=context.user_data["desc"],
        deadline=deadline,
    )
    await update.message.reply_text("Tugas ditambahkan.")

    # Notifikasi otomatis ke penerima tugas
    receiver_id = context.user_data["receiver"]
    desc = context.user_data["desc"]
    giver_name = update.effective_user.first_name
    await context.bot.send_message(
        chat_id=receiver_id,
        text=(
            f"Kamu mendapat tugas baru:\n\n"
            f"Dari: {giver_name}\n"
            f"Tugas: {desc}\n"
            f"Deadline: {deadline}"
        ),
    )

    return ConversationHandler.END


async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = db.fetch_my_tasks(update.effective_user.id)
    if not tasks:
        await update.message.reply_text("Tidak ada tugas.")
        return
    text = "Tugas kamu:\n"
    for task in tasks:
        text += f"- ID:{task['id']} | {task['description']} (Deadline: {task['deadline']})\n"
    await update.message.reply_text(text)


async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = db.fetch_all_users()
    text = "Daftar user:\n"
    for user in users:
        text += (
            f"{user['alias']} ({user['division']}) - {user['role']}\n"
        )
    await update.message.reply_text(text)


async def pending_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Khusus owner.")
        return
    pending = db.fetch_pending_users()
    if not pending:
        await update.message.reply_text("Tidak ada pending user.")
        return
    text = "Pending user:\n"
    for user in pending:
        text += (
            f"{user['id']} - {user['first_name']} {user['last_name']}\n"
        )
    await update.message.reply_text(text)


async def approve_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Khusus owner.")
        return
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            "Format: /approve <user_id> <alias> <division>"
        )
        return
    user_id = int(args[0])
    alias = args[1]
    division = args[2]
    db.approve_user(user_id, alias, division)
    await update.message.reply_text("User disetujui.")


async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Khusus owner.")
        return
    args = context.args
    if not args:
        await update.message.reply_text("Format: /remove_user <alias>")
        return
    alias = args[0]
    user = db.fetch_user_by_alias(alias)
    if not user:
        await update.message.reply_text("Alias tidak ditemukan.")
        return
    db.remove_user(user["id"])
    await update.message.reply_text(f"User {alias} dihapus.")


async def delete_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Khusus owner.")
        return
    args = context.args
    if not args:
        await update.message.reply_text("Format: /delete_task <task_id>")
        return
    db.delete_task(int(args[0]))
    await update.message.reply_text("Tugas dihapus.")


async def reminder_job(app):
    users = db.fetch_all_users()
    for user in users:
        tasks = db.fetch_my_tasks(user["id"])
        if tasks:
            try:
                await app.bot.send_message(
                    chat_id=user["id"],
                    text="Kamu masih punya tugas, cek /list."
                )
            except Exception as e:
                logging.error(f"Gagal kirim ke {user['alias']}: {e}")


app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("menu", menu))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("info", info_command))
app.add_handler(CommandHandler("list", list_tasks))
app.add_handler(CommandHandler("listuser", list_users))
app.add_handler(CommandHandler("pending", pending_users))
app.add_handler(CommandHandler("approve", approve_user))
app.add_handler(CommandHandler("remove_user", remove_user))
app.add_handler(CommandHandler("delete_task", delete_task))

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("add", add_start)],
    states={
        ADD_ALIAS: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND, add_alias
            )
        ],
        ADD_DESC: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND, add_desc
            )
        ],
        ADD_DEADLINE: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND, add_deadline
            )
        ],
    },
    fallbacks=[],
)
app.add_handler(conv_handler)

scheduler = AsyncIOScheduler(timezone=timezone(timedelta(hours=7)))
scheduler.add_job(reminder_job, "cron", hour=8, minute=10, args=[app])
scheduler.start()

if __name__ == "__main__":
    app.run_polling()

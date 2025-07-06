import os
import logging
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Inisialisasi Flask
app = Flask(__name__)

# Config
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Pastikan sudah set di Render
WEBHOOK_URL = "https://wgtodobot.onrender.com/webhook"

# States untuk ConversationHandler
ASK_DESC, ASK_DEADLINE, ASK_RECEIVER = range(3)

# =============================================
# HANDLER COMMAND
# =============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /start"""
    await update.message.reply_text(
        "🤖 **Bot Manajemen Tugas**\n\n"
        "Perintah yang tersedia:\n"
        "/add - Tambah tugas baru\n"
        "/list - Lihat tugas Anda\n"
        "/help - Bantuan"
    )

async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /add"""
    await update.message.reply_text("📝 Masukkan deskripsi tugas:")
    return ASK_DESC

async def ask_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 1: Minta deadline"""
    context.user_data['desc'] = update.message.text
    await update.message.reply_text("📅 Masukkan deadline (YYYY-MM-DD):")
    return ASK_DEADLINE

async def ask_receiver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 2: Minta penerima"""
    context.user_data['deadline'] = update.message.text
    await update.message.reply_text("👤 Masukkan username penerima:")
    return ASK_RECEIVER

async def save_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 3: Simpan tugas"""
    context.user_data['receiver'] = update.message.text
    
    # Simpan ke database (contoh simpan di memory)
    task = {
        'giver': update.effective_user.username,
        'receiver': context.user_data['receiver'],
        'desc': context.user_data['desc'],
        'deadline': context.user_data['deadline']
    }
    
    await update.message.reply_text(
        f"✅ Tugas berhasil disimpan!\n\n"
        f"📝 Deskripsi: {task['desc']}\n"
        f"📅 Deadline: {task['deadline']}\n"
        f"👤 Penerima: @{task['receiver']}"
    )
    return ConversationHandler.END

async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk /list"""
    await update.message.reply_text("🔍 Fitur ini akan menampilkan daftar tugas (dalam pengembangan)")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Batalkan conversasi"""
    await update.message.reply_text("❌ Proses dibatalkan")
    return ConversationHandler.END

# =============================================
# SETUP BOT
# =============================================

def setup_bot():
    app = Application.builder().token(BOT_TOKEN).build()

    # Handler untuk /add (conversation)
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('add', add_task)],
        states={
            ASK_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_deadline)],
            ASK_DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_receiver)],
            ASK_RECEIVER: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_task)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # Tambahkan semua handler
    app.add_handler(CommandHandler('start', start))
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler('list', list_tasks))
    
    return app

# =============================================
# FLASK ROUTES
# =============================================

@app.route('/')
def home():
    return "🤖 Bot Berjalan!", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    bot_app = setup_bot()
    update = Update.de_json(request.get_json(), bot_app.bot)
    bot_app.process_update(update)
    return "OK", 200

# =============================================
# JALANKAN BOT
# =============================================

if __name__ == '__main__':
    bot_app = setup_bot()
    bot_app.run_polling()

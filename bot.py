import os
import asyncio
import logging
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes
)
from supabase import create_client
from datetime import datetime

# Konfigurasi logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Inisialisasi environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
PORT = int(os.getenv("PORT", "10000"))  # Sesuai port Render

# Inisialisasi Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Inisialisasi Flask
app = Flask(__name__)

# Inisialisasi Telegram Bot
application = Application.builder().token(BOT_TOKEN).build()

# States untuk ConversationHandler
ASK_DESC, ASK_DEADLINE, ASK_RECEIVER = range(3)

# =============================================
# HANDLER UNTUK COMMAND TELEGRAM
# =============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /start"""
    telegram_id = update.effective_user.id
    try:
        user = supabase.table("users").select("*").eq("id", telegram_id).execute().data
        
        if user:
            await update.message.reply_text(
                f"Halo {user[0]['alias']}! Kamu sudah terdaftar.\n"
                "Gunakan /add untuk menambah tugas."
            )
        else:
            await update.message.reply_text(
                "⚠️ Kamu belum terdaftar. Hubungi admin untuk didaftarkan."
            )
    except Exception as e:
        logger.error(f"Error di /start: {e}")
        await update.message.reply_text("❌ Terjadi error. Coba lagi nanti.")

async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk memulai proses penambahan tugas"""
    telegram_id = update.effective_user.id
    try:
        user = supabase.table("users").select("*").eq("id", telegram_id).execute().data
        
        if not user or not user[0].get("can_add_task", False):
            await update.message.reply_text("❌ Kamu tidak punya izin menambah tugas.")
            return ConversationHandler.END
        
        await update.message.reply_text("✏️ Masukkan deskripsi tugas:")
        return ASK_DESC
    except Exception as e:
        logger.error(f"Error di /add: {e}")
        await update.message.reply_text("❌ Gagal memproses. Coba lagi.")
        return ConversationHandler.END

async def ask_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 1: Meminta deadline"""
    context.user_data["description"] = update.message.text.strip()
    await update.message.reply_text("📅 Masukkan deadline (format YYYY-MM-DD):")
    return ASK_DEADLINE

async def ask_receiver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 2: Meminta penerima tugas"""
    deadline_str = update.message.text.strip()
    try:
        datetime.strptime(deadline_str, "%Y-%m-%d")
        context.user_data["deadline"] = deadline_str
        await update.message.reply_text("👤 Masukkan alias penerima tugas:")
        return ASK_RECEIVER
    except ValueError:
        await update.message.reply_text("❌ Format tanggal salah. Gunakan YYYY-MM-DD. Coba lagi:")
        return ASK_DEADLINE

async def save_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 3: Menyimpan tugas ke database"""
    alias = update.message.text.strip()
    try:
        receiver = supabase.table("users").select("*").eq("alias", alias).execute().data
        
        if not receiver:
            await update.message.reply_text("❌ Penerima tidak ditemukan. Proses dibatalkan.")
            return ConversationHandler.END

        task = {
            "giver_id": update.effective_user.id,
            "receiver_id": receiver[0]["id"],
            "description": context.user_data["description"],
            "deadline": context.user_data["deadline"],
            "created_at": datetime.utcnow().isoformat()
        }
        
        supabase.table("tasks").insert(task).execute()
        await update.message.reply_text("✅ Tugas berhasil ditambahkan!")
        
    except Exception as e:
        logger.error(f"Error menyimpan tugas: {e}")
        await update.message.reply_text("❌ Gagal menyimpan tugas. Coba lagi.")
    
    return ConversationHandler.END

async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /list"""
    telegram_id = update.effective_user.id
    try:
        tasks = supabase.table("tasks").select("*").or_(
            f"giver_id.eq.{telegram_id},receiver_id.eq.{telegram_id}"
        ).execute().data

        if not tasks:
            await update.message.reply_text("📭 Tidak ada tugas untukmu saat ini.")
            return

        pesan = "📋 Daftar Tugas Anda:\n\n"
        for t in tasks:
            status = "⌛" if datetime.strptime(t['deadline'], "%Y-%m-%d") > datetime.utcnow() else "⏳"
            pesan += f"{status} {t['description']}\n   📅 {t['deadline']}\n\n"

        await update.message.reply_text(pesan)
    except Exception as e:
        logger.error(f"Error di /list: {e}")
        await update.message.reply_text("❌ Gagal mengambil daftar tugas.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk command /help"""
    bantuan = (
        "🤖 *Daftar Perintah* 🤖\n\n"
        "/start - Memulai bot\n"
        "/add - Tambah tugas baru\n"
        "/list - Lihat tugas Anda\n"
        "/help - Tampilkan pesan bantuan\n\n"
        "Gunakan format YYYY-MM-DD untuk deadline."
    )
    await update.message.reply_text(bantuan)

# =============================================
# SETUP HANDLER DAN WEBHOOK
# =============================================

def setup_handlers():
    """Mengatur semua handler untuk Telegram bot"""
    # Handler untuk percakapan tambah tugas
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add", add_start)],
        states={
            ASK_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_deadline)],
            ASK_DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_receiver)],
            ASK_RECEIVER: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_task)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
    )

    # Tambahkan semua handler
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("list", list_tasks))
    application.add_handler(CommandHandler("help", help_command))

    # Log semua handler yang terdaftar
    logger.info("Handler berhasil diatur")

@app.route('/')
def home():
    """Endpoint untuk health check"""
    return "🤖 Bot sedang berjalan dengan baik!", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    """Endpoint untuk menerima update dari Telegram"""
    if request.method == 'POST':
        try:
            # Parse update dari Telegram
            update = Update.de_json(request.get_json(), application.bot)
            
            # Proses update secara asynchronous
            asyncio.run(application.process_update(update))
            
            return jsonify({"status": "success"}), 200
        except Exception as e:
            logger.error(f"Error memproses update: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
    return jsonify({"status": "error", "message": "Method not allowed"}), 405

# =============================================
# FUNGSI UTAMA
# =============================================

def init_bot():
    """Inisialisasi bot"""
    setup_handlers()
    logger.info("Bot berhasil diinisialisasi")

if __name__ == '__main__':
    init_bot()
    app.run(host='0.0.0.0', port=PORT, debug=False)

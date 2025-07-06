import os
import asyncio
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)
from supabase import create_client, Client

# =============================================
# KONFIGURASI AWAL
# =============================================

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
WEBHOOK_URL = "https://wgtodobot.onrender.com/webhook"  # Ganti dengan URL Anda
PORT = int(os.getenv('PORT', 10000))

# Inisialisasi Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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
    try:
        user_id = update.effective_user.id
        user = supabase.table('users').select('*').eq('id', user_id).execute().data
        
        if user:
            await update.message.reply_text(
                f"Halo {user[0]['alias']}! 🎉\n"
                "Anda sudah terdaftar.\n"
                "Gunakan /add untuk menambah tugas."
            )
        else:
            await update.message.reply_text(
                "⚠️ Anda belum terdaftar.\n"
                "Hubungi admin untuk didaftarkan."
            )
    except Exception as e:
        logger.error(f"Error di /start: {e}")
        await update.message.reply_text("❌ Terjadi kesalahan. Silakan coba lagi.")

async def add_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mulai proses penambahan tugas"""
    try:
        user_id = update.effective_user.id
        user = supabase.table('users').select('*').eq('id', user_id).execute().data
        
        if not user or not user[0].get('can_add_task', False):
            await update.message.reply_text("❌ Anda tidak memiliki izin untuk menambah tugas.")
            return ConversationHandler.END
            
        await update.message.reply_text(
            "📝 Masukkan deskripsi tugas:\n"
            "(Contoh: Buat laporan penjualan bulanan)"
        )
        return ASK_DESC
    except Exception as e:
        logger.error(f"Error di /add: {e}")
        await update.message.reply_text("❌ Gagal memulai proses. Silakan coba lagi.")
        return ConversationHandler.END

async def ask_task_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Meminta deadline tugas"""
    context.user_data['description'] = update.message.text.strip()
    await update.message.reply_text(
        "📅 Masukkan deadline tugas (YYYY-MM-DD):\n"
        "(Contoh: 2025-07-15)"
    )
    return ASK_DEADLINE

async def ask_task_receiver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Meminta penerima tugas"""
    deadline = update.message.text.strip()
    try:
        datetime.strptime(deadline, '%Y-%m-%d')
        context.user_data['deadline'] = deadline
        await update.message.reply_text(
            "👤 Masukkan alias penerima tugas:\n"
            "(Contoh: budi)"
        )
        return ASK_RECEIVER
    except ValueError:
        await update.message.reply_text(
            "❌ Format tanggal salah!\n"
            "Gunakan format YYYY-MM-DD.\n"
            "Silakan coba lagi:"
        )
        return ASK_DEADLINE

async def save_new_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menyimpan tugas baru ke database"""
    alias = update.message.text.strip()
    try:
        # Cari user penerima
        receiver = supabase.table('users').select('*').eq('alias', alias).execute().data
        
        if not receiver:
            await update.message.reply_text(
                "❌ Penerima tidak ditemukan!\n"
                "Proses dibatalkan."
            )
            return ConversationHandler.END
        
        # Simpan ke database
        task_data = {
            'giver_id': update.effective_user.id,
            'receiver_id': receiver[0]['id'],
            'description': context.user_data['description'],
            'deadline': context.user_data['deadline'],
            'created_at': datetime.utcnow().isoformat()
        }
        
        supabase.table('tasks').insert(task_data).execute()
        
        await update.message.reply_text(
            "✅ Tugas berhasil ditambahkan!\n"
            f"Penerima: {alias}\n"
            f"Deadline: {context.user_data['deadline']}"
        )
        
        # Kirim notifikasi ke penerima
        try:
            bot = Bot(token=BOT_TOKEN)
            await bot.send_message(
                chat_id=receiver[0]['id'],
                text=f"📌 Anda mendapat tugas baru!\n\n"
                     f"Deskripsi: {context.user_data['description']}\n"
                     f"Deadline: {context.user_data['deadline']}"
            )
        except Exception as e:
            logger.error(f"Gagal mengirim notifikasi: {e}")
            
    except Exception as e:
        logger.error(f"Error menyimpan tugas: {e}")
        await update.message.reply_text(
            "❌ Gagal menyimpan tugas!\n"
            "Silakan coba lagi nanti."
        )
    
    return ConversationHandler.END

async def list_user_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menampilkan daftar tugas"""
    try:
        user_id = update.effective_user.id
        tasks = supabase.table('tasks').select('*').or_(
            f'giver_id.eq.{user_id},receiver_id.eq.{user_id}'
        ).execute().data
        
        if not tasks:
            await update.message.reply_text("📭 Anda tidak memiliki tugas saat ini.")
            return
        
        message = "📋 Daftar Tugas Anda:\n\n"
        for task in tasks:
            status = "✅" if datetime.strptime(task['deadline'], '%Y-%m-%d') > datetime.utcnow() else "⏳"
            message += (
                f"{status} {task['description']}\n"
                f"   🗓 {task['deadline']}\n"
                f"   👤 {'Anda memberi' if task['giver_id'] == user_id else 'Anda menerima'}\n\n"
            )
        
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error di /list: {e}")
        await update.message.reply_text("❌ Gagal mengambil daftar tugas.")

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Membatalkan percakapan"""
    await update.message.reply_text("❌ Proses dibatalkan.")
    return ConversationHandler.END

# =============================================
# SETUP APPLICATION
# =============================================

def setup_handlers():
    """Mengatur semua handler untuk bot"""
    
    # Handler untuk percakapan tambah tugas
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('add', add_task_start)],
        states={
            ASK_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_task_deadline)],
            ASK_DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_task_receiver)],
            ASK_RECEIVER: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_new_task)],
        },
        fallbacks=[CommandHandler('cancel', cancel_conversation)],
    )
    
    # Tambahkan semua handler
    application.add_handler(CommandHandler('start', start))
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('list', list_user_tasks))
    
    # Log semua handler yang terdaftar
    logger.info("Handler berhasil diatur")

# =============================================
# FLASK ROUTES
# =============================================

@app.route('/')
def health_check():
    """Endpoint untuk health check"""
    return "🤖 Bot berjalan dengan baik!", 200

@app.route('/webhook', methods=['POST'])
async def telegram_webhook():
    """Endpoint untuk menerima update dari Telegram"""
    if request.method == 'POST':
        try:
            # Parse update dari Telegram
            update = Update.de_json(request.get_json(), application.bot)
            
            # Proses update
            await application.process_update(update)
            
            return jsonify({'status': 'success'}), 200
        except Exception as e:
            logger.error(f"Error memproses update: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
    return jsonify({'status': 'error', 'message': 'Method not allowed'}), 405

# =============================================
# FUNGSI UTAMA
# =============================================

async def set_telegram_webhook():
    """Mengatur webhook untuk Telegram"""
    try:
        await application.bot.set_webhook(
            url=WEBHOOK_URL,
            drop_pending_updates=True
        )
        logger.info(f"Webhook berhasil disetel ke: {WEBHOOK_URL}")
    except Exception as e:
        logger.error(f"Gagal menyetel webhook: {e}")

def main():
    """Fungsi utama untuk menjalankan bot"""
    # Setup handlers
    setup_handers()
    
    # Set webhook
    asyncio.run(set_telegram_webhook())
    
    # Jalankan Flask
    app.run(host='0.0.0.0', port=PORT)

if __name__ == '__main__':
    main()

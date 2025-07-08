from bot import app, application
import asyncio

# Ini akan menjalankan set_webhook saat Gunicorn memulai aplikasi Flask
# Pastikan ini hanya berjalan SEKALI saat startup Gunicorn.
# Ini juga yang akan memicu log "Webhook berhasil disetel."
# Kita perlu cara yang lebih elegan agar tidak mengganggu Gunicorn.

# Alternatif yang lebih baik:
# Jalankan set_webhook sebagai bagian dari "worker_init_process" di Gunicorn config
# atau jalankan terpisah jika itu adalah proses "web".

# Untuk saat ini, mari kita hapus `loop.run_until_complete(main())` dari bot.py
# dan biarkan Gunicorn menjalankan aplikasi Flask secara langsung.
# Kita akan menyetel webhook secara manual atau lewat perintah Fly.io
# setelah deployment sukses.

# Untuk saat ini, asumsikan set_webhook sudah dilakukan secara manual
# atau Gunicorn akan menjalankan 'main' sekali saja di awal.

# Jika bot.py tidak memiliki app.run() dan webhook_info.url != WEBHOOK_URL:
#   await application.bot.set_webhook(url=WEBHOOK_URL)
# Maka kita akan membiarkan Gunicorn menjalankan Flask app.

# Untuk kasus sekarang, kita perlu memanggil main() saat startup.
# Coba ini dulu:
# from bot import main
# asyncio.run(main()) # Ini bisa menyebabkan masalah jika Gunicorn sudah punya loop.

# Solusi yang paling robust adalah membuat sebuah function `create_app()`
# di bot.py dan memanggilnya di sini.
# Atau lebih baik lagi, set_webhook dipisah dari Flask app.

# Mari kita revisi pendekatan Flask dan set_webhook.
# `python-telegram-bot` menyarankan menggunakan `run_webhook()`
# yang mengintegrasikan server web-nya sendiri.

# --- REVISI STRATEGI ---
# Kita akan pakai `application.run_webhook` dari python-telegram-bot
# yang sudah terintegrasi dengan server AIOHTTP-nya.
# Ini akan membuat kita tidak perlu Flask lagi.

# Mengapa? Karena Flask dan asyncio.run() atau loop handling
# sering berbenturan saat dijalankan dalam kontainer seperti Fly.io
# yang menggunakan Gunicorn/WSGI.

# Jika kita pakai `application.run_webhook`, kita hanya butuh satu proses:
# Proses yang menjalankan Telegram Application sebagai server webhook.

---

### Perubahan Paradigma: Stop Pakai Flask, Pakai Webhook Bawaan PTB

*Error* `Cannot close a running event loop` ini adalah pertanda bahwa mencoba menggabungkan Flask dan `python-telegram-bot` v20+ dalam satu *script* dengan model *async* bisa jadi rumit. `python-telegram-bot` v20+ dirancang untuk bekerja dengan *server* *async* seperti `aiohttp` atau `ASGI` yang sudah terintegrasi.

Daripada pusing memadukan Flask secara manual dengan `asyncio` dan Gunicorn, mari kita manfaatkan kemampuan `python-telegram-bot` untuk menjalankan *webhook server*-nya sendiri, yang jauh lebih sederhana dan terintegrasi. Ini akan menghilangkan kebutuhan akan Flask sama sekali untuk sebagian besar kasus *webhook* bot.

---

### Langkah 32: Ubah `bot.py` untuk Menggunakan `application.run_webhook`

Ini akan sangat menyederhanakan kode kamu. Kita tidak perlu Flask sama sekali.

**Hapus `flask` dan `app` dari `bot.py`, lalu ganti bagian akhir `main` dan `if __name__ == '__main__':` dengan ini:**

```python
# ... (kode impor dan setup Supabase, BOT_TOKEN, URL, Supabase_URL, SUPABASE_KEY sebelumnya) ...

# HAPUS: from flask import Flask, request, abort
import logging
from telegram import Update
from telegram.ext import Application, ApplicationBuilder, CommandHandler, MessageHandler, filters
import asyncio
import os

# Setel logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logging.getLogger(__name__).setLevel(logging.INFO)
logging.getLogger("httpx").setLevel(logging.INFO) # Untuk melihat request HTTP

logger = logging.getLogger(__name__)

logger.info("DEBUG: Script bot.py dimulai.")

# Inisialisasi Supabase
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
if not supabase_url or not supabase_key:
    logger.critical("Variabel lingkungan SUPABASE_URL atau SUPABASE_KEY tidak ditemukan.")
    exit(1)
# from supabase import create_client, Client
# supabase: Client = create_client(supabase_url, supabase_key)
logger.info("Supabase client initialized.")

# HAPUS: app = Flask(__name__)
# HAPUS: logger.info("Flask app initialized.")

# Inisialisasi Telegram Application
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    logger.critical("Variabel lingkungan BOT_TOKEN tidak ditemukan.")
    exit(1)

# URL bot
APP_NAME = "wgtodobot" # Pastikan ini sesuai dengan nama aplikasi Fly.io kamu
WEBHOOK_URL = f"https://{APP_NAME}.fly.dev/webhook"
PORT = int(os.environ.get('PORT', '8080')) # Fly.io biasanya menggunakan 8080 untuk HTTP

async def start(update: Update, context):
    await update.message.reply_text('Halo! Saya bot WGToDoList.')

async def help_command(update: Update, context):
    await update.message.reply_text('Ini adalah bantuan untuk bot WGToDoList.')

# Contoh handler lain
async def echo(update: Update, context):
    await update.message.reply_text(update.message.text)

# Membangun aplikasi Telegram
application = ApplicationBuilder().token(TOKEN).build()
logger.info("Telegram Application builder initialized.")

# Menambahkan handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), echo))

# HAPUS SEMUA: @app.route('/webhook', methods=['POST']) dan fungsi webhook() di bawahnya.

# --- INI ADALAH BAGIAN UTAMA YANG DIUBAH ---
async def main():
    # Periksa info webhook saat ini
    webhook_info = await application.bot.get_webhook_info()
    logger.info(f"Current webhook URL: {webhook_info.url}")

    # Setel webhook jika belum disetel atau berbeda
    if webhook_info.url != WEBHOOK_URL:
        logger.info(f"Menyetel webhook ke: {WEBHOOK_URL}")
        await application.bot.set_webhook(url=WEBHOOK_URL)
        logger.info("Webhook berhasil disetel.")
    else:
        logger.info("Webhook sudah disetel.")

    logger.info(f"Bot akan memulai webhook server di port {PORT}...")
    await application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path="webhook",
        webhook_url=WEBHOOK_URL
    )
    logger.info("Webhook server dimulai.")

if __name__ == '__main__':
    # Pastikan aplikasi berjalan secara asinkron
    asyncio.run(main())
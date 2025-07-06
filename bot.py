import os
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes
)
from supabase import create_client
from datetime import datetime
import asyncio # Import asyncio untuk menjalankan coroutine

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_PATH = "/webhook"
PORT = int(os.getenv("PORT", "5000"))
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)

# Inisialisasi Application di luar fungsi main() agar bisa diakses global
# dan set mode webhook.
application = (
    Application.builder()
    .token(BOT_TOKEN)
    .updater(None)  # Nonaktifkan polling
    .build()
)

# Konfigurasi webhook setelah build()
# URL webhook harus diambil dari lingkungan tempat bot di-deploy (misal Render/Fly.io)
# Contoh: f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}{WEBHOOK_PATH}"
# Untuk testing lokal, bisa pakai ngrok atau sejenisnya.
# Karena kamu pakai Fly.io, pastikan BOT_WEBHOOK_URL diset di sana.
# Di Fly.io, ini biasanya domain app kamu.
# contoh: https://wgtodobot.fly.dev/webhook
# application.set_webhook(url=f"https://your-fly-io-app-domain.fly.dev{WEBHOOK_PATH}")

ASK_DESC, ASK_DEADLINE, ASK_RECEIVER = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    user = supabase.table("users").select("*").eq("id", telegram_id).execute().data
    if user:
        await update.message.reply_text(f"Halo {user[0]['alias']}, kamu sudah terdaftar.\nGunakan /add untuk tambah tugas.")
    else:
        # Menambahkan pesan untuk user yang belum terdaftar dan instruksi ke owner
        owner_id_data = supabase.table("users").select("id").eq("role", "owner").limit(1).execute().data
        owner_id = owner_id_data[0]["id"] if owner_id_data else None

        if owner_id:
            # Tambahkan user ke pending_users
            pending_user_data, _ = supabase.table("pending_users").insert({
                "id": telegram_id,
                "first_name": update.effective_user.first_name,
                "last_name": update.effective_user.last_name,
                "requested_by": None # Bisa diset jika ada yang merequest, atau None jika user sendiri yang start
            }).execute()

            # Notifikasi ke owner
            await context.bot.send_message(
                chat_id=owner_id,
                text=f"Pengguna baru **{update.effective_user.first_name}** (ID: `{telegram_id}`) mencoba menggunakan bot.\n\n"
                     f"Apakah ingin di-_approve_?\n"
                     f"/approve_user {telegram_id} atau /reject_user {telegram_id}",
                parse_mode="Markdown"
            )
            await update.message.reply_text("⚠️ Kamu belum terdaftar, permintaan pendaftaranmu telah dikirim ke owner untuk persetujuan.")
        else:
            await update.message.reply_text("⚠️ Kamu belum terdaftar dan tidak ada owner terdaftar untuk memproses permintaanmu. Hubungi developer bot.")


async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    user = supabase.table("users").select("*").eq("id", telegram_id).execute().data
    if not user or not user[0].get("can_assign", False):
        await update.message.reply_text("❌ Kamu tidak punya izin menambah tugas.")
        return ConversationHandler.END
    await update.message.reply_text("✏️ Masukkan deskripsi tugas:")
    return ASK_DESC

async def ask_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["description"] = update.message.text.strip()
    await update.message.reply_text("📅 Masukkan deadline (YYYY-MM-DD):")
    return ASK_DEADLINE

async def ask_receiver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    deadline_str = update.message.text.strip()
    try:
        datetime.strptime(deadline_str, "%Y-%m-%d")
    except ValueError:
        await update.message.reply_text("❌ Format deadline salah, harus YYYY-MM-DD. Coba lagi:")
        return ASK_DEADLINE
    context.user_data["deadline"] = deadline_str
    
    # Mengambil daftar alias user yang bisa menerima tugas
    users_data = supabase.table("users").select("alias").execute().data
    aliases = [user["alias"] for user in users_data]
    
    if not aliases:
        await update.message.reply_text("Tidak ada user terdaftar. Batal.")
        return ConversationHandler.END

    keyboard = [[alias] for alias in aliases]
    reply_markup = telegram.ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("👤 Pilih alias penerima tugas:", reply_markup=reply_markup)
    return ASK_RECEIVER

async def save_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    alias = update.message.text.strip()
    receiver = supabase.table("users").select("*").eq("alias", alias).execute().data
    if not receiver:
        await update.message.reply_text("❌ Alias penerima tidak ditemukan. Batal.")
        return ConversationHandler.END

    task = {
        "giver_id": update.effective_user.id,
        "receiver_id": receiver[0]["id"],
        "description": context.user_data["description"],
        "deadline": context.user_data["deadline"],
        "created_at": datetime.utcnow().isoformat() + "Z" # Tambahkan 'Z' untuk UTC
    }
    supabase.table("tasks").insert(task).execute()

    await update.message.reply_text("✅ Tugas berhasil ditambahkan.")
    return ConversationHandler.END

async def list_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    tasks = supabase.table("tasks").select("*").or_(
        f"giver_id.eq.{telegram_id},receiver_id.eq.{telegram_id}"
    ).execute().data

    if not tasks:
        await update.message.reply_text("📭 Tidak ada tugas untukmu.")
        return

    pesan = "📋 Daftar Tugas:\n\n"
    for t in tasks:
        # Mendapatkan alias giver dan receiver
        giver = supabase.table("users").select("alias").eq("id", t['giver_id']).execute().data
        receiver = supabase.table("users").select("alias").eq("id", t['receiver_id']).execute().data
        
        giver_alias = giver[0]['alias'] if giver else "Tidak Dikenal"
        receiver_alias = receiver[0]['alias'] if receiver else "Tidak Dikenal"

        pesan += f"- **{t['description']}**\n" \
                 f"  Dari: @{giver_alias}\n" \
                 f"  Untuk: @{receiver_alias}\n" \
                 f"  Deadline: {t['deadline']}\n\n"

    await update.message.reply_text(pesan, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pesan = (
        "/start - Mulai bot\n"
        "/add - Tambah tugas\n"
        "/list - Lihat tugas\n"
        "/listuser - Lihat daftar user\n"
        "/help - Bantuan\n"
    )
    # Tambahkan perintah khusus untuk owner/admin jika user memiliki hak akses
    telegram_id = update.effective_user.id
    user_data = supabase.table("users").select("role").eq("id", telegram_id).execute().data
    if user_data and user_data[0]['role'] in ['owner', 'admin']:
        pesan += "\n--- Perintah Admin/Owner ---\n"
        pesan += "/addadm - Tambah admin (hanya Owner)\n"
        pesan += "/removeadm - Hapus admin (hanya Owner)\n"
        pesan += "/editalias - Edit alias & divisi user\n"
        # Tambahkan perintah approve/reject pending user
        pesan += "/approve_user <id> - Setujui user baru (Owner/Admin)\n"
        pesan += "/reject_user <id> - Tolak user baru (Owner/Admin)\n"
    
    await update.message.reply_text(pesan)

# --- Perintah Owner/Admin ---
async def check_admin_owner(telegram_id: int):
    user_data = supabase.table("users").select("role").eq("id", telegram_id).execute().data
    if user_data:
        return user_data[0]['role']
    return None

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_admin_owner(update.effective_user.id) != 'owner':
        await update.message.reply_text("❌ Hanya OWNER yang bisa menambah admin.")
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Gunakan: /addadm <Telegram ID user>")
        return

    user_id_to_promote = int(context.args[0])
    # Pastikan user ada dan bukan owner
    user_to_promote = supabase.table("users").select("role").eq("id", user_id_to_promote).execute().data
    if not user_to_promote:
        await update.message.reply_text(f"❌ User dengan ID {user_id_to_promote} tidak ditemukan.")
        return
    if user_to_promote[0]['role'] == 'owner':
        await update.message.reply_text(f"❌ User dengan ID {user_id_to_promote} sudah menjadi OWNER.")
        return

    supabase.table("users").update({"role": "admin", "can_assign": True}).eq("id", user_id_to_promote).execute()
    await update.message.reply_text(f"✅ User dengan ID {user_id_to_promote} berhasil dijadikan ADMIN.")

async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await check_admin_owner(update.effective_user.id) != 'owner':
        await update.message.reply_text("❌ Hanya OWNER yang bisa menghapus admin.")
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Gunakan: /removeadm <Telegram ID admin>")
        return

    admin_id_to_demote = int(context.args[0])
    # Pastikan user ada dan merupakan admin, dan bukan owner
    user_to_demote = supabase.table("users").select("role").eq("id", admin_id_to_demote).execute().data
    if not user_to_demote:
        await update.message.reply_text(f"❌ User dengan ID {admin_id_to_demote} tidak ditemukan.")
        return
    if user_to_demote[0]['role'] == 'owner':
        await update.message.reply_text(f"❌ Tidak bisa menghapus OWNER.")
        return
    if user_to_demote[0]['role'] != 'admin':
        await update.message.reply_text(f"❌ User dengan ID {admin_id_to_demote} bukan admin.")
        return

    supabase.table("users").update({"role": "user", "can_assign": False}).eq("id", admin_id_to_demote).execute()
    await update.message.reply_text(f"✅ User dengan ID {admin_id_to_demote} berhasil diturunkan dari ADMIN menjadi USER.")

async def approve_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    requester_role = await check_admin_owner(update.effective_user.id)
    if requester_role not in ['owner', 'admin']:
        await update.message.reply_text("❌ Kamu tidak punya izin untuk menyetujui user.")
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Gunakan: /approve_user <Telegram ID user>")
        return

    user_id_to_approve = int(context.args[0])
    pending_user = supabase.table("pending_users").select("*").eq("id", user_id_to_approve).execute().data

    if not pending_user:
        await update.message.reply_text(f"❌ User dengan ID {user_id_to_approve} tidak ditemukan di daftar pending.")
        return

    context.user_data['pending_user_id'] = user_id_to_approve
    await update.message.reply_text(
        f"✅ User {pending_user[0]['first_name']} (ID: {user_id_to_approve}) ditemukan.\n"
        f"Sekarang, masukkan **alias (satu kata)**, **divisi**, dan **hak akses (True/False untuk `can_assign`)** untuk user ini.\n\n"
        f"Contoh: `useralias HRD True`"
    )
    return 'APPROVE_INPUT_DETAILS'

async def approve_user_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_to_approve = context.user_data.get('pending_user_id')
    if not user_id_to_approve:
        await update.message.reply_text("Terjadi kesalahan, ID user yang akan di-approve tidak ditemukan.")
        return ConversationHandler.END

    try:
        parts = update.message.text.strip().split()
        if len(parts) != 3:
            raise ValueError("Format input salah.")
        
        alias, division, can_assign_str = parts
        can_assign = can_assign_str.lower() == 'true'

        # Cek apakah alias sudah ada
        existing_alias = supabase.table("users").select("id").eq("alias", alias).execute().data
        if existing_alias:
            await update.message.reply_text(f"❌ Alias '{alias}' sudah digunakan. Mohon coba alias lain.")
            return 'APPROVE_INPUT_DETAILS'

        # Tambahkan user ke tabel users
        supabase.table("users").insert({
            "id": user_id_to_approve,
            "alias": alias,
            "division": division,
            "role": "user", # Default role adalah user
            "can_add_task": can_assign 
        }).execute()

        # Hapus dari pending_users
        supabase.table("pending_users").delete().eq("id", user_id_to_approve).execute()

        await update.message.reply_text(f"✅ User dengan ID {user_id_to_approve} ({alias}) berhasil di-approve.")
        # Kirim notifikasi ke user yang baru di-approve
        await context.bot.send_message(
            chat_id=user_id_to_approve,
            text=f"Selamat! Akun Anda telah di-approve.\n"
                 f"Alias Anda: **@{alias}**\n"
                 f"Divisi Anda: **{division}**\n"
                 f"Anda {'' if can_assign else 'tidak '}bisa memberikan tugas.\n"
                 f"Silakan gunakan /start untuk memulai."
        )
        return ConversationHandler.END
    except ValueError as e:
        await update.message.reply_text(f"❌ Input tidak valid: {e}. Coba lagi dengan format: `alias divisi True/False`")
        return 'APPROVE_INPUT_DETAILS'
    except Exception as e:
        await update.message.reply_text(f"Terjadi kesalahan saat menyimpan user: {e}. Coba lagi.")
        return 'APPROVE_INPUT_DETAILS'


async def reject_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    requester_role = await check_admin_owner(update.effective_user.id)
    if requester_role not in ['owner', 'admin']:
        await update.message.reply_text("❌ Kamu tidak punya izin untuk menolak user.")
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Gunakan: /reject_user <Telegram ID user>")
        return

    user_id_to_reject = int(context.args[0])
    pending_user = supabase.table("pending_users").select("*").eq("id", user_id_to_reject).execute().data

    if not pending_user:
        await update.message.reply_text(f"❌ User dengan ID {user_id_to_reject} tidak ditemukan di daftar pending.")
        return
    
    # Hapus dari pending_users
    supabase.table("pending_users").delete().eq("id", user_id_to_reject).execute()
    await update.message.reply_text(f"✅ User dengan ID {user_id_to_reject} berhasil ditolak dan dihapus dari daftar pending.")
    
    # Notifikasi ke user yang ditolak (jika memungkinkan)
    await context.bot.send_message(
        chat_id=user_id_to_reject,
        text=f"Maaf, permintaan akun Anda telah ditolak oleh admin. Silakan hubungi admin jika ada pertanyaan."
    )

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    requester_role = await check_admin_owner(update.effective_user.id)
    if requester_role is None: # Hanya user terdaftar yang bisa melihat
        await update.message.reply_text("❌ Kamu belum terdaftar.")
        return

    divisions_data = supabase.table("users").select("division").distinct("division").execute().data
    divisions = [d["division"] for d in divisions_data if d["division"]]

    if not divisions:
        await update.message.reply_text("Tidak ada divisi terdaftar.")
        return

    keyboard = [[div] for div in divisions]
    reply_markup = telegram.ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Pilih divisi:", reply_markup=reply_markup)
    return 'SELECT_DIVISION_FOR_LIST'

async def show_users_by_division(update: Update, context: ContextTypes.DEFAULT_TYPE):
    division_selected = update.message.text.strip()
    users_in_division = supabase.table("users").select("alias", "id", "role").eq("division", division_selected).order("alias").execute().data

    if not users_in_division:
        await update.message.reply_text(f"Tidak ada user di divisi {division_selected}.")
        return ConversationHandler.END

    message_text = f"User di divisi {division_selected}:\n"
    keyboard_buttons = []

    for user in users_in_division:
        # Jika bukan owner/admin, sembunyikan alias jika alias di luar daftar yang terlihat.
        # Untuk kasus ini, karena semua user bisa melihat list user, kita tampilkan aliasnya.
        # Jika ada alias 'rahasia' yang kamu maksud, perlu logic tambahan di sini.
        message_text += f"- @{user['alias']} ({user['role']})\n"
        keyboard_buttons.append([user['alias']]) # Tombol untuk pilih user

    reply_markup = telegram.ReplyKeyboardMarkup(keyboard_buttons, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(message_text, reply_markup=reply_markup)
    return ConversationHandler.END # Setelah menampilkan list, bisa langsung selesai

async def edit_alias_division_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    requester_role = await check_admin_owner(update.effective_user.id)
    if requester_role not in ['owner', 'admin']:
        await update.message.reply_text("❌ Kamu tidak punya izin untuk mengedit alias atau divisi.")
        return

    users_data = supabase.table("users").select("alias").execute().data
    aliases = [user["alias"] for user in users_data]
    
    if not aliases:
        await update.message.reply_text("Tidak ada user terdaftar untuk diedit.")
        return ConversationHandler.END

    keyboard = [[alias] for alias in aliases]
    reply_markup = telegram.ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Pilih user yang ingin diedit alias/divisinya:", reply_markup=reply_markup)
    return 'EDIT_ALIAS_SELECT_USER'

async def edit_alias_division_input_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected_alias = update.message.text.strip()
    user_to_edit = supabase.table("users").select("id").eq("alias", selected_alias).execute().data
    
    if not user_to_edit:
        await update.message.reply_text("❌ Alias tidak ditemukan. Batalkan.")
        return ConversationHandler.END

    context.user_data['user_id_to_edit'] = user_to_edit[0]['id']
    await update.message.reply_text("Masukkan alias baru (satu kata) dan divisi baru (bisa kosong jika tidak ingin diubah).\n"
                                     "Contoh: `aliasbaru divisi_baru` atau `aliasbaru`")
    return 'EDIT_ALIAS_INPUT_DETAILS'

async def edit_alias_division_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_to_edit = context.user_data.get('user_id_to_edit')
    if not user_id_to_edit:
        await update.message.reply_text("Terjadi kesalahan, user tidak ditemukan untuk diedit.")
        return ConversationHandler.END

    parts = update.message.text.strip().split(maxsplit=1) # Pisahkan alias dan sisa (divisi)

    new_alias = parts[0]
    new_division = parts[1] if len(parts) > 1 else None

    # Cek apakah alias baru sudah ada, kecuali jika itu alias user yang sedang diedit
    existing_alias_check = supabase.table("users").select("id").eq("alias", new_alias).execute().data
    if existing_alias_check and existing_alias_check[0]['id'] != user_id_to_edit:
        await update.message.reply_text(f"❌ Alias '{new_alias}' sudah digunakan oleh user lain. Mohon coba alias lain.")
        return 'EDIT_ALIAS_INPUT_DETAILS' # Kembali ke langkah input

    update_data = {"alias": new_alias}
    if new_division:
        update_data["division"] = new_division
    
    supabase.table("users").update(update_data).eq("id", user_id_to_edit).execute()
    await update.message.reply_text(f"✅ Alias dan/atau divisi user berhasil diubah.")
    return ConversationHandler.END

# --- Handler Webhook ---
@app.route(WEBHOOK_PATH, methods=["POST"])
async def webhook(): # Pastikan ini juga async
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update) # Gunakan await di sini
    return "OK"

def main():
    # Setup conversation handler untuk tambah tugas
    conv_add_task_handler = ConversationHandler(
        entry_points=[CommandHandler("add", add_start)],
        states={
            ASK_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_deadline)],
            ASK_DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_receiver)],
            ASK_RECEIVER: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_task)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)] # Tambahkan fallback cancel
    )

    # Setup conversation handler untuk approve user
    conv_approve_user_handler = ConversationHandler(
        entry_points=[CommandHandler("approve_user", approve_user)],
        states={
            'APPROVE_INPUT_DETAILS': [MessageHandler(filters.TEXT & ~filters.COMMAND, approve_user_details)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)]
    )

    # Setup conversation handler untuk edit alias/divisi
    conv_edit_alias_handler = ConversationHandler(
        entry_points=[CommandHandler("editalias", edit_alias_division_start)],
        states={
            'EDIT_ALIAS_SELECT_USER': [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_alias_division_input_details)],
            'EDIT_ALIAS_INPUT_DETAILS': [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_alias_division_save)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)]
    )

    # Setup conversation handler untuk list user (pilih divisi dulu)
    conv_list_user_handler = ConversationHandler(
        entry_points=[CommandHandler("listuser", list_users)],
        states={
            'SELECT_DIVISION_FOR_LIST': [MessageHandler(filters.TEXT & ~filters.COMMAND, show_users_by_division)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)]
    )


    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_add_task_handler)
    application.add_handler(CommandHandler("list", list_tasks))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("addadm", add_admin))
    application.add_handler(CommandHandler("removeadm", remove_admin))
    application.add_handler(CommandHandler("reject_user", reject_user))
    application.add_handler(conv_approve_user_handler)
    application.add_handler(conv_edit_alias_handler)
    application.add_handler(conv_list_user_handler) # Tambahkan handler untuk /listuser

    # Jalankan bot dalam mode webhook
    # Ini penting: start_webhook perlu dijalankan di event loop
    # Pastikan Flask app tidak memblokir event loop asyncio
    async def run_bot_webhook():
        await application.start()
        # Bot akan menerima update melalui webhook, tidak perlu updater.run_polling()
        # Biarkan Flask yang menangani request HTTP

    # Menjalankan Flask app dan asyncio loop secara bersamaan
    # Ini memerlukan pendekatan yang sedikit berbeda untuk Flask dan Telegram Bot
    # karena Flask biasanya berjalan di thread utama dan blocking.
    # Untuk lingkungan seperti Render/Fly.io, bot.py akan menjadi web server
    # yang menerima request dari webhook.
    # Kamu bisa menjalankan Flask app seperti biasa dan biarkan webhook() function
    # yang memproses update dari Telegram.
    
    # Untuk memastikan `application.start()` dipanggil, kita bisa memanggilnya
    # di luar `if __name__ == "__main__":` atau di dalam `main()`
    # dan pastikan Flask dijalankan sebagai entry point.
    
    # Karena `application.run_webhook()` atau `application.start()`
    # akan memblokir, kita akan mengandalkan `webhook` endpoint Flask
    # untuk memproses update. `application.start()` hanya perlu dipanggil sekali
    # saat aplikasi dimulai untuk inisialisasi bot object.
    
    # Inisialisasi webhook URL
    # Ini harus disesuaikan dengan domain Fly.io kamu
    webhook_url = f"https://wgtodobot.fly.dev{WEBHOOK_PATH}" # Ganti dengan domain Fly.io kamu
    application.updater = None # Tidak perlu updater jika pakai webhook
    # Set webhook di awal
    # Karena ini adalah script Python yang akan dijalankan oleh Gunicorn/WSGI server,
    # kita tidak bisa langsung memanggil `await application.start()` atau `run_polling()`
    # di `main()` karena itu akan memblokir Flask app.
    # Cukup set webhook URL-nya saja.
    application.bot.set_webhook(url=webhook_url)

    print(f"Bot dimulai dalam mode webhook. URL: {webhook_url}")

if __name__ == "__main__":
    # Panggil main untuk setup handler
    main()
    # Jalankan Flask app
    app.run(host="0.0.0.0", port=PORT)

# === FILE: Dockerfile ===
# Gunakan Python 3.10 slim-buster sebagai base image
FROM python:3.10-slim-buster

# Set working directory
WORKDIR /app

# Salin requirements.txt
COPY requirements.txt .

# Upgrade pip sebelum menginstal dependencies
RUN pip install --no-cache-dir --upgrade pip

# Bersihkan cache pip untuk memastikan instalasi bersih
RUN pip cache purge

# Instal dependensi secara eksplisit dalam urutan yang benar
# Instal httpx terlebih dahulu karena ini adalah dependensi konflik
RUN pip install --no-cache-dir "httpx==0.24.1"

# Kemudian instal python-telegram-bot dengan fitur webhooks
RUN pip install --no-cache-dir "python-telegram-bot[webhooks]==20.3"

# Terakhir, instal supabase
RUN pip install --no-cache-dir "supabase==2.0.0"

# Salin semua file kode bot ke container
COPY . .

# Command default untuk proses 'web' jika tidak ditentukan oleh fly.toml
CMD ["python", "bot.py"]

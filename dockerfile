# === FILE: Dockerfile ===
FROM python:3.9-slim-buster

# Set working directory
WORKDIR /app

# Salin requirements.txt & install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Salin semua file kode bot ke container
COPY . .

# Jalankan bot
CMD ["python", "bot.py"]

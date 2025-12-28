# 1. Base Image
FROM python:3.11-slim

# --- TAMBAHAN: Agar log print() muncul seketika di docker logs ---
ENV PYTHONUNBUFFERED=1

# 2. Set Working Directory
WORKDIR /app

# 3. Buat User Non-Root (Syarat UTS)
RUN adduser --disabled-password --gecos "" appuser

# 4. Salin dan Instal Dependensi
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 5. Salin Semua Kode (Termasuk publisher & performance_test)
# Saya gabungkan di sini agar urutannya rapi
COPY src/ ./src/
COPY publisher.py ./
COPY performance_test.py ./

# 6. Atur Kepemilikan File (PENTING: Agar appuser bisa tulis database SQLite)
RUN chown -R appuser:appuser /app

# 7. Ganti ke User Non-Root
USER appuser

# 8. Expose Port
EXPOSE 8080

# 9. Perintah Eksekusi
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
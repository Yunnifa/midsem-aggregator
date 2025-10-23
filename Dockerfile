# 1. Base Image
FROM python:3.11-slim

# 2. Set Working Directory
WORKDIR /app

# 3. Buat User Non-Root
RUN adduser --disabled-password --gecos "" appuser

# 4. Salin File Dependensi
COPY requirements.txt ./

# 5. Instal Dependensi
RUN pip install --no-cache-dir -r requirements.txt

# 6. Salin Kode Aplikasi
COPY src/ ./src/

# ==== PERBAIKAN DI BAWAH INI ====
# Salin juga skrip publisher dan performance test ke /app
COPY publisher.py ./
COPY performance_test.py ./
# ==== AKHIR PERBAIKAN ====

# 7. Atur Kepemilikan File
RUN chown -R appuser:appuser /app

# 8. Ganti User
USER appuser

# 9. Expose Port
EXPOSE 8080

# 10. Perintah Eksekusi (CMD)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
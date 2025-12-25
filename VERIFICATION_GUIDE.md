# 🚀 Panduan Step-by-Step Verifikasi Lokal

Ikuti langkah-langkah di bawah untuk memverifikasi semua komponen berjalan dengan baik.

---

## Step 1: Verifikasi Environment

Buka PowerShell/Terminal di folder `midsem-aggregator` dan jalankan:

```powershell
# Cek Python version
python --version
# Expected: Python 3.11.x atau 3.12.x

# Cek virtual environment ada
Test-Path .\.venv
# Expected: True
```

---

## Step 2: Jalankan Unit Tests (7 Tests)

### Cara A: Run Semua Tests

```powershell
# Aktifkan virtual environment (opsional, tapi recommended)
.\.venv\Scripts\activate

# Jalankan pytest dengan verbose output
pytest tests/test_main.py -v

# Atau tanpa activate venv:
.\.venv\Scripts\python.exe -m pytest tests/test_main.py -v
```

**Expected Output:**
```
============================= test session starts =============================
collecting ... collected 7 items

tests/test_main.py::test_publish_and_deduplication PASSED               [ 14%]
tests/test_main.py::test_get_stats_endpoint PASSED                      [ 28%]
tests/test_main.py::test_get_events_by_topic PASSED                     [ 42%]
tests/test_main.py::test_schema_validation_error PASSED                 [ 57%]
tests/test_main.py::test_persistence_after_restart PASSED               [ 71%]
tests/test_main.py::test_batch_processing_performance PASSED            [ 85%]
tests/test_main.py::test_multiple_topics_isolation PASSED               [100%]

============================== 7 passed in X.XXs ==============================
```

### Cara B: Run Tests Satu per Satu (Untuk Debugging)

```powershell
# Test 1: Deduplication
pytest tests/test_main.py::test_publish_and_deduplication -v

# Test 2: Stats endpoint
pytest tests/test_main.py::test_get_stats_endpoint -v

# Test 3: Get events by topic
pytest tests/test_main.py::test_get_events_by_topic -v

# Test 4: Schema validation
pytest tests/test_main.py::test_schema_validation_error -v

# Test 5: Persistence after restart
pytest tests/test_main.py::test_persistence_after_restart -v

# Test 6: Batch processing performance
pytest tests/test_main.py::test_batch_processing_performance -v

# Test 7: Multiple topics isolation
pytest tests/test_main.py::test_multiple_topics_isolation -v
```

**✅ SUCCESS CRITERIA:** Semua 7 tests harus PASSED

---

## Step 3: Build Docker Image

```powershell
# Build Docker image
docker build -t uts-aggregator .

# Expected output (last lines):
# => exporting to image
# => naming to docker.io/library/uts-aggregator
```

**Troubleshooting:** Jika error "Cannot find the file specified", pastikan Docker Desktop sudah running.

### Verifikasi Image Berhasil

```powershell
# List Docker images
docker images | Select-String "uts-aggregator"

# Expected:
# uts-aggregator   latest   abc123def456   X minutes ago   XXX MB
```

---

## Step 4: Run Docker Container

### Terminal 1: Jalankan Container

```powershell
# Run container dengan volume untuk persistence
docker run --rm -p 8080:8080 -v ${PWD}/dedup_store.db:/app/dedup_store.db --name my-aggregator uts-aggregator
```

**Expected output:**
```
INFO:     Started server process [1]
INFO:     Waiting for application startup.
Database and table 'processed_ids' are ready at dedup_store.db.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
```

**✅ Jangan close terminal ini!** Server sedang running.

### Terminal 2: Test API

Buka PowerShell baru dan test API:

```powershell
# Test 1: GET /stats (server masih kosong)
curl http://localhost:8080/stats

# Expected response:
# {"received":0,"unique_processed":0,"duplicate_dropped":0,"topics":[],"uptime":"0:00:XX.XXXXXX"}

# Test 2: POST /publish (kirim event)
$event = @'
[
  {
    "topic": "test_logs",
    "event_id": "test-id-123",
    "source": "manual_test",
    "payload": {"message": "Hello from PowerShell"}
  }
]
'@

curl -Method POST -Uri http://localhost:8080/publish -Body $event -ContentType "application/json"

# Expected: {"status":"events processed"}

# Test 3: GET /stats lagi (sekarang ada 1 event)
curl http://localhost:8080/stats

# Expected: {"received":1,"unique_processed":1,"duplicate_dropped":0,"topics":["test_logs"],"uptime":"..."}

# Test 4: GET /events by topic
curl http://localhost:8080/events?topic=test_logs

# Expected: [{"topic":"test_logs","event_id":"test-id-123",...}]
```

### Test Deduplication (Kirim Event yang Sama Dua Kali)

```powershell
# Kirim event yang sama lagi
curl -Method POST -Uri http://localhost:8080/publish -Body $event -ContentType "application/json"

# Cek stats - seharusnya duplicate_dropped bertambah
curl http://localhost:8080/stats

# Expected: {"received":2,"unique_processed":1,"duplicate_dropped":1,...}
```

**✅ Cek Terminal 1:** Seharusnya ada log `[DUPLICATE] Event test_logs:test-id-123 already processed.`

### Stop Container

Di Terminal 1, tekan `Ctrl + C` untuk stop container.

---

## Step 5: Test Persistence (Restart Container)

```powershell
# Jalankan container lagi dengan command yang sama
docker run --rm -p 8080:8080 -v ${PWD}/dedup_store.db:/app/dedup_store.db --name my-aggregator uts-aggregator
```

Di Terminal 2, kirim event yang SAMA dengan sebelumnya:

```powershell
# Kirim event test-id-123 lagi
$event = @'
[
  {
    "topic": "test_logs",
    "event_id": "test-id-123",
    "source": "manual_test",
    "payload": {"message": "Hello from PowerShell"}
  }
]
'@

curl -Method POST -Uri http://localhost:8080/publish -Body $event -ContentType "application/json"

# Cek stats
curl http://localhost:8080/stats

# Expected: duplicate_dropped TETAP ADA (minimum 1)
# Ini membuktikan SQLite persistent store bekerja setelah restart!
```

**✅ SUCCESS:** Event `test-id-123` tetap dianggap duplikat meski container sudah di-restart.

Stop container lagi dengan `Ctrl + C`.

---

## Step 6: Run Docker Compose (Bonus)

```powershell
# Build dan run semua services
docker-compose up --build

# Expected output:
# aggregator_service | INFO: Uvicorn running on http://0.0.0.0:8080
# publisher_service  | --- Publisher started. Sending test events to http://aggregator:8080/publish ---
# publisher_service  | [SUCCESS] Sent 4 events. Server response:
# aggregator_service | [UNIQUE] Event logs:... processed successfully.
# aggregator_service | [UNIQUE] Event logs:... processed successfully.
# aggregator_service | [UNIQUE] Event metrics:... processed successfully.
# aggregator_service | [DUPLICATE] Event metrics:... already processed. Dropping.
# publisher_service exited with code 0
```

**✅ SUCCESS:** Publisher mengirim 4 events (3 unique, 1 duplicate), aggregator mendeteksi duplikat.

### Stop Docker Compose

```powershell
# Tekan Ctrl+C, lalu:
docker-compose down
```

---

## Step 7: Run Performance Test

### Terminal 1: Start Server

```powershell
# Option A: Docker
docker run --rm -p 8080:8080 -v ${PWD}/dedup_store.db:/app/dedup_store.db --name my-aggregator uts-aggregator

# Option B: Local (jika tidak pakai Docker)
.\.venv\Scripts\activate
uvicorn src.main:app --port 8080
```

### Terminal 2: Run Performance Test

```powershell
# Jalankan performance test (5000 events)
python performance_test.py
```

**Expected output:**
```
--- Performance Test Started ---
Total Events: 5000
Duplicate Percentage: 20.0%
Batch Size: 100

Generating 4000 unique IDs and 1000 duplicate IDs...
Total 5000 event payloads generated.
Sent 100/5000 events...
Sent 200/5000 events...
...
Sent 5000/5000 events...

--- Performance Test Finished ---
Total time taken: 4.23 seconds
Fetching stats from server to verify...
  Total Received: 5000
  Unique Processed: 4000
  Duplicates Dropped: 1000

[SUCCESS] Server stats match test parameters.
```

**✅ SUCCESS CRITERIA:**
- Total time < 10 seconds
- Received = 5000
- Unique Processed = 4000
- Duplicates Dropped = 1000

---

## Step 8: Verifikasi Semua File Ada

```powershell
# List semua file penting
ls src/main.py
ls tests/test_main.py
ls Dockerfile
ls docker-compose.yml
ls requirements.txt
ls README.md
ls report.md
ls publisher.py
ls performance_test.py
```

**Expected:** Semua file harus exist (tidak ada error "Cannot find path").

---

## 📋 Checklist Verifikasi

Tandai yang sudah Anda jalankan:

- [ ] ✅ Python version checked (3.11+ atau 3.12+)
- [ ] ✅ Virtual environment ada
- [ ] ✅ Pytest 7 tests PASSED
- [ ] ✅ Docker image built successfully
- [ ] ✅ Docker container running di port 8080
- [ ] ✅ API endpoints tested (POST /publish, GET /stats, GET /events)
- [ ] ✅ Deduplication bekerja (duplicate_dropped bertambah)
- [ ] ✅ Persistence tested (restart container, event tetap duplikat)
- [ ] ✅ Docker Compose tested (bonus)
- [ ] ✅ Performance test passed (5000 events, 4000 unique, 1000 dup)
- [ ] ✅ Semua file deliverables ada

---

## 🎥 Next Step: Video Demo

Setelah semua verifikasi di atas ✅, Anda siap untuk **merekam video demo**!

**Tools untuk Screen Recording:**
- **Windows Game Bar**: `Win + G` (built-in)
- **OBS Studio**: https://obsproject.com/ (free, recommended)
- **ShareX**: https://getsharex.com/ (free)

**Checklist untuk Video:**
1. Tunjukkan `docker build -t uts-aggregator .`
2. Tunjukkan `docker run --rm -p 8080:8080 ...`
3. Kirim event duplikat dengan `publisher.py` atau curl
4. Tunjukkan `curl http://localhost:8080/stats` sebelum & sesudah
5. Restart container dan kirim event sama → tunjukkan tetap duplikat
6. Jelaskan arsitektur singkat (30-60 detik)

**Upload ke YouTube:**
- Title: "UTS Sistem Terdistribusi - Pub-Sub Log Aggregator"
- Visibility: **Public**
- Link di README.md

---

## ❓ Troubleshooting

### Pytest Error: "No module named 'fastapi'"

```powershell
# Install dependencies
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### Docker Error: "Cannot connect to Docker daemon"

- Pastikan Docker Desktop sudah running
- Restart Docker Desktop
- Check: `docker version`

### Port 8080 Already in Use

```powershell
# Option 1: Cari process yang pakai port 8080
Get-NetTCPConnection -LocalPort 8080

# Option 2: Gunakan port lain
docker run --rm -p 8081:8080 ...
# Lalu akses http://localhost:8081
```

### SQLite Database Locked

```powershell
# Hapus database dan restart
rm dedup_store.db
# Test lagi dari awal
```

---

## 🎓 Summary

Semua komponen sudah berjalan dengan baik jika:
- ✅ 7 unit tests PASSED
- ✅ Docker container running dan API responsive
- ✅ Deduplication bekerja (duplikat terdeteksi)
- ✅ Persistence bekerja (restart container, SQLite tetap ada)
- ✅ Performance test passed (5000 events dalam < 10 detik)

**Yang tersisa:** Rekam video demo dan upload ke YouTube!

Good luck! 🚀

# UTS: Pub-Sub Log Aggregator

**Sistem Paralel dan Terdistribusi**

Implementasi layanan log aggregator dengan **Idempotent Consumer** dan **Deduplication** menggunakan FastAPI, SQLite, dan Docker.

---

## 🛠️ Teknologi

- **Python 3.11** + FastAPI (async)
- **SQLite** (persistent dedup store)
- **Docker** & Docker Compose
- **Pytest** (7 unit tests)

---

## 🚀 Cara Menjalankan

### Opsi 1: Docker Compose (Recommended)

```bash
# Build dan run aggregator + publisher
docker-compose up --build

# Stop
docker-compose down
```

### Opsi 2: Docker Manual

```bash
# Build image
docker build -t uts-aggregator .

# Run container (dengan persistent volume)
docker run --rm -p 8080:8080 -v ${PWD}/dedup_store.db:/app/dedup_store.db --name my-aggregator uts-aggregator
```

Server berjalan di: **http://localhost:8080**

---

## 📡 API Endpoints

### 1. POST /publish - Kirim Events

**Request** (array of events):
```bash
curl -X POST http://localhost:8080/publish \
-H "Content-Type: application/json" \
-d '[
  {
    "topic": "logs",
    "event_id": "unique-id-123",
    "source": "service-A",
    "payload": {"message": "Hello"}
  }
]'
```

**Response:**
```json
{"status": "events processed"}
```

### 2. GET /stats - Statistik

```bash
curl http://localhost:8080/stats
```

**Response:**
```json
{
  "received": 10,
  "unique_processed": 8,
  "duplicate_dropped": 2,
  "topics": ["logs", "metrics"],
  "uptime": "0:05:23.123456"
}
```

### 3. GET /events?topic={topic} - Query Events

```bash
curl http://localhost:8080/events?topic=logs
```

**Response:** Array of events untuk topic tersebut.

---

## 🧪 Testing

### Unit Tests (7 tests)

```bash
# Run semua tests
pytest -v

# Atau dengan python
python -m pytest tests/test_main.py -v
```

**Coverage:**
- Deduplication logic
- Persistent dedup store (restart-safe)
- API validation (Pydantic)
- Batch processing (500 events)
- Multi-topic isolation

### Performance Test

```bash
# Pastikan server running di localhost:8080
python performance_test.py
```

Test 5000 events (4000 unique, 1000 duplicate) dalam ~4 detik.

### Publisher Script

```bash
# Kirim sample events dengan duplikat
python publisher.py
```

---

## 📁 Struktur Project

```
midsem-aggregator/
├── src/
│   └── main.py                 # FastAPI application
├── tests/
│   └── test_main.py            # 7 unit tests
├── docs/
│   └── buku-utama.pdf.pdf      # Referensi teori
├── Dockerfile                  # Container definition
├── docker-compose.yml          # Multi-service orchestration
├── requirements.txt            # Dependencies
├── publisher.py                # Client demo script
├── performance_test.py         # Performance validation
├── report.md                   # Laporan teori lengkap (T1-T8)
├── VERIFICATION_GUIDE.md       # Panduan step-by-step
└── README.md                   # This file
```

---

## 📐 Keputusan Desain (Bab 1-7)

- **Idempotency (Bab 3):** Composite key `topic:event_id` untuk uniqueness
- **Naming (Bab 4):** UUID v4 untuk collision resistance
- **Fault Tolerance (Bab 6):** SQLite persistent store (restart-safe)
- **Consistency (Bab 7):** Eventual consistency dengan deduplication

Detail lengkap: Lihat **[report.md](./report.md)**

---

## 🎥 Video Demo

**Link YouTube:** [PLACEHOLDER - Update setelah upload video demo]
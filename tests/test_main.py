import pytest
from fastapi.testclient import TestClient
import os
import time
import datetime # <- Tambahkan ini

# Impor 'app' dan variabel state kita
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.main import app, stats, processed_events # <- Tambahkan stats & processed_events

# --- Konfigurasi Test ---

DATABASE_URL = "test_dedup_store.db"
# Arahkan aplikasi kita untuk menggunakan database TEST, bukan yang asli
app.DATABASE_URL = DATABASE_URL 

# Pytest fixture ini akan dijalankan SEBELUM setiap fungsi test
@pytest.fixture(autouse=True)
def setup_teardown():
    # SETUP: Hapus file database tes lama (jika ada) agar setiap tes bersih
    if os.path.exists(DATABASE_URL):
        os.remove(DATABASE_URL)
    
    # ==== PERBAIKAN STATE POLLUTION ====
    # Reset variabel in-memory ke kondisi awal sebelum setiap tes
    stats.clear()
    stats.update({
        "received": 0,
        "unique_processed": 0,
        "duplicate_dropped": 0,
        "topics": [],
        "uptime": str(datetime.timedelta(seconds=0))
    })
    processed_events.clear()
    # ==== AKHIR PERBAIKAN ====

    # Menjalankan startup event (lifespan) secara manual 
    with TestClient(app) as client:
        pass # TestClient otomatis memanggil event 'lifespan' startup

    yield # --- Di sinilah tes Anda akan berjalan ---

    # TEARDOWN: Hapus file database tes setelah tes selesai
    if os.path.exists(DATABASE_URL):
        os.remove(DATABASE_URL)

# --- Test Suite ---

def test_publish_and_deduplication():
    client = TestClient(app)
    
    static_event_id = "test-static-id-123"
    
    events_batch = [
        {"topic": "test_logs", "event_id": "test-id-1", "source": "tester", "payload": {}},
        {"topic": "test_logs", "event_id": "test-id-2", "source": "tester", "payload": {}},
        {"topic": "test_metrics", "event_id": static_event_id, "source": "tester", "payload": {}},
        {"topic": "test_metrics", "event_id": static_event_id, "source": "tester", "payload": {}}, # Duplikat
    ]

    # Kirim 4 event (3 unik, 1 duplikat)
    response = client.post("/publish", json=events_batch)
    assert response.status_code == 200
    assert response.json() == {"status": "events processed"}

    # Cek statistik setelah pengiriman
    stats = client.get("/stats").json()
    assert stats["received"] == 4
    assert stats["unique_processed"] == 3
    assert stats["duplicate_dropped"] == 1

def test_get_stats_endpoint():
    client = TestClient(app)
    
    # Cek statistik awal (sekarang PASTI 0)
    stats = client.get("/stats").json()
    assert stats["received"] == 0
    assert stats["unique_processed"] == 0
    assert stats["duplicate_dropped"] == 0
    assert stats["topics"] == []

def test_get_events_by_topic():
    client = TestClient(app)

    event_a = {"topic": "topic-A", "event_id": "a1", "source": "tester", "payload": {}}
    event_b = {"topic": "topic-B", "event_id": "b1", "source": "tester", "payload": {}}

    # Kirim dua event dengan topic berbeda
    client.post("/publish", json=[event_a, event_b])

    # Tes ambil topic A
    response_a = client.get("/events?topic=topic-A")
    assert response_a.status_code == 200
    data_a = response_a.json()
    assert len(data_a) == 1
    assert data_a[0]["event_id"] == "a1"

    # Tes ambil topic B
    response_b = client.get("/events?topic=topic-B")
    assert response_b.status_code == 200
    data_b = response_b.json()
    assert len(data_b) == 1
    assert data_b[0]["event_id"] == "b1"

    # Tes ambil topic yang tidak ada
    response_c = client.get("/events?topic=topic-C")
    assert response_c.status_code == 200
    assert response_c.json() == []

def test_schema_validation_error():
    client = TestClient(app)
    
    # Kirim event dengan format salah (misal: 'topic' hilang)
    bad_event = [
        {"event_id": "bad-id", "source": "tester", "payload": {}}
    ]
    
    response = client.post("/publish", json=bad_event)
    # FastAPI harus menolaknya dengan status 422 (Unprocessable Entity)
    assert response.status_code == 422
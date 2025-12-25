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


def test_persistence_after_restart():
    """
    Test 5: Persistensi dedup store setelah restart
    Memastikan bahwa event yang sudah diproses tetap dianggap duplikat
    setelah restart (simulasi dengan reset in-memory tapi database tetap ada)
    """
    client = TestClient(app)
    
    event_persistent = {
        "topic": "persistent_test",
        "event_id": "persistent-id-999",
        "source": "tester",
        "payload": {"data": "important"}
    }
    
    # Kirim event pertama kali
    response1 = client.post("/publish", json=[event_persistent])
    assert response1.status_code == 200
    
    # Verifikasi event diproses
    stats1 = client.get("/stats").json()
    assert stats1["unique_processed"] == 1
    assert stats1["duplicate_dropped"] == 0
    
    # Simulasi restart: Hapus in-memory store tapi SQLite tetap ada
    # (dalam test, kita tidak perlu restart container, cukup clear in-memory)
    # Catatan: SQLite DB tidak direset karena setup_teardown hanya clear di awal test
    processed_events.clear()
    
    # Kirim event yang SAMA lagi setelah "restart"
    response2 = client.post("/publish", json=[event_persistent])
    assert response2.status_code == 200
    
    # Verifikasi event dianggap DUPLIKAT (tidak diproses ulang)
    stats2 = client.get("/stats").json()
    assert stats2["unique_processed"] == 1  # Masih 1, tidak bertambah
    assert stats2["duplicate_dropped"] == 1  # Duplikat terdeteksi
    
    # In-memory store kosong (karena di-clear), tapi dedup tetap bekerja
    events = client.get("/events?topic=persistent_test").json()
    assert len(events) == 0  # In-memory di-clear
    # Tapi SQLite masih punya record event_id ini


def test_batch_processing_performance():
    """
    Test 6: Stress test kecil dengan batch processing
    Mengirim 500 events dalam satu batch dan mengukur bahwa
    semua terproses dengan benar dalam waktu yang wajar
    """
    client = TestClient(app)
    
    batch_size = 500
    events_batch = []
    
    for i in range(batch_size):
        events_batch.append({
            "topic": "batch_test",
            "event_id": f"batch-id-{i}",
            "source": "batch_tester",
            "payload": {"index": i}
        })
    
    # Ukur waktu eksekusi
    start_time = time.time()
    response = client.post("/publish", json=events_batch)
    elapsed_time = time.time() - start_time
    
    assert response.status_code == 200
    
    # Verifikasi semua events diproses
    stats = client.get("/stats").json()
    assert stats["received"] == batch_size
    assert stats["unique_processed"] == batch_size
    assert stats["duplicate_dropped"] == 0
    
    # Assert waktu eksekusi dalam batas wajar (< 5 detik untuk 500 events)
    assert elapsed_time < 5.0, f"Batch processing took too long: {elapsed_time:.2f}s"
    
    # Verifikasi semua events ada di in-memory store
    events = client.get("/events?topic=batch_test").json()
    assert len(events) == batch_size


def test_multiple_topics_isolation():
    """
    Test 7: Memastikan composite key (topic:event_id) bekerja dengan benar
    Event dengan event_id sama tapi topic berbeda harus dianggap UNIK
    """
    client = TestClient(app)
    
    same_event_id = "shared-id-123"
    
    event_topic_a = {
        "topic": "topic-A",
        "event_id": same_event_id,
        "source": "tester",
        "payload": {"msg": "from topic A"}
    }
    
    event_topic_b = {
        "topic": "topic-B",
        "event_id": same_event_id,  # Event_id SAMA
        "source": "tester",
        "payload": {"msg": "from topic B"}
    }
    
    # Kirim kedua events
    response = client.post("/publish", json=[event_topic_a, event_topic_b])
    assert response.status_code == 200
    
    # Verifikasi KEDUANYA diproses (tidak dianggap duplikat)
    stats = client.get("/stats").json()
    assert stats["received"] == 2
    assert stats["unique_processed"] == 2  # Keduanya unik
    assert stats["duplicate_dropped"] == 0  # Tidak ada duplikat
    
    # Verifikasi masing-masing topic ada event-nya
    events_a = client.get("/events?topic=topic-A").json()
    assert len(events_a) == 1
    assert events_a[0]["event_id"] == same_event_id
    
    events_b = client.get("/events?topic=topic-B").json()
    assert len(events_b) == 1
    assert events_b[0]["event_id"] == same_event_id
    
    # Kirim duplikat untuk topic-A (seharusnya ditolak)
    response2 = client.post("/publish", json=[event_topic_a])
    assert response2.status_code == 200
    
    stats2 = client.get("/stats").json()
    assert stats2["unique_processed"] == 2  # Masih 2
    assert stats2["duplicate_dropped"] == 1  # Duplikat terdeteksi
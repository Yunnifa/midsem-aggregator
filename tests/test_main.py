import pytest
import os
import time
import re
from fastapi.testclient import TestClient

# --- KONFIGURASI TEST ---
DATABASE_URL = "test_dedup_store.db"
os.environ["DATABASE_URL"] = DATABASE_URL

from main import app, stats, processed_events_cache

@pytest.fixture
def client():
    """Fixture untuk menyediakan TestClient dan mereset state setiap kali test."""
    if os.path.exists(DATABASE_URL):
        try:
            os.remove(DATABASE_URL)
        except PermissionError:
            pass

    stats.clear()
    stats.update({
        "received": 0,
        "unique_processed": 0,
        "duplicate_dropped": 0,
        "topics": set(),
        "uptime": ""
    })
    processed_events_cache.clear()

    with TestClient(app) as c:
        yield c

    if os.path.exists(DATABASE_URL):
        try:
            os.remove(DATABASE_URL)
        except PermissionError:
            pass

# --- TEST SUITE (TOTAL 10 EVENTS) ---

# 1. Test Inisialisasi
def test_stats_initial_state(client):
    """Menjamin statistik awal selalu nol."""
    response = client.get("/stats")
    data = response.json()
    assert data["received"] == 0
    assert data["unique_processed"] == 0

# 2. Test Publishing & Deduplication
def test_publish_and_deduplication(client):
    """Menguji batch publishing dan fitur deduplikasi."""
    payload = [
        {"topic": "T1", "event_id": "A", "source": "test", "payload": {}},
        {"topic": "T1", "event_id": "A", "source": "test", "payload": {}}, # Duplikat
    ]
    client.post("/publish", json=payload)
    res = client.get("/stats").json()
    assert res["received"] == 2
    assert res["unique_processed"] == 1
    assert res["duplicate_dropped"] == 1

# 3. Test Filter Topik
def test_get_events_by_topic(client):
    """Menguji filter data berdasarkan topik."""
    client.post("/publish", json=[{"topic": "sensor", "event_id": "s1", "source": "test", "payload": {}}])
    response = client.get("/events?topic=sensor")
    assert response.status_code == 200
    assert len(response.json()) == 1

# 4. Test Error Validasi
def test_schema_validation_error(client):
    """Memastikan error 422 jika field 'topic' tidak ada."""
    response = client.post("/publish", json=[{"event_id": "id1", "source": "test", "payload": {}}])
    assert response.status_code == 422

# 5. Test Persistensi Database
def test_persistence_after_restart(client):
    """Menguji apakah data tetap ada di SQLite meski cache RAM dihapus."""
    event = {"topic": "db", "event_id": "p1", "source": "test", "payload": {}}
    client.post("/publish", json=[event])
    processed_events_cache.clear() # Hapus cache RAM
    client.post("/publish", json=[event]) # Kirim lagi
    res = client.get("/stats").json()
    assert res["duplicate_dropped"] == 1

# 6. Test Isolasi Topik
def test_multiple_topics_isolation(client):
    """Event ID yang sama di topik berbeda harus dianggap unik."""
    payload = [
        {"topic": "App-A", "event_id": "id-1", "source": "test", "payload": {}},
        {"topic": "App-B", "event_id": "id-1", "source": "test", "payload": {}}
    ]
    client.post("/publish", json=payload)
    res = client.get("/stats").json()
    assert res["unique_processed"] == 2

# 7. Test Payload Kosong
def test_empty_batch_publish(client):
    """Memastikan sistem tidak crash jika dikirim list kosong []."""
    response = client.post("/publish", json=[])
    assert response.status_code == 200
    assert "Tidak ada event" in response.json()["message"]

# 8. Test Format Uptime
def test_uptime_format(client):
    """Memastikan format uptime adalah HH:MM:SS."""
    response = client.get("/stats")
    uptime_str = response.json()["uptime"]
    # Regex untuk format 00:00:00
    assert re.match(r"^\d+:\d{2}:\d{2}$", uptime_str)

# 9. Test Integritas Data
def test_event_retrieval_integrity(client):
    """Memastikan data payload yang disimpan tidak berubah."""
    original_payload = {"temp": 25.5, "status": "ok"}
    event = {"topic": "check", "event_id": "c1", "source": "test", "payload": original_payload}
    client.post("/publish", json=[event])
    
    response = client.get("/events?topic=check")
    retrieved_event = response.json()[0]
    assert retrieved_event["payload"] == original_payload

# 10. Test Performa Batch
def test_batch_processing_performance(client):
    """Menguji kecepatan proses 500 data (Target: < 5 detik)."""
    batch_size = 500
    events = [{"topic": "perf", "event_id": f"id-{i}", "source": "test", "payload": {}} for i in range(batch_size)]
    
    start = time.perf_counter()
    response = client.post("/publish", json=events)
    duration = time.perf_counter() - start
    
    assert response.status_code == 200
    assert duration < 5.0
import aiosqlite
import datetime
import uuid
import os
from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List, Dict
from contextlib import asynccontextmanager

# --- Model Data ---
class Event(BaseModel):
    topic: str
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.now)
    source: str
    payload: Dict

# --- Statistik Sistem ---
stats = {
    "received": 0,
    "unique_processed": 0,
    "duplicate_dropped": 0,
    "topics": set(),
    "uptime": ""
}
start_time = datetime.datetime.now()
# Penyimpanan sementara untuk list event unik per topik
processed_events_cache: Dict[str, List[Event]] = {}

# --- Lifespan Handler (Startup & Shutdown) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inisialisasi Database
    db_path = os.getenv("DATABASE_URL", "dedup_store.db")
    app.state.db = await aiosqlite.connect(db_path)
    
    # Buat tabel jika belum ada
    await app.state.db.execute("""
        CREATE TABLE IF NOT EXISTS processed_ids (
            id TEXT PRIMARY KEY
        )
    """)
    await app.state.db.commit()
    print(f"Sistem siap. Database: {db_path}")
    
    yield # Aplikasi berjalan
    
    # Menutup koneksi saat aplikasi mati
    await app.state.db.close()
    print("Sistem dimatikan.")

app = FastAPI(title="UTS Log Aggregator", lifespan=lifespan)

# --- Endpoint API ---

@app.post("/publish")
async def publish_event(events: List[Event]):
    if not events:
        return {"message": "Tidak ada event untuk diproses"}

    # 1. Kumpulkan ID unik dari batch ini
    incoming_pairs = []
    for e in events:
        stats["received"] += 1
        unique_id = f"{e.topic}:{e.event_id}"
        incoming_pairs.append((unique_id, e))

    # 2. Bulk Check: Cek ID mana saja yang sudah ada di DB dalam satu query
    placeholders = ",".join(["?"] * len(incoming_pairs))
    ids_to_check = [p[0] for p in incoming_pairs]
    
    query = f"SELECT id FROM processed_ids WHERE id IN ({placeholders})"
    async with app.state.db.execute(query, ids_to_check) as cursor:
        rows = await cursor.fetchall()
        existing_ids = {row[0] for row in rows}

    # 3. Filter data yang benar-benar baru
    new_ids_for_db = []
    unique_events_to_cache = []
    
    # Set internal untuk menangani duplikat di dalam batch yang sama (internal batch dedup)
    seen_in_current_batch = set()

    for unique_id, event_obj in incoming_pairs:
        if unique_id not in existing_ids and unique_id not in seen_in_current_batch:
            new_ids_for_db.append((unique_id,))
            unique_events_to_cache.append(event_obj)
            seen_in_current_batch.add(unique_id)
        else:
            stats["duplicate_dropped"] += 1

    # 4. Bulk Insert & Commit SEKALI SAJA (Optimasi Performa Utama)
    if new_ids_for_db:
        await app.state.db.executemany(
            "INSERT INTO processed_ids (id) VALUES (?)", 
            new_ids_for_db
        )
        await app.state.db.commit()

        # Update Cache dan Stats
        for event in unique_events_to_cache:
            stats["unique_processed"] += 1
            stats["topics"].add(event.topic)
            
            if event.topic not in processed_events_cache:
                processed_events_cache[event.topic] = []
            processed_events_cache[event.topic].append(event)

    return {"message": f"{len(events)} event telah diproses"}

@app.get("/events")
async def get_events(topic: str):
    return processed_events_cache.get(topic, [])

@app.get("/stats")
async def get_stats():
    uptime = datetime.datetime.now() - start_time
    return {
        "received": stats["received"],
        "unique_processed": stats["unique_processed"],
        "duplicate_dropped": stats["duplicate_dropped"],
        "topics": list(stats["topics"]),
        "uptime": str(uptime).split(".")[0] # Format HH:MM:SS
    }
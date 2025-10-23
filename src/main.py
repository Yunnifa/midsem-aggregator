import aiosqlite
import datetime
import uuid
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict
from contextlib import asynccontextmanager # <- Tambahkan ini

# --- 1. Model Data (Validasi Skema) ---
class Event(BaseModel):
    topic: str
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.now)
    source: str
    payload: Dict

# --- 2. Penyimpanan Data & Statistik ---
# Variabel global ini akan direset oleh pytest
processed_events: Dict[str, List[Event]] = {}
stats = {
    "received": 0,
    "unique_processed": 0,
    "duplicate_dropped": 0,
    "topics": [],
    "uptime": str(datetime.timedelta(seconds=0))
}
start_time = datetime.datetime.now()

# --- 3. Event Handler (Lifespan) ---
# Ini adalah cara baru (pengganti @app.on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Kode ini berjalan SAAT STARTUP
    # Kita gunakan app.DATABASE_URL agar bisa diganti oleh tes
    async with aiosqlite.connect(app.DATABASE_URL) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS processed_ids (
                id TEXT PRIMARY KEY
            )
        """)
        await db.commit()
    print(f"Database and table 'processed_ids' are ready at {app.DATABASE_URL}.")
    
    yield # Aplikasi berjalan di sini
    
    # Kode ini berjalan SAAT SHUTDOWN (jika perlu)
    print("Application shutting down.")

# --- 4. Inisialisasi Aplikasi ---
app = FastAPI(
    title="UTS Log Aggregator",
    description="Layanan aggregator untuk deduplikasi log (UTS SisParTer).",
    version="1.0.0",
    lifespan=lifespan # <- Hubungkan lifespan handler ke aplikasi
)

# Tentukan database default, tapi simpan di 'app'
# agar bisa di-override oleh tes
app.DATABASE_URL = "dedup_store.db"


# --- 5. Endpoint API ---

@app.post("/publish")
async def publish_event(events: List[Event]):
    
    # Gunakan DATABASE_URL dari aplikasi
    async with aiosqlite.connect(app.DATABASE_URL) as db:
        
        for event in events:
            stats["received"] += 1
            unique_id = f"{event.topic}:{event.event_id}"

            try:
                await db.execute(
                    "INSERT OR IGNORE INTO processed_ids (id) VALUES (?)", 
                    (unique_id,)
                )
                await db.commit()

                cursor = await db.execute("SELECT changes()")
                changes = await cursor.fetchone()
                
                if changes[0] == 0:
                    stats["duplicate_dropped"] += 1
                    print(f"[DUPLICATE] Event {unique_id} already processed. Dropping.")
                
                else:
                    stats["unique_processed"] += 1
                    
                    if event.topic not in processed_events:
                        processed_events[event.topic] = []
                    processed_events[event.topic].append(event)
                    print(f"[UNIQUE] Event {unique_id} processed successfully.")

            except aiosqlite.Error as e:
                print(f"An error occurred with event {unique_id}: {e}")
        
    return {"status": "events processed"}


@app.get("/events")
async def get_events(topic: str):
    return processed_events.get(topic, [])

@app.get("/stats")
async def get_stats():
    uptime_duration = datetime.datetime.now() - start_time
    stats["uptime"] = str(uptime_duration)
    stats["topics"] = list(processed_events.keys())
    return stats
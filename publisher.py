import httpx
import asyncio
import uuid
import random
import os  # <-- TAMBAHAN 1

# URL tempat server aggregator kita berjalan
# --- PERUBAHAN DI BAWAH INI ---
# Baca API_URL dari environment variable, default ke localhost jika tidak ada
API_URL = os.getenv("API_URL", "http://127.0.0.1:8080/publish")

async def send_events():
    # --- PERUBAHAN DI BAWAH INI ---
    # Tampilkan URL yang sedang dituju
    print(f"--- Publisher started. Sending test events to {API_URL} ---")
    
    # Kita akan buat 1 event duplikat secara manual
    duplicate_event_id = str(uuid.uuid4())
    
    events_batch = [
        # --- Event Unik ---
        {
            "topic": "logs", 
            "event_id": str(uuid.uuid4()), 
            "source": "service-A", 
            "payload": {"level": "info", "msg": "User logged in"}
        },
        {
            "topic": "logs", 
            "event_id": str(uuid.uuid4()), 
            "source": "service-B", 
            "payload": {"level": "warn", "msg": "DB connection slow"}
        },
        
        # --- Event Duplikat (event_id sama) ---
        {
            "topic": "metrics", 
            "event_id": duplicate_event_id, 
            "source": "service-A", 
            "payload": {"cpu": 0.5, "mem": 0.2}
        },
        {
            "topic": "metrics", 
            "event_id": duplicate_event_id, 
            "source": "service-A", 
            "payload": {"cpu": 0.5, "mem": 0.2} # Konten sama persis
        },
    ]

    # Kita gunakan httpx untuk mengirim request
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(API_URL, json=events_batch, timeout=10.0)
            
            if response.status_code == 200:
                print(f"\n[SUCCESS] Sent {len(events_batch)} events. Server response:")
                print(response.json())
            else:
                print(f"\n[ERROR] Server returned status code: {response.status_code}")
                print(response.text)

        except httpx.ConnectError as e:
            print(f"\n[FATAL ERROR] Cannot connect to server at {API_URL}.")
            print("Pastikan server aggregator (uvicorn) Anda sedang berjalan.")
        except Exception as e:
            print(f"\nAn unexpected error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(send_events())
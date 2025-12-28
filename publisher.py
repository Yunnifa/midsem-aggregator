import httpx
import asyncio
import uuid
import random
import os
import time

# Membaca URL dari environment variable (penting untuk Docker Compose)
API_URL = os.getenv("API_URL", "http://127.0.0.1:8080/publish")

async def run_stress_test():
    total_events = 5000
    duplicate_rate = 0.20  # 20% duplikasi
    batch_size = 100       # Dikirim per 100 event agar tidak berat
    
    # 1. Siapkan kumpulan ID unik (80% dari total)
    unique_count = int(total_events * (1 - duplicate_rate))
    id_pool = [str(uuid.uuid4()) for _ in range(unique_count)]
    
    print(f"Menyiapkan {total_events} event dengan target {int(duplicate_rate*100)}% duplikasi...")
    
    async with httpx.AsyncClient() as client:
        start_time = time.time()
        
        for i in range(0, total_events, batch_size):
            batch = []
            for _ in range(batch_size):
                # Pilih ID secara acak dari pool untuk menciptakan duplikasi
                chosen_id = random.choice(id_pool)
                batch.append({
                    "topic": random.choice(["logs", "metrics", "security"]),
                    "event_id": chosen_id,
                    "source": f"service-{random.randint(1, 5)}",
                    "payload": {"level": "info", "data": random.random()}
                })
            
            try:
                await client.post(API_URL, json=batch, timeout=10.0)
                print(f"Terkirim: {i + batch_size}/{total_events} event...", end="\r")
            except Exception as e:
                print(f"\n[ERROR] Gagal mengirim batch: {e}")
                break
        
        duration = time.time() - start_time
        print(f"\nSelesai! Pengiriman {total_events} event memakan waktu {duration:.2f} detik.")

if __name__ == "__main__":
    asyncio.run(run_stress_test())
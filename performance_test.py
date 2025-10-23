import httpx
import asyncio
import uuid
import time
import random

API_URL = "http://127.0.0.1:8080/publish"
TOTAL_EVENTS = 5000
DUPLICATE_PERCENTAGE = 0.2 # 20%
BATCH_SIZE = 100 # Kirim 100 event per request

async def run_performance_test():
    print("--- Performance Test Started ---")
    print(f"Total Events: {TOTAL_EVENTS}")
    print(f"Duplicate Percentage: {DUPLICATE_PERCENTAGE * 100}%")
    print(f"Batch Size: {BATCH_SIZE}\n")

    # --- 1. Buat Daftar Event ID ---
    
    num_duplicates = int(TOTAL_EVENTS * DUPLICATE_PERCENTAGE) # 1000
    num_uniques = TOTAL_EVENTS - num_duplicates             # 4000
    
    print(f"Generating {num_uniques} unique IDs and {num_duplicates} duplicate IDs...")

    unique_ids = [str(uuid.uuid4()) for _ in range(num_uniques)]
    duplicate_ids = [random.choice(unique_ids) for _ in range(num_duplicates)]
    
    all_event_ids = unique_ids + duplicate_ids
    random.shuffle(all_event_ids) 

    print(f"Total {len(all_event_ids)} event payloads generated.")

    # --- 2. Kirim Event dalam Batch ---
    
    start_time = time.time()
    total_sent = 0
    
    # Atur timeout default untuk client
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i in range(0, TOTAL_EVENTS, BATCH_SIZE):
            batch_ids = all_event_ids[i:i + BATCH_SIZE]
            events_batch = []
            
            for event_id in batch_ids:
                events_batch.append({
                    "topic": "performance_logs",
                    "event_id": event_id,
                    "source": "perf_tester",
                    "payload": {"n": i, "id": event_id}
                })
            
            try:
                response = await client.post(API_URL, json=events_batch)
                if response.status_code != 200:
                    print(f"ERROR sending batch {i}: {response.status_code}")
                
                total_sent += len(events_batch)
                print(f"Sent {total_sent}/{TOTAL_EVENTS} events...")

            except httpx.ReadTimeout:
                print(f"ERROR: ReadTimeout on batch {i}. Server mungkin kewalahan.")
            except Exception as e:
                print(f"ERROR: {e}")

        end_time = time.time()
        
        print("\n--- Performance Test Finished ---")
        print(f"Total time taken: {end_time - start_time:.2f} seconds")

        # --- 3. Verifikasi Statistik dari Server ---
        # ==== PERBAIKAN: Blok ini dipindahkan ke DALAM 'async with' ====
        try:
            print("Fetching stats from server to verify...")
            # Ambil stats SEBELUM client ditutup
            stats_response = await client.get("http://127.0.0.1:8080/stats")
            stats = stats_response.json()
            
            print(f"  Total Received: {stats.get('received')}")
            print(f"  Unique Processed: {stats.get('unique_processed')}")
            print(f"  Duplicates Dropped: {stats.get('duplicate_dropped')}")
            
            # Verifikasi (gunakan >= jika DB tidak direset)
            assert stats.get('received') >= TOTAL_EVENTS
            assert stats.get('unique_processed') >= num_uniques
            assert stats.get('duplicate_dropped') >= num_duplicates
            
            print("\n[SUCCESS] Server stats match test parameters.")
            
        except Exception as e:
            print(f"\n[ERROR] Could not verify stats from server: {e}")
        # ==== AKHIR PERBAIKAN ====


if __name__ == "__main__":
    print("PERINGATAN: Pastikan Anda menjalankan ini di server yang bersih/baru")
    print("atau statistik akan terakumulasi dari run sebelumnya.")
    print("Menunggu 3 detik... (Tekan Ctrl+C untuk batal)")
    time.sleep(3)
    asyncio.run(run_performance_test())
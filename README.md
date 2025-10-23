# UTS Pub-Sub Log Aggregator

Proyek ini adalah implementasi layanan log aggregator untuk Ujian Tengah Semester (UTS) Sistem Paralel dan Terdistribusi.

Layanan ini dirancang untuk menerima *event* atau *log* dari berbagai sumber (*publisher*), melakukan deduplikasi (menjamin *idempotency*), dan menyimpan *event* yang unik secara persisten.

## Fitur Utama

* API berbasis **FastAPI** untuk menerima *event*.
* Logika **Deduplikasi** menggunakan (topic, event\_id) sebagai kunci unik.
* Penyimpanan **Persisten** menggunakan **SQLite** (`aiosqlite`).
* **Kontainerisasi** penuh menggunakan **Docker**.
* **Unit Test** menggunakan **Pytest** untuk memvalidasi fungsionalitas inti.
* **Uji Performa** untuk memvalidasi pemrosesan 5.000+ *event*.
* **Bonus**: Orkestrasi layanan menggunakan **Docker Compose**.

## Teknologi yang Digunakan

* Python 3.11
* FastAPI
* Uvicorn
* Aiosqlite
* Pytest
* Httpx
* Docker & Docker Compose

---

## Cara Menjalankan Proyek

Anda bisa menjalankan proyek ini dengan 3 cara. Cara yang direkomendasikan adalah Opsi 1 (Docker) atau Opsi 2 (Docker Compose).

### Prasyarat

* **Docker Desktop** (harus sudah terinstal dan berjalan).
* **Python 3.8+** (hanya diperlukan untuk Opsi 3).

### Opsi 1: Menjalankan dengan Docker (Wajib)

Ini adalah cara standar untuk menjalankan layanan *aggregator* sesuai spesifikasi tugas.

1.  **Build Docker Image:**
    Buka terminal di folder proyek dan jalankan:
    ```bash
    docker build -t uts-aggregator .
    ```

2.  **Jalankan Docker Container:**
    Setelah *image* selesai di-build, jalankan *container* dengan perintah berikut:
    ```bash
    docker run --rm -p 8080:8080 -v ./dedup_store.db:/app/dedup_store.db --name my-aggregator uts-aggregator
    ```

**Penjelasan Perintah:**
* `--rm`: Otomatis menghapus *container* saat dihentikan.
* `-p 8080:8080`: Memetakan port 8080 di komputer Anda ke port 8080 di dalam *container*.
* `-v ./dedup_store.db:/app/dedup_store.db`: Ini adalah **Docker Volume**. Ini "menyambungkan" file `dedup_store.db` di folder lokal Anda ke file `/app/dedup_store.db` di dalam *container*. Ini yang membuat *database* Anda **persisten** (tidak hilang saat *container* di-restart).

Server aggregator sekarang berjalan di `http://127.0.0.1:8080`.

### Opsi 2: Menjalankan dengan Docker Compose (Bonus)

Ini adalah cara yang lebih mudah untuk menjalankan layanan *aggregator* dan *publisher* secara bersamaan (sesuai bagian bonus).

1.  **Build dan Jalankan Semua Layanan:**
    Cukup jalankan satu perintah:
    ```bash
    docker-compose up --build
    ```
    Perintah ini akan otomatis:
    * Membangun *image* Docker.
    * Menjalankan layanan `aggregator` (server).
    * Menjalankan layanan `publisher` (skrip klien), yang akan menunggu 5 detik lalu mengirim *event* ke `aggregator`.

2.  **Untuk Berhenti:**
    Tekan `Ctrl + C` di terminal, lalu jalankan:
    ```bash
    docker-compose down
    ```

### Opsi 3: Menjalankan di Lokal (Untuk Development)

Ini adalah cara menjalankan server di komputer lokal Anda tanpa Docker, biasanya digunakan untuk *coding* dan *debugging* cepat.

1.  **Buat dan Aktifkan Virtual Environment:**
    ```bash
    python -m venv .venv
    .\.venv\Scripts\activate
    ```

2.  **Instal Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Jalankan Server FastAPI:**
    ```bash
    uvicorn src.main:app --reload --port 8080
    ```
    Server akan berjalan di `http://127.0.0.1:8080`.

---

## Cara Menjalankan Tes

Proyek ini dilengkapi dengan 4 *unit test* untuk memvalidasi logika inti.

1.  **Aktifkan Virtual Environment:**
    ```bash
    .\.venv\Scripts\activate
    ```
2.  **Jalankan Pytest:**
    ```bash
    pytest
    ```
    Anda akan melihat hasil `4 passed` jika semua tes berhasil.

---

## Endpoint API

Server menyediakan 3 *endpoint* utama:

* **`POST /publish`**
    Menerima satu atau *batch* *event* dalam format JSON untuk diproses.

* **`GET /events`**
    Mengambil daftar *event* unik yang telah berhasil diproses.
    * Query Param: `topic` (contoh: `GET /events?topic=logs`)

* **`GET /stats`**
    Menampilkan statistik operasional server, termasuk:
    * `received`: Total *event* yang diterima.
    * `unique_processed`: Jumlah *event* unik yang disimpan.
    * `duplicate_dropped`: Jumlah duplikat yang ditolak.
    * `topics`: Daftar *topic* yang telah diproses.
    * `uptime`: Waktu server berjalan.

---

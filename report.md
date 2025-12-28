# Soal Teori UTS: Pub-Sub Log Aggregator
**Sistem Paralel dan Terdistribusi**

REPORT UTS SISTEM TERDISTRIBUSI
Pub-Sub Log Aggregator dengan Idempotent Consumer dan Deduplication

Nama: Yunnifa Nur Lailli
Mata Kuliah: Sistem Terdistribusi
Jenis Tugas: UTS Take-Home (Individu)
Bahasa Implementasi: Python
Buku Utama: Tanenbaum & Van Steen – Distributed Systems (Bab 1–7)

T1 — Karakteristik Sistem Terdistribusi dan Trade-off Desain

(Bab 1 – Introduction)

Soal:
Jelaskan karakteristik utama sistem terdistribusi dan trade-off yang umum pada desain Pub-Sub log aggregator.

Jawaban:
Sistem terdistribusi merupakan sistem yang tersusun dari beberapa komputer yang saling terhubung melalui jaringan dan bekerja bersama seolah-olah sebagai satu sistem terpadu. Walaupun dari sisi pengguna sistem tampak sederhana, pada kenyataannya setiap komputer bekerja secara independen dan hanya dapat berkomunikasi melalui pertukaran pesan (Tanenbaum & Van Steen, 2023). Perbedaan inilah yang membuat sistem terdistribusi memiliki tantangan tersendiri dibandingkan sistem terpusat.

Salah satu karakteristik utama sistem terdistribusi adalah konkurensi, yaitu banyak proses berjalan secara bersamaan. Dalam sistem log aggregator, kondisi ini terlihat ketika banyak publisher mengirim event hampir pada waktu yang sama. Jika tidak dikelola dengan baik, konkurensi dapat menyebabkan konflik data atau inkonsistensi hasil pemrosesan. Selain itu, sistem terdistribusi tidak memiliki jam global, sehingga urutan kejadian tidak selalu dapat ditentukan secara absolut. Perbedaan waktu antar mesin dan latency jaringan membuat timestamp dari berbagai sumber tidak selalu sejalan.

Karakteristik lain yang penting adalah kegagalan independen. Setiap komponen dalam sistem dapat mengalami kegagalan tanpa memengaruhi komponen lain. Bahkan, dari sudut pandang sistem, kegagalan sering kali sulit dibedakan dari keterlambatan jaringan. Kondisi ini membuat sistem harus dirancang dengan asumsi bahwa kegagalan adalah hal yang wajar.

Trade-off utama pada desain Pub-Sub log aggregator muncul dari kondisi tersebut. Untuk menjaga keandalan, sistem menerima mekanisme retry yang berpotensi menghasilkan event duplikat. Daripada mengejar jaminan exactly-once yang kompleks dan mahal, sistem ini memilih pendekatan yang lebih realistis dengan menerima duplikasi dan mengelolanya melalui idempotency dan deduplication.

T2 — Arsitektur Client-Server vs Publish-Subscribe

(Bab 2 – Architectures)

Soal:
Bandingkan arsitektur client-server dan publish-subscribe untuk log aggregator. Kapan memilih Pub-Sub?

Jawaban:
Arsitektur client-server bekerja dengan pola komunikasi langsung, di mana client harus mengetahui alamat server dan berinteraksi secara sinkron. Pendekatan ini relatif mudah dipahami dan diimplementasikan, namun memiliki keterbatasan ketika sistem berkembang atau jumlah client meningkat. Ketergantungan langsung antara client dan server membuat sistem menjadi kurang fleksibel terhadap perubahan.

Sebaliknya, arsitektur publish-subscribe memisahkan pengirim dan penerima event. Publisher hanya mengirim event ke sistem tanpa mengetahui siapa yang akan menerimanya. Subscriber cukup berlangganan pada topik tertentu, sementara middleware bertugas mengatur distribusi event. Coulouris dkk. menjelaskan bahwa pola ini memberikan pemisahan yang jelas antara pengirim dan penerima, baik dari sisi ruang maupun waktu, sehingga sistem menjadi lebih longgar keterikatannya (Coulouris et al., 2012).

Dalam konteks log aggregator, publish-subscribe lebih tepat digunakan karena log berasal dari banyak sumber dan dapat diproses oleh berbagai komponen dengan kebutuhan berbeda. Implementasi ini juga memanfaatkan location transparency melalui Docker DNS, sehingga publisher tidak perlu mengetahui lokasi fisik aggregator. Pendekatan ini membuat sistem lebih mudah dikembangkan, dipelihara, dan diskalakan.

T3 — Delivery Semantics dan Idempotent Consumer

(Bab 3 – Processes and Communication)

Soal:
Uraikan perbedaan at-least-once dan exactly-once delivery semantics. Mengapa idempotent consumer krusial di presence of retries?

Jawaban:
At-least-once delivery menjamin bahwa sebuah event akan dikirim setidaknya satu kali, namun tidak menutup kemungkinan event yang sama diterima lebih dari sekali. Pendekatan ini banyak digunakan karena relatif sederhana dan cukup andal dalam menghadapi kondisi jaringan yang tidak stabil. Sebaliknya, exactly-once delivery berusaha memastikan event hanya diproses satu kali, tetapi implementasinya jauh lebih kompleks.

Dalam praktik sistem terdistribusi, pengirim tidak dapat memastikan apakah sebuah event benar-benar gagal diproses atau hanya mengalami keterlambatan. Karena itu, retry menjadi mekanisme yang tidak bisa dihindari. Coulouris dkk. menekankan bahwa ketidakmampuan membedakan antara pesan yang hilang dan pesan yang terlambat merupakan alasan utama mengapa jaminan exactly-once sulit diwujudkan dalam praktik (Coulouris et al., 2012).

Idempotent consumer menjadi solusi yang lebih realistis. Consumer dirancang agar pemrosesan event yang sama tidak mengubah hasil akhir sistem. Pada sistem ini, meskipun event dengan identifier yang sama diterima berkali-kali akibat retry, penulisan ke database hanya terjadi sekali. Dengan pendekatan ini, at-least-once delivery dapat digunakan secara aman tanpa menimbulkan inkonsistensi.

T4 — Penamaan Topic dan Event ID

(Bab 4 – Naming)

Soal:
Rancang skema penamaan untuk topic dan event_id (unik dan collision-resistant). Jelaskan dampaknya terhadap deduplication.

Jawaban:
Dalam sistem terdistribusi, penamaan berperan penting untuk memastikan setiap entitas dapat dikenali secara konsisten. Tanenbaum dan Van Steen menekankan bahwa identifier sebaiknya bersifat unik, stabil, dan tidak bergantung pada lokasi fisik sistem. Prinsip ini menjadi dasar perancangan skema penamaan pada sistem log aggregator.

Sistem ini menggunakan kombinasi topic dan event_id sebagai penanda unik setiap event. Topic digunakan untuk mengelompokkan event berdasarkan jenis atau domain log, sedangkan event_id berfungsi sebagai identifier unik yang membedakan satu event dengan event lainnya. Pendekatan ini memungkinkan sistem menangani event dengan payload atau timestamp yang mirip tanpa kebingungan.

Dampaknya terhadap deduplication cukup signifikan. Ketika event dengan kombinasi topic dan event_id yang sama diterima kembali, sistem dapat langsung mengenalinya sebagai duplikat tanpa perlu membandingkan isi payload. Dengan demikian, proses deduplikasi menjadi lebih sederhana, efisien, dan mendukung pemrosesan yang bersifat idempotent.

T5 — Waktu dan Ordering Event

(Bab 5 – Time and Ordering)

Soal:
Bahas ordering pada sistem log aggregator. Kapan total ordering tidak diperlukan? Usulkan pendekatan praktis dan batasannya.

Jawaban:
Masalah waktu dan urutan kejadian menjadi tantangan tersendiri dalam sistem terdistribusi karena tidak adanya jam global. Total ordering memang memungkinkan semua event diproses dalam urutan yang sama, tetapi membutuhkan koordinasi tambahan yang mahal dan dapat menurunkan performa sistem.

Pada sistem log aggregator, total ordering tidak selalu diperlukan. Fokus utama sistem adalah memastikan seluruh event tercatat dengan benar, bukan menjaga urutan global yang benar-benar ketat. Oleh karena itu, sistem ini menggunakan pendekatan yang lebih praktis dengan mengandalkan timestamp berbasis ISO8601 (UTC) dari masing-masing source.

Pendekatan ini cukup untuk kebutuhan analisis dan observabilitas log. Namun, sistem juga menyadari adanya keterbatasan, seperti kemungkinan perbedaan waktu antar mesin. Keterbatasan tersebut diterima sebagai trade-off yang wajar demi menjaga performa dan kesederhanaan desain.

T6 — Failure Modes dan Strategi Mitigasi

(Bab 6 – Fault Tolerance)

Soal:
Identifikasi failure modes (duplikasi, out-of-order, crash) dan jelaskan strategi mitigasinya.

Jawaban:
Dalam sistem terdistribusi, kegagalan bukanlah hal yang luar biasa, melainkan kondisi yang harus diantisipasi sejak awal. Event dapat dikirim ulang, diproses tidak berurutan, atau sistem dapat mengalami crash sewaktu-waktu. Coulouris dkk. menyatakan bahwa kegagalan parsial merupakan karakteristik normal dari sistem terdistribusi (Coulouris et al., 2012).

Untuk mengatasi duplikasi akibat retry, sistem ini menggunakan deduplication yang disimpan secara persisten di database PostgreSQL. Penyimpanan ini berada pada Docker Volume, sehingga data deduplikasi tetap tersedia meskipun container direstart. Selain itu, pemrosesan event dibuat idempotent agar retry tidak menimbulkan efek samping tambahan.

Dengan pendekatan tersebut, sistem dapat pulih dengan cepat setelah kegagalan tanpa kehilangan konsistensi data, sejalan dengan prinsip fault tolerance yang dibahas dalam Bab 6.

T7 — Eventual Consistency

(Bab 7 – Consistency and Replication)

Soal:
Definisikan eventual consistency pada log aggregator dan jelaskan bagaimana idempotency serta deduplication membantu mencapainya.

Jawaban:
Eventual consistency menggambarkan kondisi di mana sistem tidak selalu konsisten setiap saat, tetapi akan mencapai konsistensi pada akhirnya. Model ini banyak digunakan pada sistem terdistribusi karena lebih toleran terhadap kegagalan dan partisi jaringan dibandingkan konsistensi kuat (Tanenbaum & Van Steen, 2023).

Dalam sistem log aggregator, eventual consistency berarti database pada akhirnya hanya akan berisi event unik. Meskipun event diterima berulang kali atau dalam urutan yang berbeda, state akhir sistem tetap benar. Idempotency memastikan bahwa pemrosesan ulang tidak mengubah hasil akhir, sedangkan deduplication mencegah penyimpanan event duplikat.

Kombinasi kedua mekanisme tersebut memungkinkan sistem mencapai konsistensi akhir tanpa memerlukan koordinasi global yang mahal.

T8 — Metrik Evaluasi Sistem

(Bab 1–7 – Sintesis)

Soal:
Rumuskan metrik evaluasi sistem (throughput, latency, duplicate rate) dan kaitkan dengan keputusan desain.

Jawaban:
Evaluasi sistem dilakukan dengan melihat beberapa metrik utama yang relevan dengan tujuan desain. Throughput digunakan untuk mengukur kemampuan sistem memproses banyak event secara bersamaan, sedangkan latency memberikan gambaran tentang respons sistem terhadap beban kerja.

Selain itu, tingkat duplikasi menjadi indikator penting untuk menilai efektivitas deduplication dan idempotent consumer. Pengujian setelah restart juga dilakukan untuk memastikan sistem tetap bekerja dengan benar setelah mengalami kegagalan. Metrik-metrik ini dipilih karena mencerminkan prioritas sistem, yaitu keandalan dan konsistensi akhir, bukan konsistensi kuat atau urutan global yang ketat.

Daftar Pustaka

Tanenbaum, A. S., & Van Steen, M. (2023). Distributed systems (4th ed.). Maarten van Steen.

Coulouris, G., Dollimore, J., Kindberg, T., & Blair, G. (2012). Distributed systems: Concepts and design (5th ed.). Addison-Wesley.

Ringkasan Sistem

Sistem ini merupakan implementasi Pub-Sub Log Aggregator yang menerima event/log dari berbagai publisher melalui HTTP, memvalidasi format event, melakukan deduplikasi berdasarkan pasangan (topic, event_id), lalu menyimpan hasil pemrosesan secara persisten menggunakan SQLite. Desainnya dibuat aman untuk kondisi at-least-once delivery (publisher dapat mengirim ulang event yang sama), sehingga komponen consumer harus bersifat idempotent: event yang sama tidak boleh menimbulkan efek samping lebih dari sekali.

Dedup store disimpan di file database SQLite (di-mount sebagai volume Docker), sehingga ketika container restart, sistem tetap “ingat” event mana yang sudah diproses dan tidak akan memproses ulang duplikat yang sama.

ARSITEKTUR SISTEM
+-------------------+        HTTP POST /publish         +------------------------+
|   Publisher 1     | --------------------------------> |                        |
+-------------------+                                   |                        |
                                                        |    FastAPI Aggregator  |
+-------------------+        HTTP POST /publish         |     (API + Consumer)   |
|   Publisher 2     | --------------------------------> |                        |
+-------------------+                                   |                        |
                                                        +-----------+------------+
+-------------------+        HTTP POST /publish                     |
|   Publisher N     | --------------------------------------------- |
+-------------------+                                               |
                                                                    v
                                                          +---------------------+
                                                          |   Event Validator   |
                                                          |   (Pydantic V2)     |
                                                          +----------+----------+
                                                                    |
                                                                    v
                                                          +---------------------+
                                                          | Deduplication Logic |
                                                          | (ON CONFLICT clause)|
                                                          +----------+----------+
                                                                    |
                                     +------------------------------+------------------------------+
                                     |                                                             |
                                     v                                                             v
                        +---------------------------+                                 +--------------------------+
                        |   PostgreSQL Storage      |                                 |   Atomic Stats Update    |
                        | (Tabel: processed_events) | <-------(Atomic Link)---------> |    (Tabel: stats)        |
                        |   (Durable & Persistent)  |                                 |   (ID=1, No Lost-Update) |
                        +------------+--------------+                                 +------------+-------------+
                                     |                                                             |
                                     |                                                             |
                                     +----------------------(Data Source)--------------------------+
                                                                    |
                                                                    v
                                                       +----------------------------+
                                                       |  GET /events & GET /stats  |
                                                       +----------------------------+

Komponen Utama
Komponen Utama

Publisher: client yang mengirim event melalui HTTP POST. Pada skenario uji, publisher sengaja dapat mengirim ulang event yang sama untuk mensimulasikan at-least-once delivery.

FastAPI Aggregator: menerima request, melakukan validasi, lalu meneruskan event ke pipeline pemrosesan.

Event Validator (Pydantic): memastikan field minimal (topic, event_id, timestamp, source, payload) valid sebelum diproses lebih jauh.

Deduplication Engine: memeriksa apakah (topic, event_id) sudah pernah diproses. Jika sudah, event dicatat sebagai duplikat dan tidak diproses ulang.

SQLite Dedup Store: menyimpan daftar event_id yang sudah diproses secara persisten (tahan restart). Ini yang membuat idempotency benar-benar efektif.

In-Memory Store: menyimpan event yang sudah lolos dedup untuk mendukung query cepat pada GET /events dan ringkasan GET /stats.

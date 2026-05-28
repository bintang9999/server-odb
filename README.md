# Server Telemetri OBD2

> **PERHATIAN: HANYA BERLAKU UNTUK APLIKASI TORQUE YANG SUDAH DI MODIFIKASI**

Sebuah server web ringan dan berkinerja tinggi yang dibangun dengan Python untuk menerima data telemetri kendaraan OBD2 secara *real-time* dari aplikasi Android **Torque Pro**. Server ini secara otomatis mencatat data ke dalam database SQLite dan menyediakan *dashboard* web *real-time* untuk memantau performa kendaraan Anda.

## Fitur Utama

- **Penerimaan Data Real-Time**: Mendukung protokol *web logging* dari Torque Pro secara *native*.
- **Penyimpanan Database SQLite**: Secara otomatis mencatat semua data telemetri (RPM, Kecepatan, Beban Mesin, Suhu Pendingin, *Throttle*, Bahan Bakar, Koordinat GPS) yang dikategorikan berdasarkan perjalanan/sesi.
- **Dashboard Web Live**: Server HTTP bawaan menyediakan *dashboard real-time* yang ditenagai oleh *Server-Sent Events* (SSE).
- **Ekspor ke CSV**: Ekspor perjalanan yang direkam ke dalam file CSV dengan mudah untuk analisis lebih mendalam.
- **Pembersihan Data Otomatis**: Secara otomatis menghapus data yang lebih lama dari 30 hari untuk menghemat ruang penyimpanan.
- **Tanpa Dependensi Eksternal**: Hanya menggunakan pustaka standar bawaan Python (`http.server`, `sqlite3`, dll.).
- **Siap untuk Docker**: Mudah di-deploy di mana saja menggunakan Docker.

## Cara Memulai

### Prasyarat

- Python 3.10+ (jika dijalankan langsung tanpa kontainer)
- Docker (jika menggunakan kontainer)
- [Aplikasi Torque Pro](https://play.google.com/store/apps/details?id=org.prowl.torque) (Android) yang terhubung dengan adaptor Bluetooth OBD2 di mobil Anda.

### Menjalankan dengan Docker (Direkomendasikan)

Anda dapat dengan mudah melakukan *build* dan menjalankan server menggunakan Docker:

```bash
# Build image Docker
docker build -t obd-server .

# Jalankan kontainer (memetakan port 8080 dan membuat volume persisten untuk data)
docker run -d -p 8080:8080 -v $(pwd)/data:/app/data --name obd-server obd-server
```

### Menjalankan Secara Manual

Jika Anda lebih suka menjalankannya menggunakan Python secara langsung:

```bash
# Jalankan server
python server_torque.py
```
Server akan mulai berjalan pada `http://0.0.0.0:8080`.

## Konfigurasi Aplikasi Torque Pro

Untuk mengirim data dari mobil Anda ke server ini, konfigurasikan aplikasi Torque Pro sebagai berikut:

1. Buka aplikasi **Torque Pro**.
2. Buka **Settings** (ikon roda gigi) > **Data Logging & Upload**.
3. Gulir ke bawah hingga menemukan **Webserver URL**.
4. Masukkan alamat IP dan port server Anda: `http://<IP_SERVER_ANDA>:8080`.
5. Centang opsi **Log to webserver**.
6. Atur **Web logging interval** sesuai kecepatan pembaruan yang Anda inginkan (misalnya, `1 second`).
7. Pastikan adaptor OBD2 Anda terhubung dan mobil dalam keadaan menyala. Data akan mulai mengalir ke server Anda.

## Dashboard & API

Setelah server berjalan, buka browser web Anda dan kunjungi `http://<IP_SERVER_ANDA>:8080` untuk mengakses *dashboard live*.

### Endpoint API yang Tersedia:

- `GET /stream`: Stream SSE (*Server-Sent Events*) secara *real-time* untuk data kendaraan yang masuk.
- `GET /api/trips`: Mengembalikan daftar JSON dari semua perjalanan/sesi yang direkam beserta statistik singkatnya (kecepatan maksimal, rata-rata rpm, dll.).
- `GET /api/trips/<session_id>`: Mengembalikan detail data telemetri berformat JSON untuk perjalanan tertentu.
- `GET /api/trips/<session_id>/csv`: Mengunduh data perjalanan dalam format file CSV.

## Pengujian Lokal

Jika Anda ingin menguji server dan *dashboard* tanpa harus terhubung ke mobil, telah disediakan *script dummy data*:

```bash
python send_dummy_data.py
```
Script ini akan menyimulasikan mobil yang sedang dikendarai dan mengirimkan *HTTP GET requests* dengan data OBD2 palsu ke server lokal.

## Lisensi

Proyek ini bersifat *open-source* dan bebas digunakan.

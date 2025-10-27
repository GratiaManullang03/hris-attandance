# Ringkasan Fitur & Flow HRIS Attendance

Dokumen ini merangkum fitur utama dan alur operasional aplikasi HRIS Attendance sebagaimana dijelaskan pada jawaban terakhir.

## Fitur Utama

1. **QR-based attendance dengan rolling token**  
   Display harus mengirim `X-Display-Key` ke endpoint `/attendance/sites/{si_id}/rolling-token` untuk memperoleh JWT baru setiap siklus, sehingga kode QR terus berubah dan sulit direplay. (lihat `app/api/v1/endpoints/attendance.py`, `app/services/attendance_service.py`)

2. **Validasi lokasi & anti-replay**  
   Backend menghitung jarak menggunakan rumus Haversine, mewajibkan koordinat saat geofence aktif, lalu menyimpan `jti` di tabel anti-replay agar token yang sama tidak bisa dipakai ulang oleh user yang sama. (lihat `app/services/attendance_service.py`)

3. **Manajemen sesi otomatis berbasis WIB**  
   Semua scan sebelum 13:00 WIB dipaksa sebagai check-in, sedangkan setelah 13:00 WIB otomatis menjadi check-out, memastikan hanya satu sesi terbuka per hari dan seluruh aksi tercatat ke audit log. (lihat `app/services/attendance_service.py`)

4. **CRUD lokasi & geofence oleh admin**  
   Pengguna dengan role ≥50 dapat membuat, memperbarui, dan menghapus site lengkap dengan validasi ID dan geofence wajib saat enforcement aktif. (lihat `app/api/v1/endpoints/sites.py`, `app/services/site_service.py`)

5. **Keamanan SSO, enkripsi respons, dan RBAC**  
   Semua endpoint attendance menggunakan Atlas SSO, pembatasan role minimal, serta opsi enkripsi payload respons GET untuk data sensitif. (lihat `README.md`, `app/api/v1/endpoints/attendance.py`)

6. **Frontend PWA display & scanner**  
   `display-qr.html` menampilkan QR besar yang auto-refresh dengan countdown dan wake lock. `scan-qr.html` melakukan pengecekan GPS, menyediakan torch, snapshot visual, serta mengirim token + koordinat ke backend. (lihat file HTML terkait)

7. **Endpoint maintenance untuk cleanup JTI**  
   Admin dapat memanggil `/maintenance/cleanup-jti` guna menghapus token lama sehingga tabel proteksi replay tetap ringan. (lihat `app/api/v1/endpoints/maintenance.py`)

## Flow Operasional

1. **Setup lokasi & aturan** – Admin menambah site via endpoint Sites sekaligus radius geofence. Konfigurasi ini dikonsumsi generator token agar setiap QR mereferensikan site valid.
2. **Perangkat display** – Aplikasi `display-qr.html` menyimpan `backend`, `displayKey`, dan `siteId`, lalu memuat token baru tiap `duration` detik dan menggambar QR beresolusi tinggi bagi karyawan.
3. **Proses scan karyawan** – Pengguna membuka `scan-qr.html`, aplikasi memastikan GPS aktif, menyalakan kamera, lalu setelah QR terbaca mengirim token + koordinat + bearer token Atlas SSO ke `/attendance/scan`.
4. **Bisnis logic backend** – Server memverifikasi JWT QR, mengecek geofence, memblokir replay, lalu menentukan apakah sesi dibuat atau ditutup berdasarkan jam WIB, sembari mencatat event audit.
5. **Monitoring & histori** – Pengguna dapat melihat status sesi hari ini dan riwayat event pribadi, sedangkan admin memiliki endpoint pencarian sesi lengkap dengan filter user, site, tanggal, status, dan urutan.
6. **Maintenance berkala** – Job terjadwal memanggil endpoint cleanup agar `used_jti` tidak membengkak dan performa tetap stabil.

## Rekomendasi Lanjutan

1. Dokumentasikan cara mengubah konfigurasi `CONFIG` pada kedua PWA agar tim operasional mudah mengarahkan ke environment berbeda.
2. Jadwalkan eksekusi otomatis untuk endpoint cleanup (cron server atau workflow CI) supaya proteksi anti-replay tetap efisien tanpa intervensi manual.

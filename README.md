# Argon AI Toolkit

**Languages:** **Bahasa Indonesia** · [English](README.canonical.md) · [Tiếng Việt](README.vi.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Español](README.es.md) · [Français](README.fr.md)

Toolkit terminal otomatis untuk **Windows dan Linux** (serta macOS) untuk memeriksa, mendiagnosis, dan menguji penawaran langganan Google AI Pro melalui Android, ADB, Frida, dan Google Play.

> **Rebuild / Rewrite by: Zennz466**  
> **Instagram: [@zennz_466](https://instagram.com/zennz_466)**

<img width="2048" height="1521" alt="image" src="https://github.com/user-attachments/assets/fc27278f-7833-4484-9770-33e46bf10005" />

> [!CAUTION]
> **Proyek eksperimental tidak resmi. Risiko pemotongan biaya nyata.**  
> Tahap **2–5** dapat membuka antarmuka checkout resmi Google Play dan menekan tombol **Subscribe** atau **Langganan**. Munculnya penawaran di daftar atau tampilan harga Rp 0 pada fase awal bukan jaminan kelayakan akun atau aktivasi langganan permanen. Selalu periksa akun, nominal tagihan, dan tanggal perpanjangan di Google Play sebelum melanjutkan. Jangan gunakan opsi tidak aman seperti `-Force` karena dapat melewati verifikasi akun Google Play.

---

## Daftar Isi
1. [Tentang Proyek](#tentang-proyek)
2. [Tahapan Uji Coba (Steps 0–5)](#tahapan-uji-coba-steps-05)
3. [Panduan Penggunaan Windows](#panduan-penggunaan-windows)
4. [Panduan Penggunaan Linux (Waydroid)](#panduan-penggunaan-linux-waydroid)
5. [TUI Dashboard Textual](#tui-dashboard-textual)
6. [CLI PowerShell dan Terminal](#cli-powershell-dan-terminal)
7. [Penyelesaian Masalah (Troubleshooting)](#penyelesaian-masalah-troubleshooting)
8. [Keamanan Pembayaran](#keamanan-pembayaran)
9. [Kredit dan Sumber Kode](#kredit-dan-sumber-kode)

---

## Tentang Proyek

Argon AI Toolkit adalah toolkit otomasi pengujian penawaran promosi Google AI Pro (5 TB) di Android. Toolkit ini menghubungkan host PC ke lingkungan Android via ADB, menginjeksi hook Frida 16.5.9 ke Google One BillingClient, dan memvalidasi penawaran intro Rp 0 langsung dari katalog Google Play Store.

Repositori ini telah di-rebuild dan disempurnakan oleh **Zennz466** dengan penambahan dukungan penuh Linux berbasis Waydroid, adapter terminal native, dan perbaikan keamanan checkout.

---

## Tahapan Uji Coba (Steps 0–5)

Kontrak tahapan di dalam toolkit ini terbagi menjadi 6 tahap terstruktur:

- **Step 0: Pemeriksaan Lingkungan**: Memeriksa koneksi ADB, status root emulator/Waydroid, keberadaan Frida 16.5.9, dan modul Google Play Store.
- **Step 1: Cek Penawaran (Read-Only)**: Membaca katalog produk Google One via BillingClient tanpa memicu proses checkout. Tahap ini aman dan bebas biaya.
- **Step 2: Google AI Pro 12 Bulan**: Mencoba paket promo uji coba 12 bulan gratis (`pro12` / `12months-eft`).
- **Step 3: Google AI Pro 6 Bulan**: Paket promo uji coba 6 bulan pertama gratis (`pro6` / `6months-eft`).
- **Step 4: Penumpukan +6 Bulan (Tahap 1)**: Perpanjangan masa aktif uji coba tambahan 6 bulan (`pro6b` / `6months-eft-2`).
- **Step 5: Penumpukan +6 Bulan (Tahap 2)**: Perpanjangan masa aktif uji coba tambahan 6 bulan berikutnya (`pro6c` / `6months-eft-ss-2026`).

Setelah menyelesaikan Step 3, pengguna wajib memverifikasi status langganan di aplikasi Google Play Store sebelum menekan **Verified in Google Play** untuk melanjutkan ke Step 4 dan Step 5.

---

## Panduan Penggunaan Windows

Panduan terperinci tersedia di [README.windows.md](README.windows.md) dan [Panduan Instalasi](docs/INSTALLATION.md).

### 1. Prasyarat
- Windows 10 atau Windows 11 (64-bit).
- Python 3.10 hingga 3.12 terpasang dan terdaftar di PATH sistem.
- Emulator Android: Direkomendasikan **MuMuPlayer 12** (Android 12, 64-bit).
- Pengaturan MuMuPlayer:
  - Aktifkan izin Root di pengaturan emulator.
  - Aktifkan koneksi ADB (port default `127.0.0.1:16384` atau `127.0.0.1:7555`).
- Pasang aplikasi Google Play Store dan Google One di dalam emulator.
- Login akun Google di emulator dan hubungkan kartu debit/kredit valid (Google Play menolak dompet digital seperti DANA untuk pra-otorisasi masa uji coba langganan).

### 2. Instalasi dan Persiapan
Buka PowerShell di folder proyek:

```powershell
# Pasang virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Pasang pustaka Python
pip install textual frida==16.5.9 frida-tools

# Jalankan preflight otomatis
python setup_env.py
```

### 3. Menjalankan Dashboard
Cukup jalankan script launcher utama tanpa argumen:

```powershell
.\run-all.ps1
```

Dashboard interaktif Textual akan muncul. Klik **Check Device & Offers** untuk memeriksa perangkat dan penawaran tanpa risiko penagihan.

---

## Panduan Penggunaan Linux (Waydroid)

Panduan terperinci tersedia di [README.linux.md](README.linux.md) dan [Panduan Fedora Waydroid](docs/FEDORA-WAYDROID.md).

### 1. Prasyarat
- Distribusi Linux (Fedora, Ubuntu, Debian, atau Arch Linux).
- Waydroid terpasang dengan image GAPPS (Google Play Services aktif).
- Paket `adb` (`android-tools`).
- Python 3.10+ dalam `.venv`.

### 2. Konfigurasi Waydroid
1. Jalankan sesi Waydroid:
   ```bash
   waydroid session start &
   ```
2. Hubungkan ADB ke IP Waydroid (biasanya `192.168.240.112`):
   ```bash
   adb connect 192.168.240.112:5555
   ```
3. Nonaktifkan proteksi sentuhan sintetis Android sekali saja:
   ```bash
   adb -s 192.168.240.112:5555 shell settings put global block_untrusted_touches 0
   ```
4. Pastikan Frida Server berjalan:
   ```bash
   adb -s 192.168.240.112:5555 shell "/data/local/tmp/frida-server &"
   ```

### 3. Menjalankan Launcher Linux
Gunakan script shell native Linux:

```bash
sh run-linux.sh
```

Atau jalankan pemeriksaan awal:
```bash
sh run-linux.sh --check
```

> [!NOTE]
> Pada sistem macOS, gunakan script launcher POSIX native melalui `sh run-macos.sh` seperti yang dijelaskan di [Pratinjau macOS](docs/MACOS-PREVIEW.md).

### 4. Interaksi Klik Mouse di Linux (Penting)
Google Play checkout pada Android 12+ memproteksi tombol pembayaran dari simulasi sentuhan sintetis via ADB. Ketika lembar checkout muncul di jendela Waydroid dan menampilkan Rp 0:
**Klik tombol Subscribe atau Langganan langsung menggunakan mouse fisik Anda pada jendela Waydroid.**

Skrip terminal akan memantau database lokal Google Play hingga 120 detik sampai token pembelian terdeteksi.

---

## TUI Dashboard Textual

Dashboard terminal berbasis Textual dirancang agar mudah digunakan oleh pengguna umum:
- **Tampilan Utama**: Memperlihatkan serial perangkat yang terhubung, akun Google Play aktif, dan tombol cepat **Check Device & Offers**.
- **Mode Eksekusi**:
  - *One step only*: Menjalankan satu tahap terpilih saja (Step 0 hingga 5).
  - *From selected step*: Menjalankan alur terpandu mulai dari tahap yang dipilih.
  - *All: Steps 2-5*: Alur lengkap terpandu mulai dari Step 2.
- **Log Real-time**: Menampilkan proses injeksi Frida, deteksi penawaran, dan hasil evaluasi terms secara langsung.

---

## CLI PowerShell dan Terminal

Untuk pengguna mahir atau otomasi tanpa antarmuka TUI:

### Perintah Windows PowerShell
```powershell
# Cek lingkungan saja (Step 0)
.\run-all.ps1 -Step 0 -Cli

# Baca penawaran tanpa checkout (Step 1)
.\run-all.ps1 -Step 1 -Cli

# Eksekusi Step 3 (6 bulan promo)
.\run-all.ps1 -Step 3 -Cli

# Menjalankan alur lengkap dari tahap 3
.\run-all.ps1 -StartStep 3 -AllStages
```

### Perintah Langsung Python
```bash
# Cek penawaran
.venv/bin/python ultra0.py --list --no-add --no-switch --serial 192.168.240.112:5555

# Eksekusi checkout promo 6 bulan
.venv/bin/python ultra0.py --no-add --no-switch --serial 192.168.240.112:5555 --plan pro6 --account emailanda@gmail.com
```

Pelajari opsi command-line dan alur automasi mendalam pada [Panduan Penggunaan](docs/USAGE.md).

---

## Penyelesaian Masalah (Troubleshooting)

- **Emulator atau Waydroid tidak terdeteksi**:  
  Pastikan emulator atau Waydroid sudah berjalan sempurna. Ketik `adb devices` di terminal untuk melihat daftar perangkat.
- **Pesan "Promo tidak ditemukan"**:  
  Terjadi jika metode pembayaran Google Play memakai e-wallet (DANA/GoPay). Ubah metode pembayaran utama ke kartu debit atau kredit fisik/virtual.
- **Pesan "The item you requested is not available for purchase"**:  
  Server Google membatasi penawaran 12 bulan (`12months-eft`) untuk akun atau wilayah tertentu. Gunakan opsi 6 bulan (`pro6` / `6months-eft`) yang tersedia untuk akun Anda.
- **Koneksi Frida terputus (Error code 3 / BILLING_UNAVAILABLE)**:  
  Pastikan versi Frida host dan server sama-sama menggunakan **16.5.9**, dan aplikasi Google One sedang berjalan di latar depan.

Laporan eksekusi tersimpan rapi dalam folder `ultra0-report/` dan log debug di folder `logs/`. Jangan pernah mengunggah log atau file laporan yang belum disanitasi karena dapat memuat data akun pribadi.

---

## Keamanan Pembayaran

- Baca [Dokumentasi Keamanan](docs/SAFETY.md) dan [Pernyataan Penyangkalan](DISCLAIMER.md) sebelum menjalankan tahap berbayar.
- Bank penerbit kartu Anda mungkin melakukan pra-otorisasi sementara (hold) untuk memvalidasi kartu (biasanya akan dilepas kembali secara otomatis oleh pihak bank).
- Jangan membagikan token pembelian, sandi, atau data kartu kepada siapa pun.
- Kunjungi [Pusat Dokumentasi](docs/README.md) dan [Arsitektur Proyek](docs/PROJECT.md) untuk mempelajari struktur teknis lebih dalam.

---

## Kredit dan Sumber Kode

- **Rebuild & Linux Waydroid Adapter**: **Zennz466** (Instagram: [@zennz_466](https://instagram.com/zennz_466))
- **Maintainer Upstream**: [David Nguyen (@hoangsvit)](https://github.com/hoangsvit) / [ePlus.DEV](https://eplus.dev) - [google-ai](https://github.com/hoangsvit/google-ai)
- **Author Original Engine**: [@gylive](https://github.com/gylive) - [github.com/gylive/google-ultra](https://github.com/gylive/google-ultra)

Lisensi asli MIT dari upstream tetap dipertahankan dan dicantumkan pada file `THIRD_PARTY_NOTICES.md`.

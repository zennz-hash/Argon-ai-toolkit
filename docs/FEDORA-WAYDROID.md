# Fedora & Waydroid Guide — ePlus AI Toolkit

Panduan instalasi dan penggunaan **ePlus AI Toolkit** di **Fedora Linux** menggunakan **Waydroid** sebagai pengganti emulator MuMu Player (Windows).

---

## 1. Arsitektur & Perbedaan dengan Windows/MuMu

| Komponen | Versi Windows (Asli) | Fedora Linux + Waydroid (Rewritten) |
| :--- | :--- | :--- |
| **Emulator** | NetEase MuMuPlayer (Windows closed-source) | **Waydroid** (Container LXC Android native Wayland) |
| **Launcher** | PowerShell (`run-all.ps1`) | Native Shell script (`run-linux.sh`) & Python venv |
| **Runner** | PowerShell subprocess wrapper | `linux_runner.py` via Python 3 |
| **Koneksi ADB** | Port TCP lokal (`127.0.0.1:16384`, `7555`, dll.) | IP Container (`192.168.240.112:5555` via `waydroid0`) / `waydroid adb connect` |
| **Root Access** | Pengaturan root bawaan MuMu | `adb root` (built-in userdebug build di Waydroid) / `su` |
| **Frida Server** | `frida-server-16.5.9-android-x86` / `arm` | `frida-server-16.5.9-android-x86_64` (diunduh otomatis) |

---

## 2. Persyaratan Sistem di Fedora

Pastikan paket-paket berikut terpasang di Fedora:

```bash
# 1. Pasang dependensi ADB dan Python
sudo dnf install -y android-tools python3 python3-pip

# 2. Pastikan sesi Wayland aktif (Waydroid memerlukan Wayland)
echo $XDG_SESSION_TYPE
# Output harus: wayland
```

---

## 3. Menyiapkan Waydroid di Fedora

### Langkah A: Inisialisasi Waydroid dengan GAPPS (Google Play)
Jika belum pernah menginisialisasi Waydroid:
```bash
sudo waydroid init -s GAPPS
sudo systemctl enable --now waydroid-container
```

### Langkah B: Sertifikasi Google Play di Waydroid (Wajib untuk GAPPS)
Karena Waydroid bukan perangkat fisik resmi, Google Play memerlukan pendaftaran ID perangkat (Google Services Framework ID):
1. Jalankan Waydroid:
   ```bash
   waydroid session start &
   waydroid show-full-ui &
   ```
2. Hubungkan ADB dan ambil GSF Android ID:
   ```bash
   adb connect 192.168.240.112:5555
   adb root
   adb shell 'sqlite3 /data/data/com.google.android.gsf/databases/gservices.db "select * from main where name = \"android_id\";"'
   ```
   *(Atau periksa di log `adb logcat | grep -i gsf`)*.
3. Buka halaman pendaftaran Google: [https://www.google.com/android/uncertified/](https://www.google.com/android/uncertified/) dan masukkan Android ID tersebut.
4. Restart Waydroid container:
   ```bash
   sudo systemctl restart waydroid-container
   ```

### Langkah C: Pasang Google One
1. Buka Play Store di dalam Waydroid.
2. Login dengan akun Google yang ingin diperiksa penawarannya.
3. Cari dan pasang **Google One** (`com.google.android.apps.subscriptions.red`).
4. Buka aplikasi Google One setidaknya satu kali agar aplikasi aktif dan terhubung dengan akun.

---

## 4. Menjalankan ePlus AI Toolkit di Fedora

Gunakan launcher `run-linux.sh`:

```bash
# 1. Jalankan dashboard interaktif (TUI)
./run-linux.sh

# 2. Atau cek diagnostik Android, Root, dan Frida terlebih dahulu:
./run-linux.sh --check

# 3. Atau cek daftar penawaran saja (tanpa checkout):
./run-linux.sh --list

# 4. Langsung menuju Step tertentu di TUI:
./run-linux.sh --step 1
```

Launcher akan otomatis:
1. Memverifikasi ketersediaan `adb` dan `python3`.
2. Membuat virtual environment lokal `.venv`.
3. Memasang `frida==16.5.9` dan `textual==8.2.8` tanpa menyentuh paket sistem Fedora.
4. Mendeteksi dan menghubungkan ADB ke container Waydroid secara otomatis (`192.168.240.112:5555`).
5. Menyiapkan `frida-server` 16.5.9 x86_64 di dalam Waydroid.

---

## 5. Fitur Keselamatan (Safety & Billing)

- **Step 0**: Diagnostik lingkungan, ADB, status root, dan Frida.
- **Step 1**: Hanya membaca/menampilkan penawaran langganan Google AI Pro yang tersedia di akun Google aktif. **Tidak ada transaksi/pembayaran**.
- **Step 2–5**: Memeriksa promosi uji coba nol rupiah ($0) sebelum membuka dialog checkout Google Play. Memerlukan konfirmasi manual bertahap di antarmuka TUI.

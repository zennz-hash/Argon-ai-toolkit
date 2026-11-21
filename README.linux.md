# ePlus AI Toolkit: Linux Guide

Guide for running the ePlus AI Toolkit on Linux distributions (Fedora, Ubuntu, Debian, Arch Linux) using Waydroid or connected Android devices.

## Overview

ePlus AI Toolkit on Linux provides stage adaptation and testing for Google AI Pro subscription offers. It works with Waydroid container environments or network-connected Android emulators, using ADB and Frida 16.5.9 to query and inspect Google One billing offers.

## Prerequisites

Ensure the following tools and packages are installed on your host system:

1. Operating system: Linux with Wayland or X11 (Fedora 38+, Ubuntu 22.04+, Arch Linux).
2. Python 3.10, 3.11, 3.12, or 3.14 with `python3-pip` and `python3-virtualenv`.
3. Android platform tools (`adb`):
   - Fedora: `sudo dnf install android-tools`
   - Ubuntu/Debian: `sudo apt install adb`
   - Arch Linux: `sudo pacman -S android-tools`
4. Waydroid installed with GAPPS support:
   - Follow your distribution guide to install Waydroid with Google Play Services.
5. Android container setup:
   - Launch Waydroid and sign in to Google Play Store with your Google account.
   - Install the Google One app from Google Play inside Waydroid.
   - Attach a valid debit or credit card to Google Play. E-wallets (such as DANA or GoPay) fail during recurring zero-price authorization checks.

## Waydroid Configuration

### 1. Start Waydroid and Verify Network

Start the container session:

```bash
waydroid session start &
```

Check IP address assigned to Waydroid:

```bash
cat /var/lib/misc/dnsmasq.waydroid0.leases
```

The default IP is usually `192.168.240.112`. Connect ADB to Waydroid:

```bash
adb connect 192.168.240.112:5555
adb devices
```

### 2. Disable Untrusted Touch Filtering

Android 12+ drops synthetic ADB touch events on checkout views that set obscured flags. Run the following command once to prevent touch event drops:

```bash
adb -s 192.168.240.112:5555 shell settings put global block_untrusted_touches 0
```

### 3. Install and Run Frida Server

Frida 16.5.9 is required on both host and Android container:

```bash
# Check host architecture; Waydroid x86_64 requires android-x86_64 build
curl -LO https://github.com/frida/frida/releases/download/16.5.9/frida-server-16.5.9-android-x86_64.xz
unxz frida-server-16.5.9-android-x86_64.xz
adb -s 192.168.240.112:5555 push frida-server-16.5.9-android-x86_64 /data/local/tmp/frida-server
adb -s 192.168.240.112:5555 shell chmod 755 /data/local/tmp/frida-server
adb -s 192.168.240.112:5555 shell "/data/local/tmp/frida-server &"
```

Verify that frida-server is running:

```bash
adb -s 192.168.240.112:5555 shell pidof frida-server
```

## Installation

1. Clone repository:

```bash
git clone <your-repository-url>
cd geminiPRO
```

2. Set up virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install textual frida==16.5.9 frida-tools
```

3. Run offline test suite to verify code integrity:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

All repository tests must pass before running live operations.

## Running the Toolkit

### Method 1: Linux Launcher Script (Recommended)

Run `run-linux.sh` to launch the interactive Textual dashboard:

```bash
sh run-linux.sh
```

Flags available in `run-linux.sh`:
- `sh run-linux.sh --check`: Run preflight environment checks.
- `sh run-linux.sh --list`: Query available offers in read-only mode without opening checkout.
- `sh run-linux.sh --step N`: Launch dashboard directly on Step N (0 to 5).
- `sh run-linux.sh --waydroid-start`: Attempt to start Waydroid session if inactive.

### Method 2: Direct CLI Execution

1. Check environment and device readiness:
```bash
.venv/bin/python ultra0.py --check --serial 192.168.240.112:5555
```

2. List available offers (read-only):
```bash
.venv/bin/python ultra0.py --list --no-add --no-switch --serial 192.168.240.112:5555
```

3. Launch 6-month free trial checkout (`pro6`):
```bash
.venv/bin/python ultra0.py --no-add --no-switch --serial 192.168.240.112:5555 --plan pro6 --account your-account@gmail.com
```

## Touch Interaction on Checkout

Google Play checkout uses security flags that block programmatic touch injection on the Subscribe button.

When `run-linux.sh` or `ultra0.py` reaches the checkout stage:
1. The Google Play bottom sheet appears in your Waydroid window.
2. Confirm the total is Rp 0 / $0.00 today and the trial duration is correct.
3. Click the "Subscribe" or "Langganan" button using your mouse directly inside the Waydroid window.
4. The script polls Google Play's local library database for up to 120 seconds to confirm purchase completion.

## Stacking Flow

To stack subsequent free trial extensions:
1. Complete Step 3 (`pro6` / `6months-eft`).
2. Verify active subscription at `https://play.google.com/store/account/subscriptions`.
3. Run Step 4 (`pro6b` / `6months-eft-2`) with `--stack`.
4. Run Step 5 (`pro6c` / `6months-eft-ss-2026`) with `--stack`.

## Troubleshooting

### Waydroid container fails DNS queries
If Google Play Services shows "No internet connection" or hangs on token retrieval:
1. Check that IP forwarding is enabled on host:
   ```bash
   sudo sysctl -w net.ipv4.ip_forward=1
   ```
2. Check firewall zone for waydroid interface:
   ```bash
   sudo firewall-cmd --zone=trusted --add-interface=waydroid0 --permanent
   sudo firewall-cmd --reload
   ```
3. Check DNS resolution inside Waydroid:
   ```bash
   adb -s 192.168.240.112:5555 shell ping -c 3 8.8.8.8
   adb -s 192.168.240.112:5555 shell ping -c 3 google.com
   ```

### VPN and TUN interface conflicts
If a VPN client was running on the host, dangling TUN interfaces can divert Waydroid traffic into inactive routing tables. Disconnect the VPN and check the default route:
```bash
ip route show
```

### Frida session detachment (BILLING_UNAVAILABLE)
If `run_trial` fails with resultCode 3 or BILLING_UNAVAILABLE:
- Ensure Google One app is running before running the script.
- Ensure `frida-server` matches version 16.5.9.

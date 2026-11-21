# ePlus AI Toolkit: Windows Guide

Guide for running the ePlus AI Toolkit on Windows 10 and Windows 11 using Android emulators (such as MuMu Player 12).

## Overview

ePlus AI Toolkit automates the inspection and staged testing of Google AI Pro subscription offers on Android. On Windows, it operates through an interactive Textual terminal dashboard (`run-all.ps1`) or direct PowerShell CLI commands. It communicates with an Android emulator through ADB and injects Frida hooks into the Google One billing client.

## Prerequisites

Before starting, prepare the following requirements:

1. Windows 10 or Windows 11 (64-bit).
2. Python 3.10, 3.11, or 3.12 added to your system PATH.
3. Android emulator: MuMu Player 12 (Android 12, 64-bit) is recommended.
4. Emulator settings:
   - Root permission enabled in MuMu Player settings.
   - ADB connection enabled (default port is `127.0.0.1:16384` or `127.0.0.1:7555`).
5. Apps installed inside the emulator:
   - Google Play Store (updated to current version).
   - Google One app installed from Google Play.
6. Google account setup inside emulator:
   - Log into the target Google account in Google Play Store.
   - Attach a valid debit or credit card as the payment method. Google Play rejects e-wallets (such as DANA or GoPay) for introductory zero-price trial authorizations.

## Installation

1. Open PowerShell:

```powershell
git clone <your-repository-url>
cd geminiPRO
```

2. Create and activate a Python virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install required Python packages:

```powershell
pip install textual frida==16.5.9 frida-tools
```

4. Run the environment preflight check:

```powershell
python setup_env.py
```

This verifies that ADB is reachable, the emulator is online, root access is granted, and frida-server 16.5.9 is active on the emulator.

## Running the Toolkit

### Method 1: Interactive TUI Dashboard (Recommended)

Launch the dashboard without arguments:

```powershell
.\run-all.ps1
```

The dashboard displays:
- Device connection status and verified Google Play account.
- One-click "Check Device & Offers" button (read-only, Step 1).
- Workflow selection: "One step only", "From selected step", or "All: Steps 2-5".
- Real-time output log and status indicators.

### Method 2: PowerShell CLI

For headless or scripted execution, run specific stages directly:

1. Check environment and dependencies (Step 0):
```powershell
.\run-all.ps1 -Step 0 -Cli
```

2. List available offers without opening checkout (Step 1, read-only):
```powershell
.\run-all.ps1 -Step 1 -Cli
```

3. Open checkout for 6-month free trial (`pro6`):
```powershell
.\run-all.ps1 -Step 3 -Cli
```

4. Run direct Python CLI with explicit parameters:
```powershell
python ultra0.py --no-add --no-switch --serial 127.0.0.1:16384 --plan pro6 --account your-account@gmail.com
```

## Stage Reference

- Step 0: Environment setup and connectivity checks (ADB, root, frida-server, Google Play).
- Step 1: Query introductory offers via Google One BillingClient (read-only, no charges).
- Step 2: Google AI Pro 12 months free trial (`pro12` / `12months-eft`).
- Step 3: Google AI Pro 6 months free trial (`pro6` / `6months-eft`).
- Step 4: First 6-month extension stacking (`pro6b` / `6months-eft-2`).
- Step 5: Second 6-month extension stacking (`pro6c` / `6months-eft-ss-2026`).

## Billing Safety Rules

- Steps 2 to 5 can trigger real charges or pre-authorizations on your payment card.
- In the TUI dashboard, every checkout step requires separate, explicit confirmation before any transaction begins.
- Always check Google Play subscriptions (`https://play.google.com/store/account/subscriptions`) to verify renewal dates and active status before proceeding to extension stages.
- Never use `--force` in production. It bypasses safety checks designed to protect against wrong-account billing.

## Troubleshooting

### Emulator not detected by ADB
Ensure MuMu Player 12 is fully loaded. In PowerShell, test the connection manually:
```powershell
adb connect 127.0.0.1:16384
adb devices
```

### Frida server connection error
Frida client and server versions must match (16.5.9). If frida-server is not running, run:
```powershell
python setup_env.py
```
This automatically transfers and starts `frida-server-16.5.9` with root permissions.

### Error: "Promo tidak ditemukan"
Google Play displays this error when an e-wallet is selected as the primary payment method for a recurring subscription trial. Change the payment method in Google Play to a physical or virtual debit/credit card.

### Error: "The item you requested is not available for purchase"
Google restricts the 12-month promotional offer (`12months-eft`) to specific regions or eligible device fingerprints. If this error occurs on Step 2, switch to Step 3 (`pro6` / `6months-eft`), which offers the 6-month trial followed by stacking.

#!/bin/sh
# Native Linux & Fedora launcher for ePlus AI Toolkit with Waydroid support.
# Checkout requires explicit TUI approval.
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

usage() {
  printf '%s\n' \
    "ePlus AI Toolkit — Linux & Fedora (Waydroid, Steps 0–5)" \
    "Usage: sh run-linux.sh [--check | --list | --step N [--sequence] | --sequence | --waydroid-start | --help]" \
    "  (no flags)        Textual dashboard, including optional confirmed checkout" \
    "  --check           Android & Waydroid/Frida setup diagnostics" \
    "  --list            Query offers (no checkout)" \
    "  --step N          Open the dashboard with Step 0..5 selected" \
    "  --sequence        Open dashboard with guided sequence controls" \
    "  --waydroid-start  Attempt to start Waydroid session if stopped" \
    "  --help            Display usage" \
    "" \
    "Steps 2–5 can submit real charges after explicit TUI confirmations."
}

if [ "$#" -eq 1 ] && { [ "$1" = "--help" ] || [ "$1" = "-h" ]; }; then
  usage
  exit 0
fi

if [ "$#" -eq 1 ] && [ "$1" = "--waydroid-start" ]; then
  if command -v waydroid >/dev/null 2>&1; then
    printf '%s\n' "Starting Waydroid session..."
    waydroid session start >/dev/null 2>&1 &
    sleep 3
    waydroid status || true
  else
    printf '%s\n' "Waydroid is not installed. Install with: sudo dnf install waydroid" >&2
  fi
  exit 0
fi

MODE=""
case "$#" in
  0) MODE="tui" ;;
  1) case "$1" in
    --check) MODE="check" ;;
    --list) MODE="list" ;;
    --sequence) MODE="tui" ;;
    *) usage >&2; exit 2 ;;
  esac ;;
  2|3)
    if [ "$1" != "--step" ]; then usage >&2; exit 2; fi
    case "$2" in
      0|1|2|3|4|5) : ;;
      *) usage >&2; exit 2 ;;
    esac
    if [ "$#" -eq 3 ] && [ "$3" != "--sequence" ]; then usage >&2; exit 2; fi
    MODE="tui" ;;
  *) usage >&2; exit 2 ;;
esac

if [ "$(uname -s)" != "Linux" ]; then
  printf '%s\n' "This launcher requires Linux. On macOS use ./run-macos.sh, on Windows use .\\run-all.ps1" >&2
  exit 2
fi

if ! command -v python3 >/dev/null 2>&1 ||
   ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
  printf '%s\n' "Install Python 3.10+ to run this toolkit (e.g. sudo dnf install python3)." >&2
  exit 2
fi

if ! command -v adb >/dev/null 2>&1; then
  printf '%s\n' "ADB is missing. On Fedora, install it with: sudo dnf install android-tools" >&2
  printf '%s\n' "After installing, check 'adb devices'." >&2
  exit 2
fi

# Inform about Waydroid status
if command -v waydroid >/dev/null 2>&1; then
  WAYDROID_SESSION=$(waydroid status 2>/dev/null | grep -i "session:" | awk '{print $2}' || echo "UNKNOWN")
  if [ "$WAYDROID_SESSION" = "STOPPED" ]; then
    printf '\033[1;33m%s\033[0m\n' "Note: Waydroid session is currently STOPPED."
    printf '%s\n' "To start Waydroid, run 'waydroid session start' or launch Waydroid from your application menu."
  fi
fi

if [ ! -x .venv/bin/python ]; then
  printf '%s\n' "Creating virtual environment in .venv..."
  python3 -m venv .venv
fi

PYTHON=.venv/bin/python

if ! "$PYTHON" -c "import importlib.metadata as m; import textual, frida; assert m.version('frida') == '16.5.9'" >/dev/null 2>&1; then
  printf '%s\n' "Installing required dependencies (frida==16.5.9, textual)..."
  "$PYTHON" -m pip install --disable-pip-version-check -r requirements-tui.txt "frida==16.5.9"
fi

export PYTHONIOENCODING=utf-8:backslashreplace
export PYTHONUTF8=1

case "$MODE" in
  check) exec "$PYTHON" linux_runner.py --step 0 ;;
  list)  exec "$PYTHON" linux_runner.py --step 1 ;;
  tui)
    if [ "$#" -eq 0 ]; then exec "$PYTHON" tui.py; fi
    exec "$PYTHON" tui.py "$@" ;;
esac
exit 2

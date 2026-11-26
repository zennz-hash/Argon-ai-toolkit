#!/bin/sh
# Desktop launcher helper for Argon / ePlus AI Toolkit on Linux.
# Opens the interactive Textual dashboard by default (no automatic checkout).
set -eu

REPO_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
cd "$REPO_DIR"

export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export PYTHONIOENCODING=utf-8:backslashreplace
export PYTHONUTF8=1

MODE="${1:-gui}"

pause_screen() {
  printf '\n%s' "Press Enter to close this window..."
  IFS= read -r _ || true
}

connect_waydroid_if_needed() {
  if ! command -v adb >/dev/null 2>&1 || ! command -v waydroid >/dev/null 2>&1; then
    return 0
  fi
  WD_IP="$(waydroid status 2>/dev/null | awk '/IP address:/ {print $3}' || true)"
  if [ -n "$WD_IP" ] && [ "$WD_IP" != "UNKNOWN" ]; then
    adb connect "${WD_IP}:5555" >/dev/null 2>&1 || true
  fi
}

detect_serial() {
  if ! command -v adb >/dev/null 2>&1; then
    return 0
  fi
  adb devices 2>/dev/null | awk 'NR > 1 && $2 == "device" {print $1; exit}'
}

run_in_terminal() {
  TARGET_MODE="$1"
  SCRIPT_PATH="$REPO_DIR/tools/linux/launch-desktop.sh"
  if command -v konsole >/dev/null 2>&1; then
    exec konsole --workdir "$REPO_DIR" -p tabtitle="Argon AI Toolkit" -e sh "$SCRIPT_PATH" "$TARGET_MODE"
  elif command -v kitty >/dev/null 2>&1; then
    exec kitty --directory "$REPO_DIR" --title "Argon AI Toolkit" sh "$SCRIPT_PATH" "$TARGET_MODE"
  elif command -v alacritty >/dev/null 2>&1; then
    exec alacritty --working-directory "$REPO_DIR" --title "Argon AI Toolkit" -e sh "$SCRIPT_PATH" "$TARGET_MODE"
  elif command -v gnome-terminal >/dev/null 2>&1; then
    exec gnome-terminal --working-directory="$REPO_DIR" --title="Argon AI Toolkit" -- sh "$SCRIPT_PATH" "$TARGET_MODE"
  elif command -v xfce4-terminal >/dev/null 2>&1; then
    exec xfce4-terminal --working-directory="$REPO_DIR" --title="Argon AI Toolkit" -e "sh '$SCRIPT_PATH' '$TARGET_MODE'"
  elif command -v xterm >/dev/null 2>&1; then
    exec xterm -T "Argon AI Toolkit" -e sh "$SCRIPT_PATH" "$TARGET_MODE"
  else
    printf '%s\n' "No supported terminal emulator found (konsole, kitty, alacritty, gnome-terminal, xterm)." >&2
    exit 1
  fi
}

if [ "$MODE" = "--terminal" ]; then
  NEXT_MODE="${2:-dashboard}"
  run_in_terminal "$NEXT_MODE"
fi

case "$MODE" in
  gui)
    connect_waydroid_if_needed
    if command -v python3 >/dev/null 2>&1 && python3 -c "import PyQt5" >/dev/null 2>&1; then
      exec python3 "$REPO_DIR/gui.py"
    fi
    run_in_terminal dashboard
    ;;
  dashboard)
    connect_waydroid_if_needed
    if ! sh "$REPO_DIR/run-linux.sh"; then
      pause_screen
      exit 1
    fi
    ;;
  check)
    connect_waydroid_if_needed
    sh "$REPO_DIR/run-linux.sh" --check || true
    pause_screen
    ;;
  list)
    connect_waydroid_if_needed
    sh "$REPO_DIR/run-linux.sh" --list || true
    pause_screen
    ;;
  sku-all|sku-free)
    connect_waydroid_if_needed
    SERIAL="$(detect_serial || true)"
    PYTHON="$REPO_DIR/.venv/bin/python"
    if [ ! -x "$PYTHON" ]; then
      sh "$REPO_DIR/run-linux.sh" --check >/dev/null 2>&1 || true
    fi
    if [ ! -x "$PYTHON" ]; then
      PYTHON="python3"
    fi
    if [ "$MODE" = "sku-free" ]; then
      if [ -n "$SERIAL" ]; then
        "$PYTHON" "$REPO_DIR/query_sku.py" --preset all --only-free --serial "$SERIAL" || true
      else
        "$PYTHON" "$REPO_DIR/query_sku.py" --preset all --only-free || true
      fi
    else
      if [ -n "$SERIAL" ]; then
        "$PYTHON" "$REPO_DIR/query_sku.py" --preset all --serial "$SERIAL" || true
      else
        "$PYTHON" "$REPO_DIR/query_sku.py" --preset all || true
      fi
    fi
    pause_screen
    ;;
  waydroid)
    if command -v waydroid >/dev/null 2>&1; then
      exec waydroid show-full-ui
    else
      printf '%s\n' "Waydroid is not installed." >&2
      pause_screen
      exit 1
    fi
    ;;
  *)
    printf '%s\n' "Usage: sh launch-desktop.sh [--terminal] [gui|dashboard|check|list|sku-all|sku-free|waydroid]" >&2
    exit 2
    ;;
esac

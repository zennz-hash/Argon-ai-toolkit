#!/bin/sh
# Install 1-click Linux desktop shortcut and application menu icon for Argon AI Toolkit.
set -eu

REPO_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
LAUNCHER="$REPO_DIR/tools/linux/launch-desktop.sh"
ICON_SRC="$REPO_DIR/assets/argon-ai-toolkit.svg"

ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
APP_DIR="$HOME/.local/share/applications"
DESKTOP_DIR="${XDG_DESKTOP_DIR:-$HOME/Desktop}"

ICON_DST="$ICON_DIR/argon-ai-toolkit.svg"
APP_DESKTOP="$APP_DIR/argon-ai-toolkit.desktop"
USER_DESKTOP="$DESKTOP_DIR/Argon-AI-Toolkit.desktop"

if [ ! -f "$ICON_SRC" ]; then
  printf '%s\n' "Icon asset is missing: $ICON_SRC" >&2
  exit 1
fi

chmod +x "$REPO_DIR/run-linux.sh" "$LAUNCHER"

mkdir -p "$ICON_DIR" "$APP_DIR"
cp "$ICON_SRC" "$ICON_DST"

write_desktop_file() {
  TARGET_FILE="$1"
  cat > "$TARGET_FILE" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Argon AI Toolkit
GenericName=Google AI Pro Offer Inspector
Comment=One-click desktop GUI for ePlus AI Toolkit (Waydroid step-by-step guide & offer detector)
Exec=/bin/sh "$LAUNCHER" gui
Path=$REPO_DIR
Icon=$ICON_DST
Terminal=false
Categories=Utility;
Keywords=argon;eplus;google;one;ai;waydroid;frida;sku;
StartupNotify=true
StartupWMClass=argon-ai-toolkit
Actions=tui-dashboard;check-offers;sku-free;env-check;waydroid-ui;

[Desktop Action tui-dashboard]
Name=Open Terminal TUI Dashboard
Exec=/bin/sh "$LAUNCHER" --terminal dashboard
Icon=$ICON_DST

[Desktop Action check-offers]
Name=Check Device & Offers (Read-Only Step 1)
Exec=/bin/sh "$LAUNCHER" --terminal list
Icon=$ICON_DST

[Desktop Action sku-free]
Name=Multi-SKU Inspector (Free Intro Only)
Exec=/bin/sh "$LAUNCHER" --terminal sku-free
Icon=$ICON_DST

[Desktop Action env-check]
Name=Environment Diagnostics (Step 0)
Exec=/bin/sh "$LAUNCHER" --terminal check
Icon=$ICON_DST

[Desktop Action waydroid-ui]
Name=Start Waydroid UI
Exec=/bin/sh "$LAUNCHER" waydroid
Icon=$ICON_DST
EOF
  chmod 755 "$TARGET_FILE"
}

write_desktop_file "$APP_DESKTOP"
if [ -d "$DESKTOP_DIR" ]; then
  write_desktop_file "$USER_DESKTOP"
fi

if command -v desktop-file-validate >/dev/null 2>&1; then
  desktop-file-validate "$APP_DESKTOP"
  if [ -f "$USER_DESKTOP" ]; then
    desktop-file-validate "$USER_DESKTOP"
  fi
fi

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$APP_DIR" >/dev/null 2>&1 || true
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1 || true
fi

if command -v kbuildsycoca6 >/dev/null 2>&1; then
  kbuildsycoca6 --noincremental >/dev/null 2>&1 || true
elif command -v kbuildsycoca5 >/dev/null 2>&1; then
  kbuildsycoca5 --noincremental >/dev/null 2>&1 || true
fi

printf '%s\n' "Installed Argon AI Toolkit desktop launcher:"
printf '  App Menu : %s\n' "$APP_DESKTOP"
if [ -f "$USER_DESKTOP" ]; then
  printf '  Desktop  : %s\n' "$USER_DESKTOP"
fi
printf '  Icon     : %s\n' "$ICON_DST"

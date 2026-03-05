#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"

"$PYTHON_BIN" -m pip install --upgrade pip
"$PYTHON_BIN" -m pip install "pyinstaller==6.11.1"

"$PYTHON_BIN" -m PyInstaller \
  --noconfirm \
  --clean \
  --name DroneChorusControlRoom \
  --windowed \
  --add-data "presets:presets" \
  --add-data "config:config" \
  --add-data "software/midi-bridge/webmidi_preview.html:." \
  software/midi-bridge/gui_app.py

echo "Built app in dist/DroneChorusControlRoom"

#!/usr/bin/env bash
#
# capture_msp.sh - Record MSP telemetry from a serial port into a timestamped
#                  .mspbin file using pyserial's miniterm.
#
# Usage examples:
#   scripts/capture_msp.sh /dev/ttyUSB0 obs/telemetry
#   scripts/capture_msp.sh COM5 logs/custom_hover.mspbin
#
# The first argument is the serial port (whatever you point Betaflight Configurator at).
# The second argument is either a directory (where the script will drop
# TIMESTAMP_port.mspbin) or a full path to the desired .mspbin file. Override the
# default 115200 baud rate by setting MSP_BAUD before running the script.
#
# The script prints status messages to stdout, but the binary capture stays in
# the generated .mspbin file so you can replay it later.
set -euo pipefail

if [[ $# -lt 2 ]]; then
  cat <<USAGE >&2
Usage: $0 SERIAL_PORT OUTPUT_PATH

SERIAL_PORT  Serial device to read from (e.g. /dev/ttyUSB0, /dev/ttyACM0, COM5).
OUTPUT_PATH  Directory to store the capture or an explicit .mspbin file.

Set MSP_BAUD to override the default 115200 baud rate.
USAGE
  exit 1
fi

PORT="$1"
TARGET="$2"
BAUD="${MSP_BAUD:-115200}"
TIMESTAMP="$(date -u +%Y%m%d-%H%M%S)"
PORT_TAG="$(basename "$PORT" | tr -c 'A-Za-z0-9_' '_')"

if [[ "${TARGET##*.}" == "mspbin" ]]; then
  OUT_FILE="$TARGET"
  mkdir -p "$(dirname "$OUT_FILE")"
else
  mkdir -p "$TARGET"
  OUT_FILE="$TARGET/${TIMESTAMP}_${PORT_TAG}.mspbin"
fi

if [[ -e "$OUT_FILE" ]]; then
  echo "Refusing to overwrite existing file: $OUT_FILE" >&2
  exit 2
fi

command -v python >/dev/null 2>&1 || { echo "python is required." >&2; exit 3; }

finish() {
  local exit_code=$?
  echo
  if [[ $exit_code -eq 0 ]]; then
    echo "Capture complete: $OUT_FILE"
  else
    echo "Capture aborted (exit code $exit_code). Partial file (if any): $OUT_FILE"
  fi
}
trap finish EXIT

cat <<INFO
Listening to $PORT @ ${BAUD} baud.
Writing raw MSP frames to $OUT_FILE
Press Ctrl+C when you've captured enough spice.
INFO

python -m serial.tools.miniterm --raw "$PORT" "$BAUD" >"$OUT_FILE"

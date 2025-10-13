#!/usr/bin/env python3
"""CLI wrapper for bridging a single MSP serial stream into MIDI CCs.

Welcome to the "one drone, one synth voice" entry point. This script is meant
to be read almost like lab notes—every helper explains why it exists so that
you can remix it without guessing.

Flow overview:

1. Parse command-line arguments (serial port, MIDI options, scaling configs).
2. Load the YAML normalization spec and any overrides students want to try.
3. Open or create a MIDI port using :mod:`mido`.
4. Delegate to :func:`msp_bridge.run_bridge`, which handles the realtime loop.
   That loop mirrors the multi-drone bridge by faking a gentle altitude ramp
   from throttle whenever the craft never publishes ``MSP_ALTITUDE`` frames, so
   CC17 keeps breathing even on minimal receivers.

If you're teaching or learning from this code, skim the argument parser first;
it documents every knob you can twist without touching the Python.
"""

import argparse
import struct
import sys
import time
from typing import Any, Dict, Optional

import mido
import yaml

from msp_bridge import MSP_ALTITUDE, clamp, run_bridge


def build_altitude_helpers():
    """Mirror the multi-bridge altitude fallback for the solo CLI."""

    last_altitude_update = 0.0
    last_altitude_m = 0.0

    def decode_altitude(state: Dict[str, float], payload: bytes) -> None:
        """Populate ``state['altitude']`` from ``MSP_ALTITUDE`` payloads."""

        nonlocal last_altitude_update, last_altitude_m
        if len(payload) < 4:
            return
        altitude_cm = struct.unpack("<i", payload[:4])[0]
        last_altitude_m = altitude_cm / 100.0
        state["altitude"] = last_altitude_m
        last_altitude_update = time.time()

    def inject_altitude(state: Dict[str, float]) -> None:
        """Ensure ``state['altitude']`` keeps moving even without baro data."""

        nonlocal last_altitude_update, last_altitude_m
        now = time.time()
        if now - last_altitude_update > 1.0:
            normalized = (state["throttle"] - 1000.0) / 1000.0
            normalized = clamp(normalized, 0.0, 1.0)
            state["altitude"] = normalized * 3.0
        else:
            state["altitude"] = last_altitude_m

    return decode_altitude, inject_altitude


def load_norm(config_path: str, key: Optional[str]) -> Dict[str, Dict[str, float]]:
    """Load a normalization block from ``config_path``.

    Args:
        config_path: Path to a YAML file containing either the norm dict itself
            or a parent mapping with named norm blocks.
        key: Optional key to select inside the YAML document. ``None`` means the
            top-level document is already the norm mapping.

    Raises:
        ValueError: If the document structure doesn't match what we expect.
    """

    with open(config_path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if key is None:
        if not isinstance(data, dict):
            raise ValueError(f"Expected mapping in {config_path} for normalization spec")
        return data
    try:
        norm = data[key]
    except KeyError as exc:
        raise ValueError(f"Key '{key}' not found in {config_path}") from exc
    if not isinstance(norm, dict):
        raise ValueError(f"Expected mapping at key '{key}' in {config_path}")
    return norm


def load_overrides(path: Optional[str]) -> Optional[Dict[str, Dict[str, float]]]:
    """Read optional per-parameter overrides from YAML.

    ``None`` signals "no overrides" which keeps the base config intact. Students
    can copy-paste the ``norm`` block into a new YAML file and tweak values
    without touching the shared repo.
    """

    if not path:
        return None
    with open(path, "r", encoding="utf-8") as fh:
        overrides = yaml.safe_load(fh) or None
    if overrides is not None and not isinstance(overrides, dict):
        raise ValueError("Overrides file must contain a mapping of parameters")
    return overrides


def open_midi_output(name: Optional[str], virtual: bool) -> Any:
    """Open a MIDI output port, falling back to the default port on failure."""

    if name:
        try:
            return mido.open_output(name, virtual=virtual)
        except Exception:
            return mido.open_output()
    return mido.open_output()


def parse_args() -> argparse.Namespace:
    """Set up and parse the command-line interface."""

    parser = argparse.ArgumentParser(description="Bridge MSP telemetry to MIDI CCs for one craft.")
    parser.add_argument("--serial", required=True, help="Serial port that exposes MSP telemetry")
    parser.add_argument("--channel", type=int, default=1, help="1-based MIDI channel to target (default: 1)")
    parser.add_argument(
        "--midi-port",
        default="DroneChorus",
        help="Name of the MIDI output port to open or create. Defaults to 'DroneChorus'.",
    )
    parser.add_argument(
        "--no-virtual",
        action="store_true",
        help="Do not request a virtual MIDI port when creating --midi-port.",
    )
    parser.add_argument(
        "--norm-config",
        default="config/multi.yaml",
        help="YAML file containing a 'norm' block to reuse for scaling.",
    )
    parser.add_argument(
        "--norm-key",
        default="norm",
        help="Key within --norm-config that holds the normalization spec. Use '-' to treat the file itself as the spec.",
    )
    parser.add_argument(
        "--norm-overrides",
        help="Path to a YAML file with per-parameter overrides (same shape as multi config norm overrides).",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=0.02,
        help="Seconds between CC bursts (default: 0.02).",
    )
    parser.add_argument(
        "--idle-sleep",
        type=float,
        default=0.001,
        help="Seconds to nap while waiting for MSP frames (default: 0.001).",
    )
    return parser.parse_args()


def main() -> None:
    """Parse CLI arguments, load configs, and launch :func:`run_bridge`."""

    args = parse_args()
    norm_key = None if args.norm_key == "-" else args.norm_key
    norm = load_norm(args.norm_config, norm_key)
    overrides = load_overrides(args.norm_overrides)
    midi_out = open_midi_output(args.midi_port, virtual=not args.no_virtual)
    decode_altitude, inject_altitude = build_altitude_helpers()

    try:
        run_bridge(
            args.serial,
            midi_out,
            norm,
            channel=max(0, args.channel - 1),
            norm_overrides=overrides,
            poll_interval=args.poll_interval,
            idle_sleep=args.idle_sleep,
            extra_state_handlers={MSP_ALTITUDE: decode_altitude},
            state_hook=inject_altitude,
        )
    except KeyboardInterrupt:
        # Let ctrl+c exit without a stack trace—the performance should stay calm.
        sys.exit(0)


if __name__ == "__main__":
    main()

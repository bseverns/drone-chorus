#!/usr/bin/env python3
"""CLI wrapper for bridging a single MSP serial stream into MIDI CCs."""

import argparse
import sys
from typing import Any, Dict, Optional

import mido
import yaml

from msp_bridge import run_bridge


def load_norm(config_path: str, key: Optional[str]) -> Dict[str, Dict[str, float]]:
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
    if not path:
        return None
    with open(path, "r", encoding="utf-8") as fh:
        overrides = yaml.safe_load(fh) or None
    if overrides is not None and not isinstance(overrides, dict):
        raise ValueError("Overrides file must contain a mapping of parameters")
    return overrides


def open_midi_output(name: Optional[str], virtual: bool) -> Any:
    if name:
        try:
            return mido.open_output(name, virtual=virtual)
        except Exception:
            return mido.open_output()
    return mido.open_output()


def parse_args() -> argparse.Namespace:
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
    args = parse_args()
    norm_key = None if args.norm_key == "-" else args.norm_key
    norm = load_norm(args.norm_config, norm_key)
    overrides = load_overrides(args.norm_overrides)
    midi_out = open_midi_output(args.midi_port, virtual=not args.no_virtual)

    try:
        run_bridge(
            args.serial,
            midi_out,
            norm,
            channel=max(0, args.channel - 1),
            norm_overrides=overrides,
            poll_interval=args.poll_interval,
            idle_sleep=args.idle_sleep,
        )
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()

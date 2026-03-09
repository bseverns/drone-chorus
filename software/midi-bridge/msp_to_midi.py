#!/usr/bin/env python3
"""CLI wrapper for bridging a single MSP serial stream into MIDI CCs.

Welcome to the "one drone, one synth voice" entry point. This script is meant
to be read almost like lab notes-every helper explains why it exists so that
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
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from midi_ports import open_midi_output as open_shared_midi_output
from msp_bridge import (
    build_altitude_consumers,
    build_signal_schema,
    merge_state_handlers,
    run_bridge,
)


def load_yaml(config_path: str) -> Dict[str, Any]:
    """Load a YAML config document and coerce empty docs to ``{}``."""

    with open(config_path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {config_path}")
    return data


def load_norm(config_data: Dict[str, Any], key: Optional[str]) -> Dict[str, Dict[str, float]]:
    """Load a normalization block from the parsed YAML document."""

    if key is None:
        norm = config_data
    else:
        try:
            norm = config_data[key]
        except KeyError as exc:
            raise ValueError(f"Key '{key}' not found in config") from exc
    if not isinstance(norm, dict):
        raise ValueError("Normalization spec must be a mapping")
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
    """Open a MIDI output port with explicit fallback warning output."""

    return open_shared_midi_output(
        name,
        virtual=virtual,
        fallback_to_default=True,
        on_fallback=lambda message: print(f"[midi-warning] {message}", file=sys.stderr),
    )


def build_estop_checker(path: Optional[str]):
    """Return a callback that reports whether the E-stop latch is active."""

    if not path:
        return None
    estop_path = Path(path)

    def estop_is_active() -> bool:
        return estop_path.exists()

    return estop_is_active


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
    parser.add_argument(
        "--throttle-limit",
        type=float,
        help="Optional max throttle value (1000-2000) enforced before CC mapping.",
    )
    parser.add_argument(
        "--gate-threshold",
        type=float,
        default=1050.0,
        help="Throttle threshold for gate CC64 (default: 1050).",
    )
    parser.add_argument(
        "--estop-file",
        help="When this file exists, the bridge forces throttle idle and gate off.",
    )
    return parser.parse_args()


def main() -> None:
    """Parse CLI arguments, load configs, and launch :func:`run_bridge`."""

    args = parse_args()
    config_data = load_yaml(args.norm_config)
    norm_key = None if args.norm_key == "-" else args.norm_key
    norm = load_norm(config_data, norm_key)
    overrides = load_overrides(args.norm_overrides)
    midi_out = open_midi_output(args.midi_port, virtual=not args.no_virtual)

    inject_altitude, altitude_handlers = build_altitude_consumers()
    signals_cfg = config_data.get("signals") if norm_key is not None else None
    state_template, cc_mapping, schema_handlers = build_signal_schema(signals_cfg)
    extra_handlers = merge_state_handlers(altitude_handlers, schema_handlers)
    estop_hook = build_estop_checker(args.estop_file)

    try:
        run_bridge(
            args.serial,
            midi_out,
            norm,
            channel=max(0, args.channel - 1),
            norm_overrides=overrides,
            poll_interval=args.poll_interval,
            idle_sleep=args.idle_sleep,
            extra_state_handlers=extra_handlers,
            state_hook=inject_altitude,
            state_template=state_template,
            cc_mapping=cc_mapping,
            throttle_limit=args.throttle_limit,
            estop_hook=estop_hook,
            gate_threshold=args.gate_threshold,
        )
    except KeyboardInterrupt:
        # Let ctrl+c exit without a stack trace-the performance should stay calm.
        sys.exit(0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Replay an MSP log into the Drone Chorus MIDI bridge.

This script is the guaranteed, batteries-included way to prove that the
telemetry pipeline works even without a quad plugged in. It mirrors the live
`msp_to_midi.py` flow:

1. Open (or spawn) a MIDI output port.
2. Decode MSP frames from a `.mspbin` file.
3. Pump every tracked signal through the same mapper/smoother stack used on
   stage, so CC14-CC20 + CC64 behave exactly like the real drone.

Usage
-----
First rebuild the sample logs (binaries live as base64 in
`scripts/generate_sample_logs.py`):

```
python scripts/generate_sample_logs.py
```

Then run the replay helper:

```
python examples/replay_log.py data/example_log_01.mspbin
```

Patch the newly created `DroneChorus-Replay` virtual port into VCV Rack, Ableton,
or whatever synth is closest. Swap in your own log files or edit the `norm`
section inside `config/mapping.yaml` to teach the mapper how to respond. That's
the sweet spot for students: tweak the ranges/curves, rerun this script, and you
instantly hear how the math shapes the music.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Dict

import mido
import yaml

# Make sure we can import the bridge utilities no matter where this script lives.
REPO_ROOT = Path(__file__).resolve().parents[1]
BRIDGE_DIR = REPO_ROOT / "software" / "midi-bridge"
if str(BRIDGE_DIR) not in sys.path:
    sys.path.insert(0, str(BRIDGE_DIR))

import msp_bridge  # type: ignore  # pylint: disable=wrong-import-position


class MSPLogSerial:
    """Minimal ``serial`` lookalike that feeds MSP bytes from memory.

    ``msp_bridge.read_msp_frame`` only needs a ``read(size)`` method. We keep a
    pointer into a ``bytes`` blob and hand back slices on demand. Returning
    ``b""`` tells the bridge that no new data is available.
    """

    def __init__(self, payload: bytes, loop: bool = False) -> None:
        self._payload = payload
        self._loop = loop
        self._pos = 0
        self._exhausted = False

    def read(self, size: int = 1) -> bytes:
        if not self._payload:
            self._exhausted = True
            return b""
        if self._pos >= len(self._payload):
            if self._loop:
                self._pos = 0
            else:
                self._exhausted = True
                return b""
        end = min(self._pos + size, len(self._payload))
        chunk = self._payload[self._pos : end]
        self._pos = end
        return chunk

    @property
    def exhausted(self) -> bool:
        return self._exhausted


class MIDILogger:
    """Tiny logger that mirrors every CC to stdout when ``--verbose`` is on."""

    def __init__(self, enabled: bool) -> None:
        self._enabled = enabled

    def dump(self, state: Dict[str, float]) -> None:
        if not self._enabled:
            return
        values = " ".join(f"{key}={value:6.2f}" for key, value in state.items())
        print(f"STATE {values}")


def load_norm_config(path: Path) -> Dict[str, Dict[str, float]]:
    data = yaml.safe_load(path.read_text())
    try:
        return data["norm"]
    except KeyError as exc:
        raise SystemExit(f"Config {path} is missing a 'norm' section") from exc


def choose_midi_port(port_name: str, virtual: bool):
    """Return an opened MIDI output, creating a virtual port when requested."""

    try:
        return mido.open_output(port_name, virtual=virtual)
    except (IOError, OSError) as exc:
        raise SystemExit(
            "Failed to open MIDI port. Pass --no-virtual to reuse an existing "
            "port or double-check your backend."
        ) from exc


def replay_log(
    log_path: Path,
    midi_port: str,
    norm: Dict[str, Dict[str, float]],
    *,
    channel: int,
    poll_interval: float,
    idle_sleep: float,
    loop: bool,
    virtual: bool,
    verbose: bool,
) -> None:
    try:
        payload = log_path.read_bytes()
    except FileNotFoundError as exc:
        raise SystemExit(
            f"{log_path} does not exist. Run 'python scripts/generate_sample_logs.py' "
            "to rehydrate the sample logs or capture your own .mspbin first."
        ) from exc
    if not payload:
        raise SystemExit(f"{log_path} is empty—did you capture any bytes?")
    mapper = msp_bridge.build_mapper(norm)
    state = dict(msp_bridge._STATE_TEMPLATE)
    serial_source = MSPLogSerial(payload, loop=loop)
    logger = MIDILogger(verbose)

    with choose_midi_port(midi_port, virtual=virtual) as midi_out:
        print(
            f"Replaying {log_path} into '{midi_out.name}' on MIDI channel {channel + 1}."
        )
        last_emit = 0.0
        while True:
            frame = msp_bridge.read_msp_frame(serial_source)
            if frame is None:
                if serial_source.exhausted and not loop:
                    print("Done. All frames transmitted.")
                    return
                time.sleep(idle_sleep)
                continue
            cmd, data = frame
            msp_bridge.update_state_from_msp(state, cmd, data)
            now = time.time()
            if now - last_emit > poll_interval:
                msp_bridge.emit_state_cc(midi_out, mapper, channel, state)
                logger.dump(state)
                last_emit = now


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pipe a recorded MSP log directly into the MIDI bridge.",
    )
    parser.add_argument("log", type=Path, help="Path to a .mspbin capture")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/mapping.yaml"),
        help="YAML file with the 'norm' mapping (defaults to config/mapping.yaml)",
    )
    parser.add_argument(
        "--midi-port",
        default="DroneChorus-Replay",
        help="Name for the MIDI output/virtual port",
    )
    parser.add_argument(
        "--channel",
        type=int,
        default=1,
        help="1-16 MIDI channel to use (defaults to 1).",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=0.02,
        help="Seconds between CC bursts.",
    )
    parser.add_argument(
        "--idle-sleep",
        type=float,
        default=0.001,
        help="Sleep duration while waiting for the next frame.",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Replay the log forever (handy for gallery installs).",
    )
    parser.add_argument(
        "--no-virtual",
        dest="virtual",
        action="store_false",
        help="Use an existing MIDI port instead of spawning a virtual one.",
    )
    parser.set_defaults(virtual=True)
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print the normalized state each time we emit CCs.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    norm = load_norm_config(args.config)
    if not 1 <= args.channel <= 16:
        raise SystemExit("Channel must live in the 1-16 range.")
    replay_log(
        args.log,
        args.midi_port,
        norm,
        channel=args.channel - 1,
        poll_interval=args.poll_interval,
        idle_sleep=args.idle_sleep,
        loop=args.loop,
        virtual=args.virtual,
        verbose=args.verbose,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Shared MSP-to-MIDI bridge utilities for Drone Chorus.

This module is the beating heart of the *Drone Chorus* telemetry pipeline. It
is intentionally written in a "show-your-work" style so that students and
curious performers can follow the signal chain from the serial wire all the way
to the MIDI messages that animate their synth patches.

Key ideas worth keeping in mind while reading:

* **MSP (MultiWii Serial Protocol)** is the telemetry dialect spoken by
  Betaflight and friends. Every MSP packet carries a command identifier and a
  payload of raw bytes. We sample only the few commands we care about (attitude,
  RC inputs, analog sensors).
* **Normalization + smoothing** keeps the MIDI output musical. The `Mapper`
  applies scaling curves (stored in YAML configs) and the `Smoother` class makes
  sure sudden jumps get softened into glissandos instead of glitches.
* **MIDI CC messages** are just controller-change events. Each tracked signal
  gets assigned a controller number (see `_CC_MAPPING`), and we send those
  values at a steady cadence while MSP frames roll in.

If you're new to this style of code, start by skimming the module-level
constants, then read `run_bridge` from top to bottom. Every helper is annotated
with intent and the data it touches.
"""

import struct
import time
from typing import Dict, Optional

import mido
import serial

# -- MSP command identifiers -------------------------------------------------
# These numeric IDs are defined by the MSP spec. We pull out only the ones we
# need; think of them as opcodes that label the payload format.
MSP_ATTITUDE = 108
MSP_RC = 105
MSP_ANALOG = 110

# A scratch buffer of the telemetry values we track. Each entry represents the
# "most recent" version of a sensor reading. The numbers below are safe defaults
# in case the serial line hasn't delivered anything yet.
_STATE_TEMPLATE = {
    "roll": 0.0,
    "pitch": 0.0,
    "yaw": 0.0,
    "altitude": 0.0,
    "rssi": 100.0,
    "vbat": 4.0,
    "throttle": 1000,
}

# Each telemetry field gets pegged to a MIDI CC number. The specific values are
# mostly arbitrary, but choosing a contiguous block keeps the Rack patch tidy.
_CC_MAPPING = {
    "roll": 14,
    "pitch": 15,
    "yaw": 16,
    "altitude": 17,
    "rssi": 18,
    "vbat": 19,
    "throttle": 20,
}


def clamp(x: float, lo: float, hi: float) -> float:
    """Limit ``x`` to the inclusive range ``[lo, hi]``.

    This tiny helper shows up everywhere because both MSP and MIDI have
    well-defined limits. Without clamping we'd risk sending negative CC values
    or blowing past the 0-127 MIDI range.
    """

    return max(lo, min(hi, x))


class Smoother:
    """Single-pole slew limiter for taming sudden jumps in controller values.

    Many MSP readings (RSSI, RC sticks) can spike several percentage points
    between frames. Feeding that straight into MIDI would produce zipper noise.
    The smoother stores the last output value and walks toward the new value at
    a fixed rate (the ``slew`` parameter).
    """

    def __init__(self, slew: float = 0.05) -> None:
        # ``slew`` is the maximum amount we allow the output to move per update
        # step. Smaller numbers => slower, more graceful movements.
        self._slew = slew
        self._y: Optional[float] = None

    def step(self, x: float) -> float:
        """Push a new reading through the filter and return the smoothed value."""

        if self._y is None:
            # Bootstrap: the first sample simply sets the initial state.
            self._y = x
            return x
        delta = clamp(x - self._y, -self._slew, self._slew)
        self._y += delta
        return self._y


class Mapper:
    """Translate raw telemetry numbers into normalized (0-1) controller values.

    The ``norm`` argument comes from the YAML config files. Each entry defines a
    ``min``/``max`` range, an optional ``curve`` (currently only ``"expo"``),
    and an optional per-parameter ``slew`` value. ``Mapper`` owns a
    :class:`Smoother` per key and feeds normalized readings through it before
    handing them off to the MIDI layer.
    """

    def __init__(self, norm: Dict[str, Dict[str, float]]) -> None:
        self._norm = norm
        self._smoothers = {
            key: Smoother(spec.get("slew", 0.03)) for key, spec in norm.items()
        }

    def norm01(self, key: str, value: float) -> float:
        """Return a smoothed, normalized number in the ``[0, 1]`` range."""

        spec = self._norm[key]
        lo, hi = spec["min"], spec["max"]
        rng = hi - lo
        # Guard against ``min == max`` by falling back to 0.0.
        v = 0.0 if rng == 0 else (value - lo) / rng
        v = clamp(v, 0.0, 1.0)
        if spec.get("curve") == "expo":
            # Exponential shaping makes the center of the joystick feel more
            # sensitive while preserving the endpoints. Raise to a power, keep
            # the sign, then shift back into [0, 1].
            shaped = (abs(v - 0.5) * 2) ** 1.3
            shaped *= 1 if v >= 0.5 else -1
            v = shaped * 0.5 + 0.5
        return self._smoothers[key].step(v)


def read_msp_frame(ser) -> Optional[tuple]:
    """Read a single MSP frame from ``ser``.

    MSP packets always start with the byte trio ``$M<`` followed by a payload
    length, command identifier, payload bytes, and a checksum. We ignore the
    checksum because Betaflight streams fast enough that a corrupt frame can be
    tossed without fuss.
    """

    if ser.read(1) != b"$" or ser.read(1) != b"M" or ser.read(1) != b"<":
        return None
    size_bytes = ser.read(1)
    cmd_bytes = ser.read(1)
    if not size_bytes or not cmd_bytes:
        return None
    size = size_bytes[0]
    cmd = cmd_bytes[0]
    data = ser.read(size)
    ser.read(1)  # checksum throwaway
    return cmd, data


def build_mapper(norm: Dict[str, Dict[str, float]], overrides: Optional[Dict] = None) -> Mapper:
    """Create a :class:`Mapper` with configuration overrides applied.

    ``overrides`` mirrors the structure of ``norm`` and allows the CLI wrappers
    to tweak ranges or slews without editing the base YAML. We merge into a new
    dictionary to keep the caller's config immutable.
    """

    merged = {key: dict(spec) for key, spec in norm.items()}
    if overrides:
        for key, values in overrides.items():
            merged.setdefault(key, {}).update(values)
    return Mapper(merged)


def update_state_from_msp(state: Dict[str, float], cmd: int, data: bytes) -> None:
    """Decode MSP payloads into the ``state`` dictionary.

    Only a handful of MSP commands are relevant for expressive control. This
    function pattern-matches the command ID, unpacks the payload, and stores the
    scaled values in-place.
    """

    if cmd == MSP_ATTITUDE and len(data) >= 6:
        roll, pitch, yaw = struct.unpack("<hhh", data[:6])
        state["roll"] = roll / 10.0
        state["pitch"] = pitch / 10.0
    elif cmd == MSP_RC and len(data) >= 16:
        channels = struct.unpack("<8H", data[:16])
        state["throttle"] = channels[2]
        state["yaw"] = (channels[3] - 1500) / 500.0 * 200.0
    elif cmd == MSP_ANALOG and len(data) >= 7:
        state["vbat"] = data[0] / 10.0
        state["rssi"] = data[3] if len(data) >= 5 else 100


def emit_state_cc(midi_out, mapper: Mapper, channel: int, state: Dict[str, float]) -> None:
    """Send the current ``state`` over MIDI CC messages.

    Each telemetry field is mapped through the ``Mapper`` and scaled to the
    canonical MIDI 0-127 range. We also emit a sustain-pedal style gate on CC64
    to let the patch know when the throttle is live (makes it easy to trigger
    envelopes or switch scenes).
    """

    for key, control in _CC_MAPPING.items():
        value = int(mapper.norm01(key, state[key]) * 127)
        midi_out.send(
            mido.Message("control_change", channel=channel, control=control, value=value)
        )
    gate = 127 if state["throttle"] > 1050 else 0
    midi_out.send(
        mido.Message("control_change", channel=channel, control=64, value=gate)
    )


def run_bridge(
    serial_port: str,
    midi_out,
    norm: Dict[str, Dict[str, float]],
    *,
    channel: int = 0,
    norm_overrides: Optional[Dict] = None,
    stop_event=None,
    poll_interval: float = 0.02,
    idle_sleep: float = 0.001,
) -> None:
    """Main pump: read MSP frames and burst out MIDI CC messages.

    Args:
        serial_port: Path to the serial device emitting MSP telemetry.
        midi_out: ``mido`` output object; anything with ``send()`` will do.
        norm: Normalization spec (usually ``config/multi.yaml``'s ``norm`` key).
        channel: Zero-based MIDI channel number.
        norm_overrides: Optional nested dict of per-parameter tweaks.
        stop_event: Optional threading event that can be toggled to exit cleanly.
        poll_interval: Minimum seconds between MIDI bursts.
        idle_sleep: Seconds to nap when no MSP frame is available.
    """

    mapper = build_mapper(norm, norm_overrides)
    state = dict(_STATE_TEMPLATE)
    with serial.Serial(serial_port, 115200, timeout=0.01) as ser:  # type: ignore[name-defined]
        last_emit = 0.0
        while True:
            if stop_event is not None and stop_event.is_set():
                return
            frame = read_msp_frame(ser)
            if frame is None:
                # No complete frame ready—back off briefly to avoid hogging CPU.
                time.sleep(idle_sleep)
                continue
            cmd, data = frame
            # Fold the new reading into our scratch state buffer.
            update_state_from_msp(state, cmd, data)
            now = time.time()
            if now - last_emit > poll_interval:
                # Time to publish! Each burst covers every tracked CC.
                emit_state_cc(midi_out, mapper, channel, state)
                last_emit = now

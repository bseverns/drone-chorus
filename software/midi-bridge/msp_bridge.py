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

from __future__ import annotations

import struct
import time
from typing import Any, Callable, Dict, Optional, Tuple

import mido
import serial

# -- MSP command identifiers -------------------------------------------------
# These numeric IDs are defined by the MSP spec. We pull out only the ones we
# need; think of them as opcodes that label the payload format.
MSP_ATTITUDE = 108
MSP_RC = 105
MSP_ALTITUDE = 109
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
    "throttle": 1000.0,
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
    data = b""
    # Walk the payload in a loop so a mid-frame timeout doesn't desync us by
    # eating the checksum; we want to bail early and let the caller retry.
    while len(data) < size:
        chunk = ser.read(size - len(data))
        if not chunk:
            return None
        data += chunk

    if not ser.read(1):  # checksum throwaway
        return None
    return cmd, data


def merge_norm_specs(
    norm: Dict[str, Dict[str, float]], overrides: Optional[Dict[str, Dict[str, float]]] = None
) -> Dict[str, Dict[str, float]]:
    """Merge base normalization specs with optional overrides."""

    merged = {key: dict(spec) for key, spec in norm.items()}
    if overrides:
        for key, values in overrides.items():
            merged.setdefault(key, {}).update(values)
    return merged


def build_mapper(norm: Dict[str, Dict[str, float]], overrides: Optional[Dict] = None) -> Mapper:
    """Create a :class:`Mapper` with configuration overrides applied.

    ``overrides`` mirrors the structure of ``norm`` and allows the CLI wrappers
    to tweak ranges or slews without editing the base YAML. We merge into a new
    dictionary to keep the caller's config immutable.
    """

    return Mapper(merge_norm_specs(norm, overrides))


SignalHandler = Callable[[Dict[str, float], bytes], None]


def _build_custom_msp_handler(signal_key: str, spec: Dict[str, Any]) -> Tuple[int, SignalHandler]:
    """Compile a declarative MSP extraction rule into a callable.

    Expected schema:
    ``{"cmd": 123, "format": "<hh", "index": 0, "byte_offset": 0,
    "scale": 1.0, "offset": 0.0, "clamp": [lo, hi]}``.
    """

    if "cmd" not in spec or "format" not in spec:
        raise ValueError(f"signals.{signal_key}.msp requires 'cmd' and 'format'")

    cmd = int(spec["cmd"])
    fmt = str(spec["format"])
    index = int(spec.get("index", 0))
    byte_offset = int(spec.get("byte_offset", 0))
    scale = float(spec.get("scale", 1.0))
    offset = float(spec.get("offset", 0.0))
    clamp_spec = spec.get("clamp")
    clamp_range: Optional[Tuple[float, float]] = None
    if clamp_spec is not None:
        if not isinstance(clamp_spec, (list, tuple)) or len(clamp_spec) != 2:
            raise ValueError(f"signals.{signal_key}.msp.clamp must be [min, max]")
        clamp_range = (float(clamp_spec[0]), float(clamp_spec[1]))

    size = struct.calcsize(fmt)

    def handler(state: Dict[str, float], payload: bytes) -> None:
        if len(payload) < byte_offset + size:
            return
        values = struct.unpack(fmt, payload[byte_offset : byte_offset + size])
        if not values or index < 0 or index >= len(values):
            return
        value = float(values[index]) * scale + offset
        if clamp_range is not None:
            value = clamp(value, clamp_range[0], clamp_range[1])
        state[signal_key] = value

    return cmd, handler


def _chain_handlers(first: SignalHandler, second: SignalHandler) -> SignalHandler:
    def chained(state: Dict[str, float], payload: bytes) -> None:
        first(state, payload)
        second(state, payload)

    return chained


def build_signal_schema(
    signals: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Tuple[Dict[str, float], Dict[str, int], Dict[int, SignalHandler]]:
    """Build state defaults, CC map, and extra MSP handlers from config.

    The optional ``signals`` mapping lets users add or remap fields without
    editing this module. Any signal may define:

    - ``cc``: MIDI controller number
    - ``default``: startup state value
    - ``msp``: declarative extraction rule for arbitrary MSP payloads
    """

    state_template = dict(_STATE_TEMPLATE)
    cc_mapping = dict(_CC_MAPPING)
    handlers: Dict[int, SignalHandler] = {}

    if not signals:
        return state_template, cc_mapping, handlers

    if not isinstance(signals, dict):
        raise ValueError("signals config must be a mapping")

    for key, spec in signals.items():
        if not isinstance(spec, dict):
            raise ValueError(f"signals.{key} must be a mapping")
        if "default" in spec:
            state_template[key] = float(spec["default"])
        elif key not in state_template:
            state_template[key] = 0.0

        if "cc" in spec:
            cc_mapping[key] = int(spec["cc"])
        elif key not in cc_mapping:
            raise ValueError(f"signals.{key} must define 'cc' for new fields")

        custom_msp = spec.get("msp")
        if custom_msp is not None:
            if not isinstance(custom_msp, dict):
                raise ValueError(f"signals.{key}.msp must be a mapping")
            cmd, handler = _build_custom_msp_handler(key, custom_msp)
            if cmd in handlers:
                handlers[cmd] = _chain_handlers(handlers[cmd], handler)
            else:
                handlers[cmd] = handler

    return state_template, cc_mapping, handlers


def build_altitude_helpers(
    *, time_source: Callable[[], float] = time.time
) -> Tuple[
    Callable[[Dict[str, float], bytes], None],
    Callable[[Dict[str, float]], None],
]:
    """Return ``(decode_altitude, inject_altitude)`` helpers with shared state."""

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
        last_altitude_update = time_source()

    def inject_altitude(state: Dict[str, float]) -> None:
        """Ensure ``state['altitude']`` keeps moving even without baro data."""

        nonlocal last_altitude_update, last_altitude_m
        now = time_source()
        if now - last_altitude_update > 1.0:
            normalized = (state.get("throttle", 1000.0) - 1000.0) / 1000.0
            normalized = clamp(normalized, 0.0, 1.0)
            state["altitude"] = normalized * 3.0
        else:
            state["altitude"] = last_altitude_m

    return decode_altitude, inject_altitude


def build_altitude_consumers(
    *, time_source: Callable[[], float] = time.time
) -> Tuple[Callable[[Dict[str, float]], None], Dict[int, Callable[[Dict[str, float], bytes], None]]]:
    """Package altitude helpers for easy use in bridge callers.

    The CLI entrypoints both need the same combo: a state hook that injects a
    fallback ramp when barometer data disappears, and an MSP handler to decode
    ``MSP_ALTITUDE`` payloads when they *do* show up. Returning them together
    keeps tests and consumers aligned on the intended behavior.
    """

    decode_altitude, inject_altitude = build_altitude_helpers(time_source=time_source)
    return inject_altitude, {MSP_ALTITUDE: decode_altitude}


def update_state_from_msp(state: Dict[str, float], cmd: int, data: bytes) -> None:
    """Decode MSP payloads into the ``state`` dictionary.

    Only a handful of MSP commands are relevant for expressive control. This
    function pattern-matches the command ID, unpacks the payload, and stores the
    scaled values in-place.
    """

    if cmd == MSP_ATTITUDE and len(data) >= 6:
        roll, pitch, _yaw = struct.unpack("<hhh", data[:6])
        state["roll"] = roll / 10.0
        state["pitch"] = pitch / 10.0
    elif cmd == MSP_RC and len(data) >= 16:
        channels = struct.unpack("<8H", data[:16])
        state["throttle"] = float(channels[2])
        state["yaw"] = (channels[3] - 1500) / 500.0 * 200.0
    elif cmd == MSP_ALTITUDE and len(data) >= 4:
        altitude_cm = struct.unpack("<i", data[:4])[0]
        state["altitude"] = altitude_cm / 100.0
    elif cmd == MSP_ANALOG and len(data) >= 7:
        state["vbat"] = data[0] / 10.0
        state["rssi"] = float(data[3] if len(data) >= 5 else 100)


def emit_state_cc(
    midi_out,
    mapper: Mapper,
    channel: int,
    state: Dict[str, float],
    *,
    cc_mapping: Optional[Dict[str, int]] = None,
    gate_threshold: float = 1050.0,
) -> None:
    """Send the current ``state`` over MIDI CC messages.

    Each telemetry field is mapped through the ``Mapper`` and scaled to the
    canonical MIDI 0-127 range. We also emit a sustain-pedal style gate on CC64
    to let the patch know when the throttle is live (makes it easy to trigger
    envelopes or switch scenes).
    """

    active_cc = cc_mapping or _CC_MAPPING
    for key, control in active_cc.items():
        if key not in state:
            continue
        value = int(mapper.norm01(key, state[key]) * 127)
        midi_out.send(
            mido.Message("control_change", channel=channel, control=control, value=value)
        )
    gate = 127 if state.get("throttle", 0.0) > gate_threshold else 0
    midi_out.send(
        mido.Message("control_change", channel=channel, control=64, value=gate)
    )


def merge_state_handlers(
    base: Optional[Dict[int, SignalHandler]], extra: Optional[Dict[int, SignalHandler]]
) -> Dict[int, SignalHandler]:
    """Merge MSP command handlers, chaining handlers that share a command."""

    merged: Dict[int, SignalHandler] = {}
    for source in (base or {}, extra or {}):
        for cmd, handler in source.items():
            if cmd in merged:
                merged[cmd] = _chain_handlers(merged[cmd], handler)
            else:
                merged[cmd] = handler
    return merged


def run_bridge(
    serial_port: str,
    midi_out,
    norm: Dict[str, Dict[str, float]],
    *,
    channel: int = 0,
    norm_overrides: Optional[Dict[str, Dict[str, float]]] = None,
    stop_event=None,
    poll_interval: float = 0.02,
    idle_sleep: float = 0.001,
    state_hook: Optional[Callable[[Dict[str, float]], None]] = None,
    extra_state_handlers: Optional[Dict[int, SignalHandler]] = None,
    state_template: Optional[Dict[str, float]] = None,
    cc_mapping: Optional[Dict[str, int]] = None,
    throttle_limit: Optional[float] = None,
    estop_hook: Optional[Callable[[], bool]] = None,
    gate_threshold: float = 1050.0,
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
        state_hook: Optional callback to mutate ``state`` before emitting CCs.
        extra_state_handlers: Optional MSP command → handler map for decoding
            telemetry beyond the built-in trio (attitude, RC, analog).
        state_template: Optional initial state values keyed by signal name.
        cc_mapping: Optional MIDI CC map keyed by signal name.
        throttle_limit: Optional max throttle (1000-2000) applied before mapping.
        estop_hook: Optional callback that returns ``True`` when E-stop is active.
        gate_threshold: Throttle threshold used for CC64 gate emission.
    """

    merged_norm = merge_norm_specs(norm, norm_overrides)
    mapper = Mapper(merged_norm)
    active_state_template = dict(state_template or _STATE_TEMPLATE)
    active_cc_mapping = dict(cc_mapping or _CC_MAPPING)

    missing_norm = [key for key in active_cc_mapping if key not in merged_norm]
    if missing_norm:
        raise ValueError(
            f"Normalization config missing keys for CC mapping: {', '.join(sorted(missing_norm))}"
        )

    if throttle_limit is not None:
        throttle_limit = clamp(float(throttle_limit), 1000.0, 2000.0)

    state = dict(active_state_template)
    handlers = extra_state_handlers or {}

    with serial.Serial(serial_port, 115200, timeout=0.01) as ser:  # type: ignore[name-defined]
        last_emit = 0.0
        while True:
            if stop_event is not None and stop_event.is_set():
                return
            frame = read_msp_frame(ser)
            now = time.time()
            estop_active = bool(estop_hook is not None and estop_hook())

            if frame is not None:
                cmd, data = frame
                # Fold the new reading into our scratch state buffer.
                update_state_from_msp(state, cmd, data)
                if cmd in handlers:
                    handlers[cmd](state, data)

                if throttle_limit is not None and "throttle" in state:
                    state["throttle"] = min(float(state["throttle"]), throttle_limit)

                if state_hook is not None:
                    state_hook(state)

            if estop_active:
                for key, default in active_state_template.items():
                    state[key] = default
                state["throttle"] = 1000.0

            if now - last_emit > poll_interval and (frame is not None or estop_active):
                # Time to publish! Each burst covers every tracked CC.
                emit_state_cc(
                    midi_out,
                    mapper,
                    channel,
                    state,
                    cc_mapping=active_cc_mapping,
                    gate_threshold=gate_threshold,
                )
                last_emit = now

            if frame is None:
                # No complete frame ready—back off briefly to avoid hogging CPU.
                time.sleep(idle_sleep)

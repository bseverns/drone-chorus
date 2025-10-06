"""Shared MSP-to-MIDI bridge utilities for Drone Chorus."""

import struct
import time
from typing import Dict, Optional

import mido
import serial

MSP_ATTITUDE = 108
MSP_RC = 105
MSP_ANALOG = 110

_STATE_TEMPLATE = {
    "roll": 0.0,
    "pitch": 0.0,
    "yaw": 0.0,
    "altitude": 0.0,
    "rssi": 100.0,
    "vbat": 4.0,
    "throttle": 1000,
}

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
    return max(lo, min(hi, x))


class Smoother:
    def __init__(self, slew: float = 0.05) -> None:
        self._slew = slew
        self._y: Optional[float] = None

    def step(self, x: float) -> float:
        if self._y is None:
            self._y = x
            return x
        delta = clamp(x - self._y, -self._slew, self._slew)
        self._y += delta
        return self._y


class Mapper:
    def __init__(self, norm: Dict[str, Dict[str, float]]) -> None:
        self._norm = norm
        self._smoothers = {
            key: Smoother(spec.get("slew", 0.03)) for key, spec in norm.items()
        }

    def norm01(self, key: str, value: float) -> float:
        spec = self._norm[key]
        lo, hi = spec["min"], spec["max"]
        rng = hi - lo
        v = 0.0 if rng == 0 else (value - lo) / rng
        v = clamp(v, 0.0, 1.0)
        if spec.get("curve") == "expo":
            shaped = (abs(v - 0.5) * 2) ** 1.3
            shaped *= 1 if v >= 0.5 else -1
            v = shaped * 0.5 + 0.5
        return self._smoothers[key].step(v)


def read_msp_frame(ser) -> Optional[tuple]:
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
    merged = {key: dict(spec) for key, spec in norm.items()}
    if overrides:
        for key, values in overrides.items():
            merged.setdefault(key, {}).update(values)
    return Mapper(merged)


def update_state_from_msp(state: Dict[str, float], cmd: int, data: bytes) -> None:
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
    mapper = build_mapper(norm, norm_overrides)
    state = dict(_STATE_TEMPLATE)
    with serial.Serial(serial_port, 115200, timeout=0.01) as ser:  # type: ignore[name-defined]
        last_emit = 0.0
        while True:
            if stop_event is not None and stop_event.is_set():
                return
            frame = read_msp_frame(ser)
            if frame is None:
                time.sleep(idle_sleep)
                continue
            cmd, data = frame
            update_state_from_msp(state, cmd, data)
            now = time.time()
            if now - last_emit > poll_interval:
                emit_state_cc(midi_out, mapper, channel, state)
                last_emit = now

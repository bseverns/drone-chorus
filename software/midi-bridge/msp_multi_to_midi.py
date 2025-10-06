#!/usr/bin/env python3
"""Bridge Betaflight MSP telemetry into MIDI CC streams for multiple drones.

This version cleans up the previous quick-and-dirty merge that left a pile of
inline statements and racey altitude handling.  The altitude logic now lives in
an explicit helper so we can reason about barometric freshness versus the
throttle-shaped proxy without juggling globals.  Smoothers keep musical gestures
alive even when telemetry burps.
"""

from __future__ import annotations

import struct
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Iterable, Mapping, Optional

import mido
import serial
import yaml


MSP_ATTITUDE = 108
MSP_RC = 105
MSP_ALTITUDE = 109
MSP_ANALOG = 110


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class Smoother:
    """Simple slew limiter used across signals to tame zipper noise."""

    def __init__(self, slew: float = 0.05) -> None:
        self.slew = slew
        self._value: Optional[float] = None

    def step(self, target: float) -> float:
        if self._value is None:
            self._value = target
            return target

        delta = clamp(target - self._value, -self.slew, self.slew)
        self._value += delta
        return self._value


@dataclass
class Mapper:
    """Convert raw telemetry values into 0..1 for MIDI CC."""

    norm: Mapping[str, Mapping[str, float]]
    _smoothers: Dict[str, Smoother] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for key, spec in self.norm.items():
            slew = float(spec.get("slew", 0.03))
            self._smoothers[key] = Smoother(slew)

    def norm01(self, key: str, value: float) -> float:
        spec = self.norm[key]
        low, high = float(spec["min"]), float(spec["max"])
        if high == low:
            normalised = 0.0
        else:
            normalised = (value - low) / (high - low)

        normalised = clamp(normalised, 0.0, 1.0)

        if spec.get("curve") == "expo":
            # A tiny punk-rock curve: more sensitive near the edges without
            # going into full log-land.
            shifted = (abs(normalised - 0.5) * 2) ** 1.3
            normalised = (shifted if normalised >= 0.5 else -shifted) * 0.5 + 0.5

        return self._smoothers[key].step(normalised)


class AltitudeTracker:
    """Blend barometric altitude with a throttle-derived proxy when stale."""

    def __init__(
        self,
        *,
        range_min: float,
        range_max: float,
        stale_after: float = 1.5,
        proxy_blend: float = 0.3,
    ) -> None:
        self.range_min = range_min
        self.range_max = range_max
        self.stale_after = stale_after
        self.proxy_blend = proxy_blend

        self._last_baro: Optional[float] = None
        self._last_baro_timestamp: float = 0.0
        self._current: float = range_min

    def _throttle_proxy(self, throttle_value: float) -> float:
        ratio = clamp((throttle_value - 1000.0) / 1000.0, 0.0, 1.0)
        return self.range_min + ratio * (self.range_max - self.range_min)

    def push_baro(self, altitude_m: float, *, timestamp: float) -> None:
        self._last_baro = altitude_m
        self._last_baro_timestamp = timestamp
        self._current = altitude_m

    def value(self, throttle_value: float, *, timestamp: float) -> float:
        baro_is_fresh = (
            self._last_baro is not None
            and timestamp - self._last_baro_timestamp <= self.stale_after
        )

        if baro_is_fresh:
            # Stick to the barometric truth while it's fresh.
            self._current = self._last_baro  # type: ignore[assignment]
        else:
            # Ease toward the throttle proxy so pads stay alive when MSP mutes.
            proxy = self._throttle_proxy(throttle_value)
            self._current = (1.0 - self.proxy_blend) * self._current + self.proxy_blend * proxy

        return self._current


def read_msp_frame(port: serial.Serial) -> tuple[Optional[int], bytes]:
    if port.read(1) != b"$" or port.read(1) != b"M" or port.read(1) != b"<":
        return None, b""

    size = port.read(1)
    if not size:
        return None, b""

    payload_len = size[0]
    cmd = port.read(1)
    if not cmd:
        return None, b""

    payload = port.read(payload_len)
    _checksum = port.read(1)
    return cmd[0], payload


def _iter_cc_map() -> Iterable[tuple[str, int]]:
    return (
        ("roll", 14),
        ("pitch", 15),
        ("yaw", 16),
        ("altitude", 17),
        ("rssi", 18),
        ("vbat", 19),
        ("throttle", 20),
    )


def worker(drone_cfg: Mapping[str, object], base_norm: Mapping[str, Mapping[str, float]], midi_out: mido.ports.BaseOutput):
    norm: Dict[str, Dict[str, float]] = {key: dict(value) for key, value in base_norm.items()}
    for key, override in (drone_cfg.get("norm_overrides") or {}).items():
        norm[key].update(override)

    mapper = Mapper(norm)
    channel = int(drone_cfg["channel"]) - 1

    altitude_spec = norm["altitude"]
    altitude_tracker = AltitudeTracker(
        range_min=float(altitude_spec["min"]),
        range_max=float(altitude_spec["max"]),
    )

    state = {
        "roll": 0.0,
        "pitch": 0.0,
        "yaw": 0.0,
        "altitude": altitude_tracker.range_min,
        "rssi": 100.0,
        "vbat": 4.0,
        "throttle": 1000.0,
    }

    serial_path = str(drone_cfg["serial"])
    with serial.Serial(serial_path, 115200, timeout=0.01) as port:
        last_emit = 0.0

        while True:
            cmd, payload = read_msp_frame(port)
            now = time.time()

            if cmd is None:
                time.sleep(0.001)
                state["altitude"] = altitude_tracker.value(state["throttle"], timestamp=now)
                continue

            if cmd == MSP_ATTITUDE and len(payload) >= 6:
                roll, pitch, _yaw = struct.unpack("<hhh", payload[:6])
                state["roll"] = roll / 10.0
                state["pitch"] = pitch / 10.0

            elif cmd == MSP_RC and len(payload) >= 16:
                channels = struct.unpack("<8H", payload[:16])
                throttle = float(channels[2])
                state["throttle"] = throttle
                yaw_channel = float(channels[3])
                state["yaw"] = (yaw_channel - 1500.0) / 500.0 * 200.0

            elif cmd == MSP_ALTITUDE and len(payload) >= 6:
                altitude_cm, _vario = struct.unpack("<ih", payload[:6])
                altitude_m = altitude_cm / 100.0
                altitude_tracker.push_baro(altitude_m, timestamp=now)
                state["altitude"] = altitude_m

            elif cmd == MSP_ANALOG and payload:
                state["vbat"] = payload[0] / 10.0
                if len(payload) >= 5:
                    state["rssi"] = float(payload[3])

            # Even if we just processed a frame we still want the fallback tick
            state["altitude"] = altitude_tracker.value(state["throttle"], timestamp=now)

            if now - last_emit < 0.02:
                continue

            for key, cc in _iter_cc_map():
                cc_value = int(mapper.norm01(key, state[key]) * 127)
                midi_out.send(
                    mido.Message("control_change", channel=channel, control=cc, value=cc_value)
                )

            gate_value = 127 if state["throttle"] > 1050.0 else 0
            midi_out.send(mido.Message("control_change", channel=channel, control=64, value=gate_value))
            last_emit = now


def main() -> None:
    with open("config/multi.yaml", "r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    try:
        midi_out = mido.open_output(config["midi"]["port_name"], virtual=True)
    except Exception:
        midi_out = mido.open_output()

    threads = []
    for drone in config["drones"]:
        thread = threading.Thread(
            target=worker,
            args=(drone, config["norm"], midi_out),
            daemon=True,
        )
        thread.start()
        threads.append(thread)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

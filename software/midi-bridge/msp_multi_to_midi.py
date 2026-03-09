#!/usr/bin/env python3
"""Spin up multiple MSP->MIDI bridges at once.

Where :mod:`msp_to_midi` handles a solo craft, this module is the ensemble
director. It reads the multi-drone YAML, opens a shared MIDI port, and spawns a
thread per drone so that every craft gets its own MIDI channel. Comments lean
into "workbench" mode so students can trace how the concurrency pieces fit
together.
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import yaml

from midi_ports import open_midi_output as open_shared_midi_output
from msp_bridge import (
    build_altitude_consumers,
    build_signal_schema,
    merge_state_handlers,
    run_bridge,
)


def build_estop_checker(path: Optional[str]) -> Optional[Callable[[], bool]]:
    if not path:
        return None
    estop_path = Path(path)

    def estop_is_active() -> bool:
        return estop_path.exists()

    return estop_is_active


def worker(
    drone: Dict[str, Any],
    norm: Dict[str, Dict[str, float]],
    midi_out,
    stop_event: threading.Event,
    *,
    poll_interval: float,
    idle_sleep: float,
    throttle_limit: Optional[float],
    gate_threshold: float,
    estop_hook: Optional[Callable[[], bool]],
    state_template: Dict[str, float],
    cc_mapping: Dict[str, int],
    base_handlers: Dict[int, Callable[[Dict[str, float], bytes], None]],
) -> None:
    """Bridge a single drone's MSP stream inside a background thread."""

    # Altitude strategy: prefer MSP_ALTITUDE (baro / fusion estimate) and fall back
    # to a throttle-derived ramp if the craft never publishes barometric data.
    inject_altitude, altitude_handlers = build_altitude_consumers()
    merged_handlers = merge_state_handlers(altitude_handlers, base_handlers)

    run_bridge(
        drone["serial"],
        midi_out,
        norm,
        channel=drone["channel"] - 1,
        norm_overrides=drone.get("norm_overrides"),
        stop_event=stop_event,
        poll_interval=float(drone.get("poll_interval", poll_interval)),
        idle_sleep=float(drone.get("idle_sleep", idle_sleep)),
        state_hook=inject_altitude,
        extra_state_handlers=merged_handlers,
        state_template=state_template,
        cc_mapping=cc_mapping,
        throttle_limit=drone.get("throttle_limit", throttle_limit),
        estop_hook=build_estop_checker(drone.get("estop_file")) or estop_hook,
        gate_threshold=float(drone.get("gate_threshold", gate_threshold)),
    )


def open_midi_output(port_name: str):
    """Open configured MIDI output; warn when we must fall back."""

    return open_shared_midi_output(
        port_name,
        virtual=True,
        fallback_to_default=True,
        on_fallback=lambda message: print(f"[midi-warning] {message}", file=sys.stderr),
    )


def main() -> None:
    """Load configuration, launch worker threads, and keep them alive."""

    with open("config/multi.yaml", "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}

    midi_out = open_midi_output(str(cfg["midi"]["port_name"]))

    runtime = cfg.get("runtime", {})
    safety = cfg.get("safety", {})
    poll_interval = float(runtime.get("poll_interval", 0.02))
    idle_sleep = float(runtime.get("idle_sleep", 0.001))
    throttle_limit = safety.get("throttle_limit")
    gate_threshold = float(safety.get("gate_threshold", 1050.0))
    estop_hook = build_estop_checker(safety.get("estop_file"))

    state_template, cc_mapping, schema_handlers = build_signal_schema(cfg.get("signals"))

    stop_event = threading.Event()
    threads = []
    for drone in cfg["drones"]:
        thread = threading.Thread(
            target=worker,
            args=(drone, cfg["norm"], midi_out, stop_event),
            kwargs={
                "poll_interval": poll_interval,
                "idle_sleep": idle_sleep,
                "throttle_limit": throttle_limit,
                "gate_threshold": gate_threshold,
                "estop_hook": estop_hook,
                "state_template": state_template,
                "cc_mapping": cc_mapping,
                "base_handlers": schema_handlers,
            },
            daemon=True,
        )
        thread.start()
        threads.append(thread)

    try:
        while True:
            # Sleep instead of busy-waiting; the workers do the realtime stuff.
            time.sleep(1)
    except KeyboardInterrupt:
        stop_event.set()
        for thread in threads:
            thread.join(timeout=0.5)


if __name__ == "__main__":
    main()

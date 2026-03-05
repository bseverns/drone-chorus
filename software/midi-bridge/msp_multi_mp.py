#!/usr/bin/env python3
"""Multiprocessing MSP->MIDI bridge prototype.

This launcher is an experimental alternative to ``msp_multi_to_midi.py`` for
higher drone counts and/or noisier telemetry rates. Each drone gets a dedicated
worker process that parses MSP frames and publishes state snapshots to a shared
queue. The parent process owns MIDI output and emits CC values for every drone.

Design goals:

1. Keep serial decode work off the main interpreter thread.
2. Keep MIDI output single-owner to avoid concurrent send() contention.
3. Preserve existing norm/safety/signal-schema behavior from config/multi.yaml.
"""

from __future__ import annotations

import argparse
import multiprocessing as mp
from queue import Empty, Full
import signal
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

import mido
import serial
import yaml

from msp_bridge import (
    build_altitude_consumers,
    build_mapper,
    build_signal_schema,
    clamp,
    emit_state_cc,
    merge_state_handlers,
    read_msp_frame,
    update_state_from_msp,
)

StateSnapshot = Dict[str, float]


def build_estop_checker(path: Optional[str]) -> Optional[Callable[[], bool]]:
    """Return a callback that reports whether the E-stop latch is active."""

    if not path:
        return None
    estop_path = Path(path)

    def estop_is_active() -> bool:
        return estop_path.exists()

    return estop_is_active


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prototype process-based launcher for multi-drone MSP->MIDI"
    )
    parser.add_argument(
        "--config",
        default="config/multi.yaml",
        help="Path to multi-drone YAML config (default: config/multi.yaml)",
    )
    parser.add_argument(
        "--queue-size",
        type=int,
        default=2048,
        help="Max in-flight worker->parent state messages (default: 2048)",
    )
    return parser.parse_args()


def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}
    if not isinstance(cfg, dict):
        raise ValueError("Config must be a mapping")
    return cfg


def _queue_put_drop_oldest(queue: mp.Queue, message: Tuple[str, Any]) -> None:
    """Try to enqueue without blocking; drop oldest entries under pressure."""

    try:
        queue.put_nowait(message)
        return
    except Full:
        pass

    try:
        queue.get_nowait()
    except Empty:
        return

    try:
        queue.put_nowait(message)
    except Full:
        return


def drone_worker(
    drone: Dict[str, Any],
    *,
    state_template: Dict[str, float],
    schema_handlers: Dict[int, Callable[[StateSnapshot, bytes], None]],
    runtime: Dict[str, Any],
    safety: Dict[str, Any],
    out_queue: mp.Queue,
    stop_event: mp.Event,
) -> None:
    """Decode MSP for one drone process and publish state snapshots."""

    drone_name = str(drone.get("name") or f"drone{int(drone['channel']):02d}")
    poll_interval = float(drone.get("poll_interval", runtime.get("poll_interval", 0.02)))
    idle_sleep = float(drone.get("idle_sleep", runtime.get("idle_sleep", 0.001)))
    publish_interval = float(drone.get("publish_interval", poll_interval))

    throttle_limit = drone.get("throttle_limit", safety.get("throttle_limit"))
    if throttle_limit is not None:
        throttle_limit = clamp(float(throttle_limit), 1000.0, 2000.0)

    inject_altitude, altitude_handlers = build_altitude_consumers()
    handlers = merge_state_handlers(altitude_handlers, schema_handlers)

    state = dict(state_template)
    serial_port = str(drone["serial"])

    try:
        with serial.Serial(serial_port, 115200, timeout=0.01) as ser:  # type: ignore[name-defined]
            last_publish = 0.0
            while not stop_event.is_set():
                frame = read_msp_frame(ser)
                if frame is None:
                    time.sleep(idle_sleep)
                    continue

                cmd, data = frame
                update_state_from_msp(state, cmd, data)
                if cmd in handlers:
                    handlers[cmd](state, data)

                if throttle_limit is not None and "throttle" in state:
                    state["throttle"] = min(float(state["throttle"]), throttle_limit)

                inject_altitude(state)
                now = time.time()
                if now - last_publish >= publish_interval:
                    _queue_put_drop_oldest(
                        out_queue,
                        ("state", {"drone": drone_name, "state": dict(state), "ts": now}),
                    )
                    last_publish = now
    except Exception as exc:  # pragma: no cover - realtime/runtime path
        _queue_put_drop_oldest(
            out_queue,
            (
                "error",
                {
                    "drone": drone_name,
                    "serial": serial_port,
                    "error": f"{type(exc).__name__}: {exc}",
                },
            ),
        )
    finally:  # pragma: no cover - realtime/runtime path
        _queue_put_drop_oldest(out_queue, ("stopped", {"drone": drone_name, "ts": time.time()}))


def _open_midi_output(port_name: str):
    try:
        return mido.open_output(port_name, virtual=True)
    except Exception:
        return mido.open_output()


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)

    runtime = cfg.get("runtime", {})
    safety = cfg.get("safety", {})
    drones = cfg.get("drones") or []
    if not drones:
        raise ValueError("Config must define at least one drone in 'drones'")

    state_template, cc_mapping, schema_handlers = build_signal_schema(cfg.get("signals"))

    midi_port = str((cfg.get("midi") or {}).get("port_name", "DroneChorus"))
    midi_out = _open_midi_output(midi_port)

    ctx = mp.get_context("spawn")
    queue: mp.Queue = ctx.Queue(maxsize=max(64, int(args.queue_size)))
    stop_event = ctx.Event()

    global_estop = build_estop_checker(safety.get("estop_file"))

    drone_runtime: Dict[str, Dict[str, Any]] = {}
    workers = []

    for drone in drones:
        drone_name = str(drone.get("name") or f"drone{int(drone['channel']):02d}")
        norm_overrides = drone.get("norm_overrides")
        mapper = build_mapper(cfg["norm"], norm_overrides)

        poll_interval = float(drone.get("poll_interval", runtime.get("poll_interval", 0.02)))
        gate_threshold = float(drone.get("gate_threshold", safety.get("gate_threshold", 1050.0)))
        drone_estop = build_estop_checker(drone.get("estop_file"))

        drone_runtime[drone_name] = {
            "channel": max(0, int(drone["channel"]) - 1),
            "mapper": mapper,
            "state": dict(state_template),
            "last_emit": 0.0,
            "poll_interval": poll_interval,
            "gate_threshold": gate_threshold,
            "dirty": False,
            "last_estop": False,
            "estop_check": drone_estop,
        }

        process = ctx.Process(
            target=drone_worker,
            kwargs={
                "drone": drone,
                "state_template": state_template,
                "schema_handlers": schema_handlers,
                "runtime": runtime,
                "safety": safety,
                "out_queue": queue,
                "stop_event": stop_event,
            },
            daemon=True,
        )
        process.start()
        workers.append(process)

    def request_stop(_signum=None, _frame=None) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    try:
        while not stop_event.is_set():
            now = time.time()

            try:
                msg_type, payload = queue.get(timeout=0.02)
            except Empty:
                msg_type, payload = None, None

            if msg_type == "state" and payload is not None:
                drone_name = payload["drone"]
                if drone_name in drone_runtime:
                    drone_runtime[drone_name]["state"] = payload["state"]
                    drone_runtime[drone_name]["dirty"] = True
            elif msg_type == "error" and payload is not None:
                print(
                    f"[worker-error] {payload['drone']} {payload['serial']}: {payload['error']}",
                    flush=True,
                )
            elif msg_type == "stopped" and payload is not None:
                print(f"[worker-stopped] {payload['drone']}", flush=True)

            for name, data in drone_runtime.items():
                local_estop_fn = data.get("estop_check")
                local_estop = bool(local_estop_fn and local_estop_fn())
                estop_active = local_estop or bool(global_estop and global_estop())
                estop_changed = estop_active != bool(data.get("last_estop", False))

                should_emit = (now - float(data["last_emit"])) >= float(data["poll_interval"])
                if not should_emit:
                    continue
                if not bool(data["dirty"]) and not estop_changed:
                    continue

                if estop_active:
                    emit_state = dict(state_template)
                    emit_state["throttle"] = 1000.0
                else:
                    emit_state = data["state"]

                emit_state_cc(
                    midi_out,
                    data["mapper"],
                    int(data["channel"]),
                    emit_state,
                    cc_mapping=cc_mapping,
                    gate_threshold=float(data["gate_threshold"]),
                )
                data["last_emit"] = now
                data["dirty"] = False
                data["last_estop"] = estop_active

            if any(not process.is_alive() for process in workers):
                dead = [str(process.pid) for process in workers if not process.is_alive()]
                print(f"[warning] worker process exited unexpectedly: {', '.join(dead)}", flush=True)
                stop_event.set()

    finally:
        stop_event.set()
        for process in workers:
            process.join(timeout=1.5)
            if process.is_alive():
                process.terminate()
        if hasattr(midi_out, "close"):
            midi_out.close()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import threading
import time
from typing import Any, Dict

import mido
import yaml

from msp_bridge import run_bridge


def worker(
    drone: Dict[str, Any],
    norm: Dict[str, Dict[str, float]],
    midi_out,
    stop_event: threading.Event,
) -> None:
    run_bridge(
        drone["serial"],
        midi_out,
        norm,
        channel=drone["channel"] - 1,
        norm_overrides=drone.get("norm_overrides"),
        stop_event=stop_event,
    )


def main() -> None:
    with open("config/multi.yaml", "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    try:
        midi_out = mido.open_output(cfg["midi"]["port_name"], virtual=True)
    except Exception:
        midi_out = mido.open_output()

    stop_event = threading.Event()
    threads = []
    for drone in cfg["drones"]:
        thread = threading.Thread(
            target=worker,
            args=(drone, cfg["norm"], midi_out, stop_event),
            daemon=True,
        )
        thread.start()
        threads.append(thread)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_event.set()
        for thread in threads:
            thread.join(timeout=0.5)


if __name__ == "__main__":
    main()

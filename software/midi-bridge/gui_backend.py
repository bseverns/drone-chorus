"""GUI-friendly backend for MSP→MIDI control with live monitoring.

This module keeps the realtime serial/MIDI work inside a testable Python class
so the PyQt front-end can stay focused on widgets. The design mirrors the
existing CLI bridges but exposes callbacks and reload hooks that a GUI can
listen to. Comments lean into "workbench" mode to demystify the realtime loop
for students poking around.
"""

from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from typing import Callable, Dict, Optional

import mido
import yaml

from midi_ports import open_midi_output as open_shared_midi_output
from msp_bridge import (
    build_altitude_consumers,
    build_mapper,
    clamp,
    read_msp_frame,
    update_state_from_msp,
)

try:  # optional dependency for the preview server
    import websockets
except Exception:  # pragma: no cover - runtime optional
    websockets = None


STATE_KEYS = ("roll", "pitch", "yaw", "altitude", "rssi", "vbat", "throttle")


@dataclass
class BridgeStatus:
    """Snapshot of the bridge's state for GUI consumption."""

    active_serial: Optional[str] = None
    midi_port: Optional[str] = None
    last_config: Optional[Path] = None
    last_error: Optional[str] = None
    config_notice: Optional[str] = None
    heartbeat_ts: float = 0.0
    cc_values: Dict[str, Dict[str, int]] = field(default_factory=dict)


class MonitoringMidiOut:
    """Proxy that mirrors CC traffic into a callback."""

    def __init__(self, midi_out, on_cc: Callable[[str, int, int], None], drone: str):
        self._midi_out = midi_out
        self._on_cc = on_cc
        self._drone = drone

    def send(self, message):
        self._midi_out.send(message)
        if message.type == "control_change":
            self._on_cc(self._drone, message.control, message.value)

    def close(self) -> None:
        if hasattr(self._midi_out, "close"):
            self._midi_out.close()


class WebMidiStreamer:
    """Minimal websocket broadcaster for CC snapshots."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        http_host: str = "127.0.0.1",
        http_port: int = 8080,
    ):
        self._host = host
        self._port = port
        self._http_host = http_host
        self._http_port = http_port
        self._server = None
        self._clients: set = set()
        self._thread: Optional[threading.Thread] = None
        self._loop = None
        self._http: Optional[ThreadingHTTPServer] = None
        self._http_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if websockets is None or self._thread:
            return
        import asyncio

        async def handler(ws, _path):
            self._clients.add(ws)
            try:
                await ws.wait_closed()
            finally:
                self._clients.discard(ws)

        async def run_server():
            async with websockets.serve(handler, self._host, self._port):
                await asyncio.Future()

        def runner():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(run_server())

        self._thread = threading.Thread(target=runner, daemon=True)
        self._thread.start()
        self._start_http()

    def stop(self) -> None:
        if self._loop:
            import asyncio

            self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread = None
        if self._http:
            self._http.shutdown()
            self._http.server_close()
            self._http = None
        if self._http_thread:
            self._http_thread.join(timeout=1)
            self._http_thread = None

    def broadcast(self, payload: Dict) -> None:
        if websockets is None or not self._clients or self._loop is None:
            return
        import asyncio

        async def _send():
            dead = []
            for client in list(self._clients):
                try:
                    await client.send(json.dumps(payload))
                except Exception:
                    dead.append(client)
            for client in dead:
                self._clients.discard(client)

        asyncio.run_coroutine_threadsafe(_send(), self._loop)

    def _start_http(self) -> None:
        html_path = Path(__file__).with_name("webmidi_preview.html")

        class Handler(BaseHTTPRequestHandler):  # pragma: no cover - tiny server
            def do_GET(self):
                if self.path in ("/", "/index.html"):
                    content = html_path.read_text(encoding="utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.send_header("Content-Length", str(len(content.encode("utf-8"))))
                    self.end_headers()
                    self.wfile.write(content.encode("utf-8"))
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, format, *args):  # noqa: A003
                return

        self._http = ThreadingHTTPServer((self._http_host, self._http_port), Handler)

        def run_server():
            assert self._http
            self._http.serve_forever()

        self._http_thread = threading.Thread(target=run_server, daemon=True)
        self._http_thread.start()


class BridgeWorker(threading.Thread):
    """Background thread that owns the MSP read loop and CC emission."""

    def __init__(
        self,
        serial_port: str,
        midi_out,
        norm: Dict[str, Dict[str, float]],
        *,
        channel: int = 0,
        on_cc: Optional[Callable[[str, int, int], None]] = None,
        on_heartbeat: Optional[Callable[[float], None]] = None,
        simulated: bool = False,
        drone_name: str = "drone01",
        poll_interval: float = 0.02,
        idle_sleep: float = 0.001,
    ) -> None:
        super().__init__(daemon=True)
        self.serial_port = serial_port
        self._mapper = build_mapper(norm)
        self._mapper_lock = threading.Lock()
        self.channel = channel
        self.stop_event = threading.Event()
        self._on_cc = on_cc
        self._on_heartbeat = on_heartbeat
        self._simulated = simulated
        self._drone_name = drone_name
        self._poll_interval = poll_interval
        self._idle_sleep = idle_sleep
        self._state = {key: 0.0 for key in STATE_KEYS}
        self._inject_altitude, self._extra_handlers = build_altitude_consumers()
        self._midi_out = MonitoringMidiOut(midi_out, self._push_cc, drone_name)

    def update_mapper(self, norm: Dict[str, Dict[str, float]]) -> None:
        with self._mapper_lock:
            self._mapper = build_mapper(norm)

    def stop(self) -> None:
        self.stop_event.set()

    def _push_cc(self, drone: str, control: int, value: int) -> None:
        if self._on_cc:
            self._on_cc(drone, control, value)

    def _emit_cc_burst(self) -> None:
        with self._mapper_lock:
            mapper = self._mapper
        gate = 127 if self._state.get("throttle", 0) > 1050 else 0
        for key, control in (
            ("roll", 14),
            ("pitch", 15),
            ("yaw", 16),
            ("altitude", 17),
            ("rssi", 18),
            ("vbat", 19),
            ("throttle", 20),
        ):
            value = int(mapper.norm01(key, self._state.get(key, 0.0)) * 127)
            self._midi_out.send(
                mido.Message(
                    "control_change", channel=self.channel, control=control, value=value
                )
            )
        self._midi_out.send(
            mido.Message("control_change", channel=self.channel, control=64, value=gate)
        )
        if self._on_heartbeat:
            self._on_heartbeat(time.time())

    def _run_simulated(self) -> None:
        start = time.time()
        while not self.stop_event.is_set():
            t = time.time() - start
            self._state["roll"] = math.sin(t) * 30
            self._state["pitch"] = math.cos(t * 0.7) * 30
            self._state["yaw"] = math.sin(t * 0.5) * 150
            self._state["altitude"] = (math.sin(t * 0.25) + 1) * 1.5
            self._state["rssi"] = clamp(80 + math.sin(t * 0.2) * 15, 0, 100)
            self._state["vbat"] = clamp(3.7 + math.sin(t * 0.1) * 0.1, 3.2, 4.2)
            self._state["throttle"] = clamp(1200 + math.sin(t * 1.5) * 200, 1000, 2000)
            self._emit_cc_burst()
            time.sleep(self._poll_interval)

    def run(self) -> None:  # pragma: no cover - realtime loop
        try:
            if self._simulated:
                self._run_simulated()
                return
            import serial

            with serial.Serial(self.serial_port, 115200, timeout=0.01) as ser:  # type: ignore[name-defined]
                last_emit = 0.0
                while not self.stop_event.is_set():
                    frame = read_msp_frame(ser)
                    if frame is None:
                        time.sleep(self._idle_sleep)
                        continue
                    cmd, data = frame
                    update_state_from_msp(self._state, cmd, data)
                    if cmd in self._extra_handlers:
                        self._extra_handlers[cmd](self._state, data)
                    self._inject_altitude(self._state)
                    now = time.time()
                    if now - last_emit > self._poll_interval:
                        self._emit_cc_burst()
                        last_emit = now
        except Exception:
            # Swallow exceptions so the GUI can report them instead of crashing the app.
            self.stop_event.set()
            raise
        finally:
            self._midi_out.close()


class BridgeBackend:
    """Coordinator that owns the worker thread and config lifecycle."""

    def __init__(self) -> None:
        self.status = BridgeStatus()
        self._worker: Optional[BridgeWorker] = None
        self._cc_cache: Dict[str, Dict[int, int]] = {}
        self._status_lock = threading.Lock()
        self._on_state = None
        self._web_streamer: Optional[WebMidiStreamer] = None

    def set_state_callback(self, fn: Callable[[BridgeStatus], None]) -> None:
        self._on_state = fn

    def _notify(self) -> None:
        if self._on_state:
            self._on_state(self.status)

    def _cc_listener(self, drone: str, control: int, value: int) -> None:
        with self._status_lock:
            cache = self._cc_cache.setdefault(drone, {})
            if cache.get(control) == value:
                return
            cache[control] = value
            self.status.cc_values = {
                name: {k: v for k, v in controls.items()}
                for name, controls in self._cc_cache.items()
            }
        if self._web_streamer:
            try:
                self._web_streamer.broadcast(self.status.cc_values)
            except Exception:
                pass
        self._notify()

    def _heartbeat(self, ts: float) -> None:
        self.status.heartbeat_ts = ts
        self._notify()

    def load_config(self, path: Path) -> Dict[str, Dict[str, float]]:
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        if not isinstance(data, dict):
            raise ValueError("Config must be a mapping or contain a 'norm' mapping")
        norm_block = data.get("norm")
        if norm_block is None:
            norm_block = data
        if not isinstance(norm_block, dict):
            raise ValueError("Config 'norm' block must be a mapping")
        missing = [key for key in STATE_KEYS if key not in norm_block]
        if missing:
            raise ValueError(f"Config missing keys: {', '.join(missing)}")
        cli_only_keys = [key for key in ("signals", "runtime", "safety", "drones", "midi") if key in data]
        if "norm" in data and cli_only_keys:
            self.status.config_notice = (
                "GUI applies only the 'norm' block. "
                f"CLI-only keys present: {', '.join(sorted(cli_only_keys))}."
            )
        else:
            self.status.config_notice = None
        self.status.last_config = path
        self.status.last_error = None
        self._notify()
        return norm_block

    def start(
        self,
        *,
        serial_port: str,
        midi_port: str,
        norm: Dict[str, Dict[str, float]],
        channel: int = 0,
        simulated: bool = False,
        drone_name: str = "drone01",
        poll_interval: float = 0.02,
    ) -> None:
        self.stop()
        try:
            if not midi_port.strip():
                raise RuntimeError("Choose a MIDI output before starting the bridge.")
            existing_outputs = set(mido.get_output_names())
            requested_is_existing = midi_port in existing_outputs
            midi_out = open_shared_midi_output(
                midi_port,
                virtual=not requested_is_existing,
                fallback_to_default=False,
            )
        except Exception as exc:
            self.status.last_error = str(exc)
            self._notify()
            raise
        self.status.active_serial = serial_port
        self.status.midi_port = getattr(midi_out, "name", midi_port)
        self.status.last_error = None
        self._cc_cache.clear()
        self._worker = BridgeWorker(
            serial_port,
            midi_out,
            norm,
            channel=channel,
            on_cc=self._cc_listener,
            on_heartbeat=self._heartbeat,
            simulated=simulated,
            drone_name=drone_name,
            poll_interval=poll_interval,
        )
        self._worker.start()
        self._notify()

    def reload_config(self, norm: Dict[str, Dict[str, float]]) -> None:
        if self._worker:
            self._worker.update_mapper(norm)

    def stop(self) -> None:
        if self._worker:
            self._worker.stop()
            self._worker.join(timeout=1)
            self._worker = None
        self.status.heartbeat_ts = 0.0
        self._notify()

    def toggle_web_stream(self, enabled: bool) -> None:
        if enabled:
            if self._web_streamer is None:
                self._web_streamer = WebMidiStreamer()
                self._web_streamer.start()
        else:
            if self._web_streamer:
                self._web_streamer.stop()
                self._web_streamer = None


__all__ = [
    "BridgeBackend",
    "BridgeStatus",
]

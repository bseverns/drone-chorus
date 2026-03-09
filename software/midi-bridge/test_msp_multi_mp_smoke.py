import argparse
import sys
from pathlib import Path
from queue import Empty

MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

import msp_multi_mp  # noqa: E402


def _norm():
    return {
        "roll": {"min": -45.0, "max": 45.0},
        "pitch": {"min": -45.0, "max": 45.0},
        "yaw": {"min": -200.0, "max": 200.0},
        "altitude": {"min": 0.0, "max": 3.0},
        "rssi": {"min": 0.0, "max": 100.0},
        "vbat": {"min": 3.2, "max": 4.2},
        "throttle": {"min": 1000.0, "max": 2000.0},
    }


def _base_config():
    return {
        "norm": _norm(),
        "midi": {"port_name": "DroneChorus"},
        "runtime": {"poll_interval": 0.02, "idle_sleep": 0.001},
        "safety": {"gate_threshold": 1050.0},
        "drones": [{"name": "drone01", "channel": 1, "serial": "/dev/null"}],
    }


class FakeEvent:
    def __init__(self):
        self._set = False

    def set(self):
        self._set = True

    def is_set(self):
        return self._set


class FakeQueue:
    def __init__(self, messages=None):
        self._messages = list(messages or [])

    def get(self, timeout=0):
        if self._messages:
            return self._messages.pop(0)
        raise Empty


class FakeProcess:
    def __init__(self, *, pid=9999, alive_sequence=None):
        self.pid = pid
        self._alive = list(alive_sequence or [False])
        self.started = False
        self.joined = False
        self.terminated = False

    def start(self):
        self.started = True

    def is_alive(self):
        if len(self._alive) > 1:
            return self._alive.pop(0)
        return self._alive[0]

    def join(self, timeout=0):
        self.joined = True

    def terminate(self):
        self.terminated = True


class FakeContext:
    def __init__(self, *, queue_messages=None, process_alive=None):
        self._queue_messages = queue_messages or []
        self._process_alive = process_alive or [False]
        self.processes = []
        self.event = None

    def Queue(self, maxsize=0):  # noqa: N802
        return FakeQueue(self._queue_messages)

    def Event(self):  # noqa: N802
        self.event = FakeEvent()
        return self.event

    def Process(self, target=None, kwargs=None, daemon=True):  # noqa: N802
        process = FakeProcess(alive_sequence=self._process_alive)
        self.processes.append(process)
        return process


def test_mp_main_smoke_starts_and_stops_cleanly(monkeypatch):
    fake_ctx = FakeContext(process_alive=[False])
    fake_midi = type("FakeMidi", (), {"closed": False, "close": lambda self: setattr(self, "closed", True)})()

    monkeypatch.setattr(
        msp_multi_mp,
        "parse_args",
        lambda: argparse.Namespace(config="config/multi.yaml", queue_size=128),
    )
    monkeypatch.setattr(msp_multi_mp, "load_config", lambda _path: _base_config())
    monkeypatch.setattr(msp_multi_mp, "_open_midi_output", lambda _name: fake_midi)
    monkeypatch.setattr(msp_multi_mp.mp, "get_context", lambda _mode: fake_ctx)
    monkeypatch.setattr(msp_multi_mp.signal, "signal", lambda *_args, **_kwargs: None)

    msp_multi_mp.main()

    assert fake_ctx.event is not None
    assert fake_ctx.event.is_set() is True
    assert len(fake_ctx.processes) == 1
    assert fake_ctx.processes[0].started is True
    assert fake_ctx.processes[0].joined is True
    assert fake_midi.closed is True


def test_mp_main_emits_cc_when_state_message_arrives(monkeypatch):
    state_msg = (
        "state",
        {
            "drone": "drone01",
            "state": {
                "roll": 1.0,
                "pitch": 2.0,
                "yaw": 3.0,
                "altitude": 1.5,
                "rssi": 80.0,
                "vbat": 3.9,
                "throttle": 1200.0,
            },
            "ts": 1.0,
        },
    )
    fake_ctx = FakeContext(queue_messages=[state_msg], process_alive=[True, False, False])
    fake_midi = type("FakeMidi", (), {"close": lambda self: None})()
    emitted = []

    monkeypatch.setattr(
        msp_multi_mp,
        "parse_args",
        lambda: argparse.Namespace(config="config/multi.yaml", queue_size=128),
    )
    monkeypatch.setattr(msp_multi_mp, "load_config", lambda _path: _base_config())
    monkeypatch.setattr(msp_multi_mp, "_open_midi_output", lambda _name: fake_midi)
    monkeypatch.setattr(msp_multi_mp.mp, "get_context", lambda _mode: fake_ctx)
    monkeypatch.setattr(msp_multi_mp.signal, "signal", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        msp_multi_mp,
        "emit_state_cc",
        lambda *args, **kwargs: emitted.append((args, kwargs)),
    )

    msp_multi_mp.main()

    assert len(emitted) >= 1

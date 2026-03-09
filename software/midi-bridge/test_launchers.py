import importlib.util
import sys
from pathlib import Path
from queue import Empty, Full

import pytest

MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

import msp_multi_mp  # noqa: E402
import msp_multi_to_midi  # noqa: E402
import msp_to_midi  # noqa: E402

REPO_ROOT = MODULE_DIR.parent.parent
REPLAY_PATH = REPO_ROOT / "examples" / "replay_log.py"
_SPEC = importlib.util.spec_from_file_location("replay_log", REPLAY_PATH)
assert _SPEC and _SPEC.loader
replay_log = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(replay_log)


def test_single_launcher_warns_when_named_port_falls_back(monkeypatch, capsys):
    sentinel = object()
    record = {}

    def fake_open_shared(port_name, **kwargs):
        record["port_name"] = port_name
        record["kwargs"] = kwargs
        kwargs["on_fallback"]("fallback message")
        return sentinel

    monkeypatch.setattr(msp_to_midi, "open_shared_midi_output", fake_open_shared)
    out = msp_to_midi.open_midi_output("MissingPort", virtual=True)

    assert out is sentinel
    assert record["port_name"] == "MissingPort"
    assert record["kwargs"]["virtual"] is True
    assert record["kwargs"]["fallback_to_default"] is True
    assert "[midi-warning]" in capsys.readouterr().err


def test_threaded_launcher_warns_when_named_port_falls_back(monkeypatch, capsys):
    sentinel = object()
    record = {}

    def fake_open_shared(port_name, **kwargs):
        record["port_name"] = port_name
        record["kwargs"] = kwargs
        kwargs["on_fallback"]("fallback message")
        return sentinel

    monkeypatch.setattr(msp_multi_to_midi, "open_shared_midi_output", fake_open_shared)
    out = msp_multi_to_midi.open_midi_output("MissingPort")

    assert out is sentinel
    assert record["port_name"] == "MissingPort"
    assert record["kwargs"]["virtual"] is True
    assert record["kwargs"]["fallback_to_default"] is True
    assert "[midi-warning]" in capsys.readouterr().err


def test_multiprocess_launcher_warns_when_named_port_falls_back(monkeypatch, capsys):
    sentinel = object()
    record = {}

    def fake_open_shared(port_name, **kwargs):
        record["port_name"] = port_name
        record["kwargs"] = kwargs
        kwargs["on_fallback"]("fallback message")
        return sentinel

    monkeypatch.setattr(msp_multi_mp, "open_shared_midi_output", fake_open_shared)
    out = msp_multi_mp._open_midi_output("MissingPort")

    assert out is sentinel
    assert record["port_name"] == "MissingPort"
    assert record["kwargs"]["virtual"] is True
    assert record["kwargs"]["fallback_to_default"] is True
    assert "[midi-warning]" in capsys.readouterr().err


def test_mp_queue_helper_drops_oldest_entry_under_backpressure():
    class TinyQueue:
        def __init__(self, maxsize):
            self._max = maxsize
            self.items = []

        def put_nowait(self, message):
            if len(self.items) >= self._max:
                raise Full
            self.items.append(message)

        def get_nowait(self):
            if not self.items:
                raise Empty
            return self.items.pop(0)

    queue = TinyQueue(maxsize=1)
    msp_multi_mp._queue_put_drop_oldest(queue, ("state", {"seq": 1}))
    msp_multi_mp._queue_put_drop_oldest(queue, ("state", {"seq": 2}))

    assert queue.items == [("state", {"seq": 2})]


def test_replay_choose_midi_port_uses_strict_helper(monkeypatch):
    record = {}
    sentinel = object()

    def fake_open(port_name, **kwargs):
        record["port_name"] = port_name
        record["kwargs"] = kwargs
        return sentinel

    monkeypatch.setattr(replay_log, "open_shared_midi_output", fake_open)

    out = replay_log.choose_midi_port("ReplayPort", virtual=False)

    assert out is sentinel
    assert record["port_name"] == "ReplayPort"
    assert record["kwargs"]["virtual"] is False
    assert record["kwargs"]["fallback_to_default"] is False


def test_replay_choose_midi_port_exits_on_open_failure(monkeypatch):
    monkeypatch.setattr(
        replay_log,
        "open_shared_midi_output",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with pytest.raises(SystemExit, match="Failed to open MIDI port"):
        replay_log.choose_midi_port("ReplayPort", virtual=True)

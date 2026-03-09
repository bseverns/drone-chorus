import sys
from pathlib import Path

import pytest

MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

import gui_backend  # noqa: E402
from gui_backend import BridgeBackend, WebMidiStreamer  # noqa: E402


def _norm_spec():
    return {key: {"min": 0.0, "max": 1.0} for key in gui_backend.STATE_KEYS}


def test_load_config_sets_cli_scope_notice_for_extra_keys(tmp_path):
    config_path = tmp_path / "multi_like.yaml"
    config_path.write_text(
        """
norm:
  roll: {min: -45, max: 45}
  pitch: {min: -45, max: 45}
  yaw: {min: -200, max: 200}
  altitude: {min: 0, max: 5}
  rssi: {min: 0, max: 100}
  vbat: {min: 3.2, max: 4.2}
  throttle: {min: 1000, max: 2000}
runtime:
  poll_interval: 0.02
signals:
  climb_rate:
    cc: 21
""".strip(),
        encoding="utf-8",
    )

    backend = BridgeBackend()
    norm = backend.load_config(config_path)

    assert "roll" in norm
    assert backend.status.config_notice is not None
    assert "GUI applies only the 'norm' block." in backend.status.config_notice
    assert "runtime" in backend.status.config_notice
    assert "signals" in backend.status.config_notice


def test_load_config_accepts_top_level_norm_mapping_without_notice(tmp_path):
    config_path = tmp_path / "norm_only.yaml"
    config_path.write_text(
        """
roll: {min: -45, max: 45}
pitch: {min: -45, max: 45}
yaw: {min: -200, max: 200}
altitude: {min: 0, max: 5}
rssi: {min: 0, max: 100}
vbat: {min: 3.2, max: 4.2}
throttle: {min: 1000, max: 2000}
""".strip(),
        encoding="utf-8",
    )

    backend = BridgeBackend()
    norm = backend.load_config(config_path)

    assert norm["throttle"]["max"] == 2000
    assert backend.status.config_notice is None


def test_start_fails_when_requested_midi_port_cannot_open(monkeypatch):
    backend = BridgeBackend()
    monkeypatch.setattr(gui_backend.mido, "get_output_names", lambda: [])
    monkeypatch.setattr(
        gui_backend.mido,
        "open_output",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("port missing")),
    )

    with pytest.raises(RuntimeError, match="Failed to open requested MIDI port"):
        backend.start(
            serial_port="/dev/null",
            midi_port="MissingPort",
            norm=_norm_spec(),
            simulated=True,
        )

    assert backend.status.last_error is not None
    assert "MissingPort" in backend.status.last_error


def test_start_uses_existing_output_name_without_virtual_fabrication(monkeypatch):
    class FakeMidiOut:
        def __init__(self, name):
            self.name = name

    calls = []

    def fake_open_output(name, virtual=False):
        calls.append((name, virtual))
        return FakeMidiOut("OpenedHardwarePort")

    created = {}

    class FakeWorker:
        def __init__(self, *args, **kwargs):
            created["worker"] = self
            self.started = False
            self.stopped = False
            self.joined = False

        def start(self):
            self.started = True

        def stop(self):
            self.stopped = True

        def join(self, timeout=0):
            self.joined = True

    monkeypatch.setattr(gui_backend.mido, "get_output_names", lambda: ["HardwarePort"])
    monkeypatch.setattr(gui_backend.mido, "open_output", fake_open_output)
    monkeypatch.setattr(gui_backend, "BridgeWorker", FakeWorker)

    backend = BridgeBackend()
    backend.start(
        serial_port="/dev/null",
        midi_port="HardwarePort",
        norm=_norm_spec(),
        simulated=True,
    )

    assert calls == [("HardwarePort", False)]
    assert backend.status.midi_port == "OpenedHardwarePort"
    assert created["worker"].started is True
    backend.stop()
    assert created["worker"].stopped is True
    assert created["worker"].joined is True


def test_webmidi_defaults_to_loopback_hosts():
    streamer = WebMidiStreamer()
    assert streamer._host == "127.0.0.1"
    assert streamer._http_host == "127.0.0.1"

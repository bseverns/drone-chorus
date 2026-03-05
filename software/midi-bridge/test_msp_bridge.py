import struct
import sys
from pathlib import Path

import pytest

# Make sure the test can import the module even though the directory name contains a dash.
MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

import msp_bridge  # noqa: E402
from msp_bridge import (  # noqa: E402
    MSP_ANALOG,
    MSP_ALTITUDE,
    MSP_ATTITUDE,
    MSP_RC,
    Mapper,
    _CC_MAPPING,
    _STATE_TEMPLATE,
    build_altitude_consumers,
    build_signal_schema,
    emit_state_cc,
    merge_state_handlers,
    read_msp_frame,
    update_state_from_msp,
)


class ScriptedSerial:
    """Pretend serial port that yields pre-scripted chunks to ``read`` calls."""

    def __init__(self, script):
        self._script = list(script)

    def read(self, n):
        if not self._script:
            return b""
        chunk = self._script.pop(0)
        if len(chunk) > n:
            raise AssertionError(
                f"Script attempted to return {len(chunk)} bytes for read({n})"
            )
        return chunk


class IdentitySmoother:
    """Bypass smoother that simply echoes the mapped value."""

    def __init__(self):
        self.seen = []

    def step(self, value):
        self.seen.append(value)
        return value


class StubSmoother:
    """Configurable smoother for deterministic slew tests."""

    def __init__(self, slew=0.05, start=None):
        self._slew = slew
        self._y = start

    def step(self, value):
        # Reuse the production slew math to ensure parity with real runs.
        from msp_bridge import clamp  # local import to avoid global patching

        if self._y is None:
            self._y = value
            return value
        delta = clamp(value - self._y, -self._slew, self._slew)
        self._y += delta
        return self._y


class FakeMidiMessage:
    def __init__(self, type, channel, control, value):
        self.type = type
        self.channel = channel
        self.control = control
        self.value = value


class FakeMidiOut:
    def __init__(self):
        self.sent = []

    def send(self, message):
        self.sent.append(message)


class TimeMachine:
    def __init__(self):
        self.now = 0.0

    def jump(self, value):
        self.now = value

    def time(self):
        return self.now


def test_read_msp_frame_success():
    script = [
        b"$",
        b"M",
        b"<",
        bytes([2]),
        bytes([0x10]),
        b"\xaa\xbb",
        b"\xff",
    ]
    ser = ScriptedSerial(script)

    cmd, payload = read_msp_frame(ser)

    assert cmd == 0x10
    assert payload == b"\xaa\xbb"


def test_read_msp_frame_timeout_preserves_alignment():
    script = [
        b"$",
        b"M",
        b"<",
        bytes([2]),
        bytes([0x22]),
        b"\xaa",
        b"",  # timeout while waiting for the second payload byte
        b"$",
        b"M",
        b"<",
        bytes([0]),
        bytes([0x33]),
        b"\x99",
    ]
    ser = ScriptedSerial(script)

    # First frame should bail with ``None`` because the payload never finished.
    assert read_msp_frame(ser) is None

    # The next call should start at the ``$`` byte of the second frame.
    cmd, payload = read_msp_frame(ser)

    assert cmd == 0x33
    assert payload == b""


def test_mapper_norm01_linear_and_expo_paths_share_shape_math():
    mapper = Mapper(
        {
            "roll": {"min": -180.0, "max": 180.0},
            "yaw": {"min": 0.0, "max": 100.0, "curve": "expo"},
        }
    )
    mapper._smoothers["roll"] = IdentitySmoother()
    mapper._smoothers["yaw"] = IdentitySmoother()

    linear = mapper.norm01("roll", 0.0)
    assert linear == pytest.approx(0.5)
    expo = mapper.norm01("yaw", 25.0)

    normalized = 0.25
    shaped = (abs(normalized - 0.5) * 2) ** 1.3
    shaped *= -1
    expected_expo = shaped * 0.5 + 0.5

    assert mapper._smoothers["roll"].seen == [0.5]
    assert mapper._smoothers["yaw"].seen == [pytest.approx(expected_expo)]
    assert expo == pytest.approx(expected_expo)


def test_mapper_norm01_respects_per_parameter_slew_limits():
    mapper = Mapper({"pitch": {"min": -90.0, "max": 90.0, "slew": 0.1}})
    mapper._smoothers["pitch"] = StubSmoother(slew=0.1, start=0.2)

    # Target normalized value would be 1.0 without slew; limiter should step by 0.1.
    assert mapper.norm01("pitch", 90.0) == pytest.approx(0.3)
    # Second step keeps gliding toward the target.
    assert mapper.norm01("pitch", 90.0) == pytest.approx(0.4)


def test_update_state_from_msp_decodes_core_payloads():
    state = dict(_STATE_TEMPLATE)

    update_state_from_msp(state, MSP_ATTITUDE, struct.pack("<hhh", 100, -50, 0))
    assert state["roll"] == pytest.approx(10.0)
    assert state["pitch"] == pytest.approx(-5.0)

    rc_payload = struct.pack("<8H", 1000, 1500, 1600, 1800, 0, 0, 0, 0)
    update_state_from_msp(state, MSP_RC, rc_payload)
    assert state["throttle"] == 1600
    expected_yaw = (1800 - 1500) / 500.0 * 200.0
    assert state["yaw"] == pytest.approx(expected_yaw)

    altitude_payload = struct.pack("<i", 250)
    update_state_from_msp(state, MSP_ALTITUDE, altitude_payload)
    assert state["altitude"] == pytest.approx(2.5)

    analog_payload = bytes([42, 0, 0, 88, 0, 0, 0])
    update_state_from_msp(state, MSP_ANALOG, analog_payload)
    assert state["vbat"] == pytest.approx(4.2)
    assert state["rssi"] == 88


def test_emit_state_cc_publishes_all_controllers(monkeypatch):
    spec = {key: {"min": 0.0, "max": 1.0} for key in _CC_MAPPING}
    mapper = Mapper(spec)
    state = dict(_STATE_TEMPLATE)
    state.update({
        "roll": 0.0,
        "pitch": 0.0,
        "yaw": 0.0,
        "altitude": 0.0,
        "rssi": 0.0,
        "vbat": 0.0,
        "throttle": 1200,
    })
    norm_values = {
        "roll": 0.0,
        "pitch": 0.5,
        "yaw": 0.25,
        "altitude": 0.75,
        "rssi": 1.0,
        "vbat": 0.1,
        "throttle": 0.9,
    }

    def fake_norm01(key, value):
        assert value == state[key]
        return norm_values[key]

    mapper.norm01 = fake_norm01  # type: ignore[assignment]
    monkeypatch.setattr(msp_bridge.mido, "Message", FakeMidiMessage)
    midi_out = FakeMidiOut()

    emit_state_cc(midi_out, mapper, 2, state)

    assert len(midi_out.sent) == len(_CC_MAPPING) + 1
    for message, (key, control) in zip(midi_out.sent[:-1], _CC_MAPPING.items()):
        assert message.type == "control_change"
        assert message.channel == 2
        assert message.control == control
        assert message.value == int(norm_values[key] * 127)
    gate = midi_out.sent[-1]
    assert gate.control == 64
    assert gate.value == 127


def test_emit_state_cc_gate_closes_below_idle(monkeypatch):
    mapper = Mapper({key: {"min": 0.0, "max": 1.0} for key in _CC_MAPPING})
    state = dict(_STATE_TEMPLATE)
    state["throttle"] = 1000

    mapper.norm01 = lambda key, value: 0.0  # type: ignore[assignment]
    monkeypatch.setattr(msp_bridge.mido, "Message", FakeMidiMessage)
    midi_out = FakeMidiOut()

    emit_state_cc(midi_out, mapper, 0, state)

    gate = midi_out.sent[-1]
    assert gate.control == 64
    assert gate.value == 0


def test_altitude_helpers_switch_between_baro_and_throttle():
    clock = TimeMachine()
    inject_altitude, extra_handlers = build_altitude_consumers(time_source=clock.time)
    assert MSP_ALTITUDE in extra_handlers
    state = {"altitude": 0.0, "throttle": 1300.0}

    # Without baro data the throttle-derived ramp should kick in after 1s.
    clock.jump(5.0)
    inject_altitude(state)
    expected_ramp = ((1300.0 - 1000.0) / 1000.0) * 3.0
    assert state["altitude"] == pytest.approx(expected_ramp)

    # A barometer payload should overwrite the ramp and freeze for <1s.
    clock.jump(5.2)
    extra_handlers[MSP_ALTITUDE](state, struct.pack("<i", int(2.5 * 100)))
    assert state["altitude"] == pytest.approx(2.5)

    clock.jump(5.7)
    inject_altitude(state)
    assert state["altitude"] == pytest.approx(2.5)

    # Past the stale threshold the ramp should resume using the latest throttle.
    state["throttle"] = 900.0
    clock.jump(7.5)
    inject_altitude(state)
    assert state["altitude"] == 0.0


def test_build_signal_schema_adds_custom_signal_and_handler():
    signals = {
        "climb_rate": {
            "cc": 21,
            "default": 0.0,
            "msp": {"cmd": MSP_ALTITUDE, "format": "<i", "scale": 0.01},
        }
    }

    state_template, cc_mapping, handlers = build_signal_schema(signals)

    assert state_template["climb_rate"] == 0.0
    assert cc_mapping["climb_rate"] == 21
    assert MSP_ALTITUDE in handlers

    state = dict(state_template)
    handlers[MSP_ALTITUDE](state, struct.pack("<i", 350))
    assert state["climb_rate"] == pytest.approx(3.5)


def test_build_signal_schema_requires_cc_for_new_signals():
    with pytest.raises(ValueError, match="must define 'cc'"):
        build_signal_schema({"new_signal": {"default": 0.0}})


def test_merge_state_handlers_chains_shared_commands():
    def base_handler(state, payload):
        state["first"] = payload[0]

    def extra_handler(state, payload):
        state["second"] = payload[0] + 1

    merged = merge_state_handlers({1: base_handler}, {1: extra_handler})
    state = {}
    merged[1](state, b"\x05")
    assert state == {"first": 5, "second": 6}


def test_emit_state_cc_supports_custom_cc_mapping(monkeypatch):
    mapper = Mapper({"roll": {"min": 0.0, "max": 1.0}})
    state = {"roll": 0.5, "throttle": 900.0}
    mapper.norm01 = lambda key, value: value  # type: ignore[assignment]
    monkeypatch.setattr(msp_bridge.mido, "Message", FakeMidiMessage)
    midi_out = FakeMidiOut()

    emit_state_cc(midi_out, mapper, 1, state, cc_mapping={"roll": 70})

    assert midi_out.sent[0].control == 70
    assert midi_out.sent[0].value == int(0.5 * 127)
    assert midi_out.sent[-1].control == 64
    assert midi_out.sent[-1].value == 0

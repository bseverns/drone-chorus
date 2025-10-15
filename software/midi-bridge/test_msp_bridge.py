import sys
from pathlib import Path

import pytest

# Make sure the test can import the module even though the directory name contains a dash.
MODULE_DIR = Path(__file__).resolve().parent
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from msp_bridge import read_msp_frame  # noqa: E402


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

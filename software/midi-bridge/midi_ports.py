"""Shared MIDI port opening helpers used across bridge entrypoints."""

from __future__ import annotations

from typing import Callable, Optional

import mido


def open_midi_output(
    port_name: Optional[str],
    *,
    virtual: bool = True,
    fallback_to_default: bool = True,
    on_fallback: Optional[Callable[[str], None]] = None,
):
    """Open a MIDI output using a consistent fallback policy.

    Args:
        port_name: Named destination to open. Empty/None means "default output".
        virtual: Whether to request a virtual port when opening ``port_name``.
        fallback_to_default: If True, failure to open ``port_name`` falls back to
            ``mido.open_output()``.
        on_fallback: Optional callback invoked with a warning string when the
            function falls back from a requested named port to default output.
    """

    requested = (port_name or "").strip()
    if requested:
        try:
            return mido.open_output(requested, virtual=virtual)
        except Exception as exc:
            if not fallback_to_default:
                raise RuntimeError(
                    f"Failed to open requested MIDI port '{requested}': {exc}"
                ) from exc
            if on_fallback is not None:
                on_fallback(
                    "Requested MIDI port "
                    f"'{requested}' unavailable ({type(exc).__name__}: {exc}); "
                    "falling back to default output."
                )
            try:
                return mido.open_output()
            except Exception as fallback_exc:
                raise RuntimeError(
                    "Failed to open requested MIDI port "
                    f"'{requested}' and default output: {fallback_exc}"
                ) from fallback_exc

    if not fallback_to_default:
        raise RuntimeError("MIDI port name is required when fallback is disabled.")
    try:
        return mido.open_output()
    except Exception as exc:
        raise RuntimeError(f"Failed to open default MIDI output: {exc}") from exc


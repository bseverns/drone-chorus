# GUI Control Room Guide

This guide covers the PyQt6 dashboard in `software/midi-bridge/gui_app.py`:
serial selection, MIDI output routing, preset workflows, and live config editing.

See also:

- [CURRENT_STATE.md](CURRENT_STATE.md) for scope and maturity
- [CONTROL_CONTRACT.md](CONTROL_CONTRACT.md) for the canonical mapping contract
- [PRESET_GALLERY.md](PRESET_GALLERY.md) for how presets should be named and documented

## Scope truth

- Canonical stack: CLI launchers (`msp_to_midi.py`, `msp_multi_to_midi.py`, `msp_multi_mp.py`).
- GUI scope: single-drone bridge operation, live monitoring, and `norm` mapping edits.
- Not first-class in GUI today: multi-drone orchestration, full `signals` workflows, and full `runtime`/`safety` controls.

## Launch

```bash
python software/midi-bridge/gui_app.py
```

If the app fails to start, install/update dependencies first:

```bash
pip install -r software/midi-bridge/requirements.txt
```

## Panel tour

1. Top bar
- `Serial Port`: MSP input device (auto-refreshes every 2s).
- `MIDI Out`: destination MIDI port (auto-refreshes every 2s).
- `Debug Simulator`: generates synthetic telemetry with no drone connected.
- `Start Bridge` / `Stop`: start or halt the backend worker.

2. Live MIDI Monitor
- Heartbeat LED pulses when CC bursts are emitted.
- Tree view shows `Drone`, `Control`, `CC`, `Value`.
- Table updates on value changes to avoid unnecessary UI churn.

3. Config + Presets
- `Preset`: YAML files from `presets/`.
- `Load Preset`: loads selected YAML and hot-reloads mapper settings.
- `Browse...`: open any YAML file.
- `Unlock editor`: enable inline YAML editing.
- `Save YAML`: writes current text back to disk and keeps watcher active.

4. Extras
- `WebMIDI preview server`: starts websocket + local preview page:
  - `ws://localhost:8765`
  - `http://localhost:8080`
  - Both services bind to loopback only by default.

## Preset workflow

1. Copy `presets/demo.yaml` to a new file in `presets/`, e.g. `presets/show_a.yaml`.
2. Tune `norm` values (range, curve, slew).
3. In the GUI, choose the preset and click `Load Preset`.
4. Fly or run simulator and watch CC response.
5. Save once the patch feels musical.

Recommended naming:
- `venue_patchname.yaml` for show files.
- `lab_experiment_<date>.yaml` for rehearsal experiments.

For a repo-level preset documentation structure, see [PRESET_GALLERY.md](PRESET_GALLERY.md).

## Customizing signals and CC assignments

The CLI and multi-drone bridge support a `signals:` schema in config YAML.
The GUI currently focuses on the `norm` block only, so use CLI launchers for
full custom signal extraction/CC remapping workflows.

## Safety usage in control room

- Keep `Debug Simulator` on when patching new mappings.
- Validate CC ranges before arming aircraft.
- For live sessions, pair GUI use with checklist steps from `docs/checklists/SAFETY.md`.
- If you are using an external E-stop latch file in CLI workflows, verify it
  closes CC64 gate before rehearsal.

## Common issues

1. Empty serial dropdown
- Replug USB cable.
- Confirm MSP is enabled in Betaflight Ports tab.
- Restart GUI after driver changes.

2. No MIDI output in Rack
- Ensure Rack device is listening to the same port shown in GUI.
- On Windows, create/select a loopback MIDI port first.
- GUI startup no longer silently falls back to a different MIDI port; if selected
  output cannot open, start fails with an explicit error.

3. Config error on load
- Ensure YAML parses.
- Ensure each norm key has `min` and `max`.

4. Web preview not loading
- Confirm nothing else is using port `8080` or `8765`.

## Operating tips for less technical users

- Start in simulator mode to learn the interface with zero flight risk.
- Keep one "known good" preset untouched as a fallback.
- Change only one telemetry range at a time, then listen and compare.

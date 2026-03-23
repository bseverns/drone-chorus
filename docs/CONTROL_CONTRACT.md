# Control Contract

This is the canonical operator page for the Drone-Chorus control contract:

`telemetry in -> normalized musical signals -> MIDI CC out -> Rack / show system`

If you want the shortest accurate answer to "what data becomes what control signal, and why?", start here.

See also:

- [CONTROL_STACK_PLAYBOOK.md](CONTROL_STACK_PLAYBOOK.md)
- [CURRENT_STATE.md](CURRENT_STATE.md)
- [GUI_CONTROL_ROOM.md](GUI_CONTROL_ROOM.md)

## Contract in one view

### Telemetry inputs

Drone-Chorus reads Betaflight MSP frames and currently derives control from these built-in inputs:

- `MSP_ATTITUDE`:
  - `roll`
  - `pitch`
- `MSP_RC`:
  - `throttle`
  - `yaw` as a yaw-stick-derived rate proxy
- `MSP_ANALOG`:
  - `vbat`
  - `rssi`
- `MSP_ALTITUDE`:
  - `altitude` in meters when present

Altitude has a documented fallback: if `MSP_ALTITUDE` has not updated recently, the bridge derives a simple 0-3 m envelope from throttle so CC17 still moves on aircraft that do not publish barometric altitude.

### Normalized signals

The built-in normalized signal set is:

- `roll`
- `pitch`
- `yaw`
- `altitude`
- `rssi`
- `vbat`
- `throttle`

Each signal is shaped by the YAML `norm` block:

- `min`
- `max`
- `curve`
- `slew`

This is the musical middle of the system. The repo's sound and trustworthiness come less from raw telemetry than from these ranges and smoothing values.

### Default CC assignments

The stable default CC block is:

| CC | Signal | Why it exists in the musical contract |
| ---: | --- | --- |
| 14 | `roll` | lateral motion translated into timbre / filter movement |
| 15 | `pitch` | front-back tilt translated into pitch-adjacent or FM motion |
| 16 | `yaw` | lively motion, often suited to delay or space modulation |
| 17 | `altitude` | vertical energy / macro shape |
| 18 | `rssi` | signal health translated into wetness or texture restraint |
| 19 | `vbat` | battery sag translated into tone, compression, or stress color |
| 20 | `throttle` | direct energy / VCA / dynamic drive |
| 64 | arm gate | sustain-style gate for scene hold, bypass, or envelope logic |

The default mapping is intentionally compact and easy to remember. That simplicity is part of the instrument design.

## Arm and gate behavior

CC64 is the gate/arm signal.

- Default behavior:
  - send `127` when throttle is above the gate threshold
  - send `0` when throttle is at or below the gate threshold
- Default threshold:
  - `1050`
- Config location:
  - `safety.gate_threshold` in `config/multi.yaml`
  - `--gate-threshold` for `msp_to_midi.py`

Important truth: the repo documentation often talks about "arm" or "arming," but the current emitted contract is throttle-threshold-based gate behavior, not a separate MSP arming-status field.

If an external E-stop latch file is active, the bridge forces throttle back to idle and CC64 closes.

## Per-drone channel strategy

The canonical ensemble strategy is:

- one shared MIDI port, usually `DroneChorus`
- one MIDI channel per drone
- same CC numbers for every drone

Example:

- Drone A -> channel 1 -> CC14-20 + CC64
- Drone B -> channel 2 -> CC14-20 + CC64
- Drone C -> channel 3 -> CC14-20 + CC64

Why this is canonical:

- it keeps patch structure consistent across drones
- it makes VCV Rack duplication straightforward
- it preserves one musical vocabulary while adding more voices

See: [per-drone-channels.md](per-drone-channels.md)

## Single-drone vs multi-drone expectations

### Single-drone

Use the single-drone CLI path when you want:

- bench tuning
- first-flight musical mapping
- a safe one-voice rehearsal
- replay against one patch voice

Typical shape:

- `software/midi-bridge/msp_to_midi.py`
- MIDI channel 1
- `vcv/DroneChorus_Patch.vcv`
- optional `--norm-overrides`

### Multi-drone

Use the multi-drone CLI path when you want:

- one voice per drone
- fixed per-drone channel assignment
- ensemble rehearsal with a shared port
- shared norms with optional per-drone overrides

Typical shape:

- `software/midi-bridge/msp_multi_to_midi.py`
- `config/multi.yaml`
- channels `1..N`
- duplicated or complementary Rack voices

### Process-based multi-drone

`software/midi-bridge/msp_multi_mp.py` preserves the same contract but changes the runtime architecture. Treat it as a runtime experiment, not a new control vocabulary.

## Stable contract

These are the parts operators should expect to remain consistent:

- Betaflight MSP is the telemetry source
- the built-in signal set:
  - `roll`, `pitch`, `yaw`, `altitude`, `rssi`, `vbat`, `throttle`
- the default CC block:
  - CC14-20 and CC64
- one shared MIDI port plus per-drone channel assignment
- CLI launchers as the canonical operator path
- altitude fallback when `MSP_ALTITUDE` is absent
- throttle-threshold gate behavior on CC64

## Configurable contract

These parts are meant to be tuned without changing the system's identity:

- `norm` values:
  - `min`, `max`, `curve`, `slew`
- per-drone `norm_overrides`
- MIDI port naming
- channel assignment per drone
- runtime tuning:
  - `poll_interval`
  - `idle_sleep`
  - `publish_interval` in multiprocessing mode
- safety thresholds:
  - `throttle_limit`
  - `gate_threshold`
  - `estop_file`

The repo's intended workflow is to keep the vocabulary stable while tuning these values for aircraft, room, patch, and rehearsal context.

## Experimental extensions

These capabilities exist, but should be treated as extensions rather than core contract:

- `signals:` schema in YAML for custom or remapped signals
- process-based multi-drone launcher
- GUI-side debug simulator and WebMIDI preview server

The `signals:` schema can add new fields and new CC assignments without Python edits, but those added signals are not yet part of the repo's stable musical vocabulary.

## OSC equivalents

There is no first-class OSC output contract documented in this repo today.

What does exist:

- MIDI CC is the canonical control output
- the GUI offers a websocket/WebMIDI preview surface for monitoring
- OBS scenes can visualize the performance stack

What does not exist today:

- a documented OSC message schema
- a canonical OSC port/address contract
- an operator doc that treats OSC as equal to the MIDI path

TODO:

- If OSC becomes a real supported output, document exact message addresses, value ranges, channel strategy, and whether OSC mirrors the MIDI contract or introduces a separate one.

## Known doc tensions and truth-preserving notes

- Several docs describe CC64 as "arm" or "arm gate." The code currently derives it from throttle threshold plus E-stop behavior, not from a separate arming-status telemetry field.
- Some docs imply OBS overlays are part of the same control surface. They are adjacent show surfaces, not the canonical control contract.
- The GUI edits `norm` workflows well, but it does not yet expose the full `signals`, `runtime`, and `safety` surface of the CLI path.

TODO:

- Consolidate any remaining duplicate CC/gate descriptions in older docs around the language used here.

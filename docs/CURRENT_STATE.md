# Current State

This page labels the maturity of each major Drone-Chorus surface so visitors do not have to infer stability from tone alone.

Labels used here:

- `Stable operator path`
- `Documented but evolving`
- `Experimental / frontier`
- `Explore now`

## Single-drone CLI path

**Label**: `Stable operator path`

What is real now:

- `software/midi-bridge/msp_to_midi.py` is the canonical single-drone launcher.
- It supports the built-in telemetry-to-CC contract, `norm` reuse, overrides, throttle limit, gate threshold, and E-stop latch behavior.
- It is the clearest path for one-aircraft tuning, rehearsal, and first safe flight-to-sound proof.

Good entry docs:

- [README.md](../README.md)
- [CONTROL_CONTRACT.md](CONTROL_CONTRACT.md)
- [CONTROL_STACK_PLAYBOOK.md](CONTROL_STACK_PLAYBOOK.md)

## Multi-drone CLI path

**Label**: `Stable operator path`

What is real now:

- `software/midi-bridge/msp_multi_to_midi.py` plus `config/multi.yaml` is the canonical ensemble path.
- One shared port plus per-drone MIDI channels is supported and documented.
- Shared norms, per-drone overrides, and bridge-level safety/runtime controls are part of this path.

Caveat:

- Stability here means "real operator path," not "finished forever." Patch design, venue practice, and operator receipts still matter.

Good entry docs:

- [README.md](../README.md)
- [CONTROL_CONTRACT.md](CONTROL_CONTRACT.md)
- [CONTROL_STACK_PLAYBOOK.md](CONTROL_STACK_PLAYBOOK.md)

## Process-based multi-drone path

**Label**: `Experimental / frontier`

What is real now:

- `software/midi-bridge/msp_multi_mp.py` exists and preserves the same control contract.
- It uses worker processes per drone and a parent-owned MIDI output path.
- The repo includes smoke-test coverage for this launcher.

Caveat:

- The runtime architecture is explicitly a prototype path for heavier load, not the default recommended operator route.

Good entry docs:

- [README.md](../README.md)
- [CONTROL_CONTRACT.md](CONTROL_CONTRACT.md)
- [software/midi-bridge/README.md](../software/midi-bridge/README.md)

## GUI control room

**Label**: `Documented but evolving`

What is real now:

- The PyQt6 GUI supports single-drone operation, live CC monitoring, `norm` preset workflows, a debug simulator, and a WebMIDI preview server.
- It is useful for mapper tuning, teaching, and less-terminal-heavy sessions.

What is not first-class in the GUI:

- full multi-drone orchestration
- full `signals` workflows
- full `runtime` and `safety` surface parity with the CLI

Good entry docs:

- [GUI_CONTROL_ROOM.md](GUI_CONTROL_ROOM.md)
- [CURRENT_STATE.md](CURRENT_STATE.md)
- [PRESET_GALLERY.md](PRESET_GALLERY.md)

## Replay / sample logs

**Label**: `Explore now`

What is real now:

- `examples/replay_log.py` replays `.mspbin` logs through the same mapper stack used by live flight.
- `data/` ships workshop-friendly sample logs.
- `obs/telemetry/bench_hover.mspbin` provides a bench capture for no-props rehearsal.

Why the label is not "experimental":

- This path is already useful and trustworthy for proof, workshops, and tuning.
- It is not the live operator path, so the label emphasizes immediate use rather than runtime centrality.

Good entry docs:

- [REPLAY_AND_RECEIPTS.md](REPLAY_AND_RECEIPTS.md)
- [data/README.md](../data/README.md)
- [obs/telemetry/README.md](../obs/telemetry/README.md)

## VCV Rack patches

**Label**: `Explore now`

What is real now:

- Starter patches exist:
  - `vcv/DroneChorus_Patch.vcv`
  - `vcv/DroneChorus_2Drones.vcv`
- Patch cards document intent, setup quirks, and safety notes.

Caveat:

- These are starter surfaces, not exhaustive patch libraries. Manual patching judgment remains part of the instrument.

Good entry docs:

- [README.md](../README.md)
- [vcv/cards/README.md](../vcv/cards/README.md)
- [PRESET_GALLERY.md](PRESET_GALLERY.md)

## OBS layer

**Label**: `Documented but evolving`

What is real now:

- An OBS scene collection ships with documented relinking steps.
- The scenes are useful for rehearsal recording, streaming, and classroom demos.

Caveat:

- OBS is a show and teaching surface around the control stack, not the control contract itself.

Good entry docs:

- [obs/README.md](../obs/README.md)
- [EXPERIENCE_PLAYBOOK.md](EXPERIENCE_PLAYBOOK.md)
- [REPLAY_AND_RECEIPTS.md](REPLAY_AND_RECEIPTS.md)

## Workshop / teaching surface

**Label**: `Documented but evolving`

What is real now:

- The repo voice is already workshop-friendly.
- There are non-coder setup instructions, replay material, patch cards, logs, and safety docs.
- The code comments themselves are readable enough to teach from.

What is still partial:

- A dedicated workshop pack or curriculum sequence is not yet a single packaged artifact.
- More screenshots, filled-in receipts, and example session logs would strengthen this surface.

Good entry docs:

- [CHOOSE_YOUR_PATH.md](CHOOSE_YOUR_PATH.md)
- [SETUP_FOR_NONCODERS.md](SETUP_FOR_NONCODERS.md)
- [REPLAY_AND_RECEIPTS.md](REPLAY_AND_RECEIPTS.md)
- [logs/README.md](../logs/README.md)

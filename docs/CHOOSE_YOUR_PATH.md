# Choose Your Path

This page is for visitors who want the smallest useful route into the repo.

## I want to hear it without flying

Read these:

- [README.md](../README.md)
- [REPLAY_AND_RECEIPTS.md](REPLAY_AND_RECEIPTS.md)
- [data/README.md](../data/README.md)
- [obs/telemetry/README.md](../obs/telemetry/README.md)

Then run:

```bash
python scripts/generate_sample_logs.py
python examples/replay_log.py data/example_log_01.mspbin --verbose
```

## I want to fly one drone safely

Read these:

- [README.md](../README.md)
- [CONTROL_CONTRACT.md](CONTROL_CONTRACT.md)
- [CONTROL_STACK_PLAYBOOK.md](CONTROL_STACK_PLAYBOOK.md)
- [checklists/SAFETY.md](checklists/SAFETY.md)

Use the single-drone quickstart in the README, then patch channel 1 into `vcv/DroneChorus_Patch.vcv`.

## I want a multi-drone rehearsal

Read these:

- [README.md](../README.md)
- [CURRENT_STATE.md](CURRENT_STATE.md)
- [CONTROL_CONTRACT.md](CONTROL_CONTRACT.md)
- [CONTROL_STACK_PLAYBOOK.md](CONTROL_STACK_PLAYBOOK.md)
- [EXPERIENCE_PLAYBOOK.md](EXPERIENCE_PLAYBOOK.md)

Start with `config/multi.yaml` and the canonical launcher:

```bash
./scripts/launch_multi.sh
```

## I want the GUI/control room path

Read these:

- [GUI_CONTROL_ROOM.md](GUI_CONTROL_ROOM.md)
- [CURRENT_STATE.md](CURRENT_STATE.md)
- [PRESET_GALLERY.md](PRESET_GALLERY.md)
- [checklists/SAFETY.md](checklists/SAFETY.md)

Launch:

```bash
python software/midi-bridge/gui_app.py
```

Keep the scope truth in mind: GUI is a single-drone control room and preset-tuning surface, not the canonical full multi-drone operator stack.

## I want to patch VCV Rack

Read these:

- [CONTROL_CONTRACT.md](CONTROL_CONTRACT.md)
- [vcv/cards/README.md](../vcv/cards/README.md)
- [EXPERIENCE_PLAYBOOK.md](EXPERIENCE_PLAYBOOK.md)

Start from:

- `vcv/DroneChorus_Patch.vcv`
- `vcv/DroneChorus_2Drones.vcv`

## I want to teach this in a workshop

Read these:

- [README.md](../README.md)
- [SETUP_FOR_NONCODERS.md](SETUP_FOR_NONCODERS.md)
- [REPLAY_AND_RECEIPTS.md](REPLAY_AND_RECEIPTS.md)
- [CURRENT_STATE.md](CURRENT_STATE.md)
- [logs/README.md](../logs/README.md)

The fastest low-risk workshop path is replay first, live flight second.

## I want to contribute

Read these:

- [repo_health_drone_chorus_2026_03.md](repo_health_drone_chorus_2026_03.md)
- [CURRENT_STATE.md](CURRENT_STATE.md)
- [CONTROL_CONTRACT.md](CONTROL_CONTRACT.md)
- [ASSUMPTION_LEDGER.md](ASSUMPTION_LEDGER.md)
- [docs/releases/README.md](releases/README.md)

Good contribution targets:

- clearer receipts and filled-in logs
- patch cards and screenshots
- additional sample captures
- doc tightening around stable vs experimental behavior

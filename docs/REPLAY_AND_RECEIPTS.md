# Replay and Receipts

Replay is one of the strongest parts of Drone-Chorus because it turns the repo into something you can prove, teach, and iterate without spinning props.

## What replay means in this repo

Replay means feeding recorded MSP bytes back through the same mapper path used by live flight so the repo emits the same class of MIDI control behavior it would on stage.

Current replay surfaces:

- `examples/replay_log.py`
- `data/` sample logs
- `obs/telemetry/bench_hover.mspbin`
- bench-playback recipes in [software/midi-bridge/README.md](../software/midi-bridge/README.md)

## Why replay matters

### For workshops

- students can hear the system without needing aircraft in the air
- everyone can work from the same telemetry source
- musical differences become easier to compare because the source motion is fixed

### For debugging

- mapper changes can be tested against known telemetry
- regressions are easier to spot because the input stream is repeatable
- safety and setup checks can start with no-props proof

### For musical iteration

- you can tune `norm` ranges and curves against the same performance gesture repeatedly
- presets can earn trust through repeated comparison instead of memory
- patch changes can be auditioned against the same flight material

## Replay paths

### One-command sample-log replay

```bash
python scripts/generate_sample_logs.py
python examples/replay_log.py data/example_log_01.mspbin --verbose
```

That path:

- rebuilds the sample logs committed as base64 sources
- opens a replay MIDI port
- decodes MSP frames from the log
- emits the same class of CC14-20 plus CC64 output used by live flight

### Bench capture replay

For platform-specific pseudo-serial workflows using `socat` or `miniterm`, see:

- [software/midi-bridge/README.md](../software/midi-bridge/README.md)
- [obs/telemetry/README.md](../obs/telemetry/README.md)

## How replay differs from live flight

Replay is not a substitute for all live rehearsal truths.

Replay gives you:

- repeatable telemetry input
- safer first proof
- better teaching conditions
- faster mapping comparisons

Replay does not give you:

- live RF conditions
- current battery behavior in the room
- human pilot stress and timing
- venue-specific audience, OBS, or audio-chain surprises

Treat replay as a proof and tuning surface, then validate with real rehearsal.

## What a receipt means here

A receipt is the minimum evidence that a run actually happened and that its results can be trusted later.

In Drone-Chorus, a good receipt can include:

- the exact config or preset used
- the replay log or capture name
- the Rack patch/card used
- the OBS scene or recording reference
- a written log entry in `logs/`
- notes on what changed and what held up

The repo already has the beginnings of this discipline in:

- [logs/README.md](../logs/README.md)
- [logs/TEMPLATE.md](../logs/TEMPLATE.md)
- patch cards in `vcv/cards/`
- release-note policy in [docs/releases/README.md](releases/README.md)

## What operators should record after rehearsal or show runs

Minimum useful receipt:

- date/time
- pilot(s)
- drone IDs and MIDI channels
- mapping config or preset file
- replay log or live-capture source
- Rack patch used
- OBS scene/version if relevant
- what sounded good
- what felt unstable or unclear
- next tweaks

If the run was live, also record:

- battery notes
- RF/environment notes
- safety incidents or near-misses
- limiter / gain staging notes

## Good current proof surfaces

- sample logs in `data/`
- bench capture in `obs/telemetry/`
- `examples/replay_log.py`
- pilot log template in `logs/`
- patch cards in `vcv/cards/`

## TODOs

- Add one or more filled-in rehearsal receipts under `logs/` to model the desired standard.
- Add screenshots or short capture references showing replay driving Rack and/or OBS.
- Add explicit cross-links from future presets to the logs or captures that validated them.

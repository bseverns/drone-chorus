# MSP → MIDI Bridge Studio Notes

Welcome to the synth-nerd pit crew. This folder contains the Python that turns
Betaflight telemetry into modulation you can actually jam with. Treat this as a
combo lab notebook and zine—the goal is to help you *understand* the flow so you
can mangle it into your own rig.

## Files at a glance

| File | What it does | Why you should peek |
| --- | --- | --- |
| `msp_bridge.py` | Core plumbing: reads MSP frames, smooths/normalizes values, and blasts MIDI CCs. | The inline comments read like a wiring diagram—start here if you're learning the protocol. |
| `msp_to_midi.py` | Command-line launcher for a single drone. | Shows how to load the YAML norms, open a MIDI port, and kick the bridge loop. |
| `msp_multi_to_midi.py` | Threaded launcher for multi-drone ensembles. | Demonstrates sharing one MIDI port while isolating each craft on its own channel. |

## Dependencies (keep your rig in tune)

The bridge only leans on three external libraries, all pinned in
[`requirements.txt`](./requirements.txt) so your bench tests match mine exactly:

- **`mido==1.3.3`** — MIDI plumbing without the mystery smoke.
- **`PyYAML==6.0.3`** — loads the normalization maps you scribble in `config/`.
- **`pyserial==3.5`** — keeps the MSP serial link from getting cranky.

Drop into a shell and run `pip install -r software/midi-bridge/requirements.txt`
before you start hacking; future-you (and your collaborators) will thank you.

## Study guide

1. **Normalization maps live in `config/multi.yaml`.** The scripts load them and
   optionally merge override files. Copy the block, tweak ranges, and pass your
   remix via `--norm-overrides` while testing.
2. **Smoothing is your friend.** `Smoother` in `msp_bridge.py` clamps step size
   so your CCs glide instead of sputter. Experiment with the `slew` values to
   feel how the synth responds.
3. **Gate logic rides on throttle.** When the craft is armed (throttle > 1050),
   we send CC64 = 127. Patch that into envelopes, VCAs, whatever keeps your
   patch honest.

## Quick experiments

- **Run a dry rehearsal** by pointing `--serial` at a log playback tool like
  `socat` piping from a file. The bridge doesn't care where the bytes originate.
- **Add a new telemetry field** by editing `_STATE_TEMPLATE`, `_CC_MAPPING`, and
  `update_state_from_msp`. The new CC will appear automatically once you map it
  in Rack.
- **Teach the class**: have students clone this repo, annotate their own copies
  of the YAML, and compare how different scaling curves feel on the same patch.

> Bonus punk tip: keep a notepad next to your controller and jot down the
> wildest sounds each change summons. Science + noise forever.

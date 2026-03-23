# Repo Health Audit — March 2026

## What Drone-Chorus is

Drone-Chorus is a telemetry-driven performance stack built around a specific contract:

`Betaflight MSP telemetry -> smoothing/normalization -> MIDI CC -> VCV Rack / show system`

It is not just a bridge script and not a generic media-control app. In repo form, it behaves like three things at once:

- an operator stack for safe single-drone and multi-drone rehearsal
- a field manual for running that stack without guessing
- a teaching instrument for showing how flight data becomes musical control

## What is already unusually strong

- The repo has a clear center of gravity: flight telemetry becomes sound through a fixed, legible control vocabulary.
- The CLI stack is treated as canonical, which keeps the real control surface grounded in code and config that match.
- Safety language is part of the system shape, not a disclaimer bolted on after the fun part.
- The fixed CC block is memorable and repeated consistently enough to teach from.
- Replay is real: sample logs, bench captures, and `examples/replay_log.py` already support proof, rehearsal, and workshops.
- The docs already sound like a field manual instead of product copy, which makes the repo trustworthy.
- Per-drone MIDI channels provide a simple ensemble model without changing the musical contract.
- Logs, patch cards, and release-note policy already point toward operator discipline and reproducibility.

## What currently makes the repo feel complete

- A newcomer can go from README to single-drone CLI to VCV Rack patch without hunting through code first.
- Multi-drone scaling has a real documented path, not just a hand-wave.
- GUI scope is honest: useful for single-drone monitoring and `norm` tuning, not presented as the full stack.
- OBS, patch cards, logs, and sample captures make the repo feel like a performance system rather than a bare protocol experiment.
- The code comments and docs are already written in a teaching-ready style.

## What currently feels fragmented or under-consolidated

- The control contract is present in several places but not yet gathered into one operator-first page.
- Replay and "proof" value are strong in practice but dispersed across README, bridge notes, `data/`, and `obs/telemetry/`.
- Presets exist, but preset meaning is not yet framed as part of the musical and operational language of the repo.
- Maturity is implied rather than labeled, so newcomers have to infer what is stable, exploratory, or partial.
- Workshop entry points exist, but they are spread across multiple docs instead of being routed from one small "start here" page.
- There is no single page that says plainly where the contract ends and where configuration or experimentation begins.

## Canonical vs secondary surfaces

### Canonical

- CLI bridge path:
  - `software/midi-bridge/msp_to_midi.py`
  - `software/midi-bridge/msp_multi_to_midi.py`
  - `config/multi.yaml`
- Telemetry-to-CC mapping:
  - `software/midi-bridge/msp_bridge.py`
  - `config/multi.yaml`
  - `config/mapping.yaml`
- Operator safety and rehearsal discipline:
  - `docs/checklists/SAFETY.md`
  - `logs/`

### Secondary but important

- GUI control room for single-drone tuning and monitoring
- Replay helpers, sample logs, and telemetry captures
- VCV Rack starter patches and patch cards
- OBS scene collection and teaching-oriented broadcast layouts

## What expansion should protect at all costs

- The repo's center: safe flight -> legible mapping -> musical control -> documented rehearsal.
- CLI truth as the canonical control surface.
- The fixed default CC vocabulary and per-drone channel model.
- Honest scope statements instead of aspirational interface claims.
- Safety-first and teaching-zine tone.
- Replay/proof paths that let people learn and test without spinning props.
- Release/log discipline that keeps operator trust intact.

## Highest-value next expansions

1. Make the control contract canonical in one page and keep other docs pointing to it.
2. Give presets and mappings a documented naming/intention structure so growth stays musical instead of becoming anonymous YAML drift.
3. Label maturity by surface so visitors can see stable operator paths versus frontier work immediately.
4. Elevate replay, logs, and run receipts into a first-class rehearsal and proof surface.
5. Create a concise route picker for newcomers, performers, and workshop users.
6. Keep adding screenshots, sample captures, and filled-in operator logs so the repo accrues evidence, not just explanation.

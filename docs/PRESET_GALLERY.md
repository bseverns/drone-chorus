# Preset Gallery

This page gives presets a stable documentation shape so they read like named musical and operational personalities, not anonymous YAML drift.

## What a preset means here

In Drone-Chorus, a preset is currently a YAML description of mapping feel, centered on the `norm` block:

- input range
- response curve
- smoothing / slew

Today, presets are primarily a mapper-feel surface for the single-drone GUI and related tuning workflows. They do not represent an all-systems scene recall format for the entire repo.

## What a good preset name should communicate

A preset name should hint at both musical intent and operational context.

Prefer names that tell an operator:

- where it belongs:
  - rehearsal
  - show
  - lab
- what it is trying to do:
  - stable hover shaping
  - exaggerated timbre motion
  - slow macro swell

Examples of naming structure:

- `rehearsal_hover_stable.yaml`
- `show_patch_a.yaml`
- `lab_altitude_experiment_2026-03.yaml`

The exact filename style can stay simple, but the meaning should be legible.

## What to document for every preset

Each preset entry should eventually answer:

- **Filename**: exact YAML file
- **Status**:
  - rehearsal-safe
  - show
  - lab experiment
- **Intent**: what musical or operational behavior it is meant to produce
- **Patch context**: which Rack patch or voice layout it was tuned against
- **Risk notes**: anything unusually wide, twitchy, or venue-specific
- **Receipts**: which replay log, rehearsal log, or show log proved it useful

## Preset classes

### Rehearsal-safe presets

Use when you want:

- predictable ranges
- conservative slews
- easy-to-read behavior for tuning and workshops

Traits:

- stable center behavior
- reduced surprise
- suitable for first patch checks and no-props replay

### Show presets

Use when you want:

- repeatable performance feel
- a named relation to a specific patch or scene layout
- enough expressive range to be musical without needing last-minute rescue

Traits:

- proven in rehearsal
- documented with receipts
- not edited casually before a run

### Lab experiments

Use when you want:

- exaggerated mappings
- targeted tests of a new range, curve, or gesture idea
- quick comparisons against replay logs or simulator sessions

Traits:

- explicitly provisional
- documented with what is being tested
- easy to discard if they do not earn a real musical role

## Current examples in repo

| File | Status | What is documented now | Notes |
| --- | --- | --- | --- |
| `presets/demo.yaml` | rehearsal-safe starter | Basic `norm` tuning only | Good baseline for GUI loading and first tuning passes |

## Suggested gallery template for future entries

### `preset_name.yaml`

- **Status**:
- **Intent**:
- **Patch context**:
- **Notable norm changes**:
- **Best use**:
- **Receipts**:
- **TODO**:

## TODOs

- Add filled-in preset descriptions once more named presets exist in `presets/`.
- Link presets to concrete logs in `logs/` once rehearsal receipts are committed.
- Add patch-card cross references when specific presets are known to pair well with specific Rack cards.

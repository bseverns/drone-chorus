# Patch Cards

This directory is the trading-card deck for Drone Chorus patches. Each card (Markdown + PNG) is a storytelling tool you can hand to a collaborator, student, or future-you so they know how to fly the synth without guesswork.

## What every card must include

- **Patch name + screenshot (.png or .svg)** — capture the full Rack window with module labels visible. SVGs are preferred in PRs to keep diffs text-only; wrap PNG data inside an SVG if needed.
- **Telemetry mapping highlights** — which CCs hit which modules, and any attenuverters/offsets worth noting.
- **Musical intent** — describe foreground vs. texture voices, and which gestures make it sing.
- **Gain staging + safety notes** — headroom in Rack, limiter settings, and safe SPL targets.
- **Setup quirks** — required Rack plugins, MIDI channels, or controller mappings beyond the defaults.

## Workflow

1. Clone an existing card or start from `TEMPLATE.md` if you add one.
2. Export the Rack patch to `vcv/` and keep filenames in sync with the card.
3. Drop screenshots into `vcv/cards/media/` (create the folder if missing) and link using relative paths.
4. Commit both Markdown + media alongside any patch or config changes.

## Teaching prompts

- Have students annotate cards with sticky notes during rehearsal, then fold those annotations back into the Markdown after the session.
- Create alternate versions of the same patch mapped for different drones/channels to illustrate ensemble arranging.
- Encourage crews to log which card they flew in each session (`logs/`) so you can correlate sonic outcomes with telemetry data later.


# Sample MSP Logs

This folder is the "playback crate" for Drone Chorus workshops. Each file is a
slice of `obs/telemetry/bench_hover.mspbin`, trimmed so you can share it over
chat or drop it into a classroom repo without blowing bandwidth.

Binary logs don't survive some review pipelines, so the actual bytes live as
base64 strings in [`scripts/generate_sample_logs.py`](../scripts/generate_sample_logs.py).
Rebuild them after cloning with:

```bash
python scripts/generate_sample_logs.py
```

That command rehydrates all three `.mspbin` files into `data/`. Re-run with
`--force` whenever you want to refresh them.

| File | Vibe | Notes |
| --- | --- | --- |
| `example_log_01.mspbin` | Calm hover | The first 4 KB of the original bench capture. Mostly attitude + throttle trims. |
| `example_log_02.mspbin` | Stick jiggles | Mid-session RC wiggles to make the MIDI output visibly move. |
| `example_log_03.mspbin` | Brownout recovery | The tail end of the log where voltage sags and altitude corrections show up. |

Pair these with `examples/replay_log.py` for a guaranteed "log file → MIDI"
demo, even when you're away from the actual airframe.

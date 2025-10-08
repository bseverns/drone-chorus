# CONTROL STACK PLAYBOOK

This is the soup‑to‑nuts wiring for **flight → MIDI → Rack**.

## Signals (surface‑level map)
- **MSP telemetry** (roll, pitch, yaw proxy, throttle, RSSI, VBAT, altitude/vel)
- **Python bridge** smooths & scales → **MIDI CC** on port `DroneChorus`
- **VCV Rack** reads CC via **Core > MIDI‑CC** (one per drone or channel)

## CC plan (consistent across channels)
| CC | Meaning | Default target in Rack |
|---:|---|---|
| 14 | roll    | VCF cutoff |
| 15 | pitch   | VCO FM amount |
| 16 | yaw rate| Delay feedback |
| 17 | altitude| LFO rate / crossfade |
| 18 | RSSI    | Reverb wet |
| 19 | VBAT    | Comp threshold / tone |
| 20 | throttle| VCA amp |
| 64 | arm     | Global bypass/hold |

## Single‑drone
- Use this when you’re flying one whoop or doing bench tuning before stacking channels.
- Config: reuse the `norm` block in `config/multi.yaml` or supply `--norm-overrides` with a YAML of tweaks.
- Bridge: `software/midi-bridge/msp_to_midi.py --serial <port>` (defaults to a virtual `DroneChorus` MIDI port, channel 1).
- Rack patch: `vcv/DroneChorus_Patch.vcv` — one voice, prewired attenuverters, easy to duplicate.

## Find your MSP port
- **Linux**: plug in the quad, then rip `ls /dev/ttyUSB*`. If you see more than one hit, unplug the craft and run it again to spot the disappearing device.
- **macOS**: same hunt but with Apple flair — `ls /dev/tty.usb*`. Again, yank the cable to confirm which path vanishes.
- **Windows**: open **Device Manager → Ports (COM & LPT)** and note the COM number (e.g. `COM5`). Prefer CLI? Run `mode` in PowerShell or Command Prompt and scan the list.
- **Betaflight Configurator**: every time you jack into the quad, hit the **Ports** tab and make sure the correct USB/UART has MSP toggled on. Otherwise the bridge hears nothing and sulks.

## Multi‑drone (per‑channel)
- Config: `config/multi.yaml` — list each drone: `serial`, `channel`, optional `norm_overrides`
- Bridge: `software/midi-bridge/msp_multi_to_midi.py` (spawn via `./scripts/launch_multi.sh` when you want all drones live)
- In Rack, duplicate voice per channel; keep attenuverters modest.

## Tuning heuristics
- **Slew** hides jitter; **expo** on roll/pitch feels musical.
- Use **yaw rate** for lively micro‑movement; keep delay FB under 0.6.
- Altitude CC: we sniff **MSP_ALTITUDE** first; if the craft never sends it (no
  baro), the bridge remaps throttle into a 0–3 m envelope so CC17 keeps moving.

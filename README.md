# Drone Chorus — Telemetry‑Driven Synth (VCV Rack Edition)

**Drone Chorus** turns FPV flight into **modulation you can hear**. We read Betaflight telemetry, smooth it into **MIDI CC** on a virtual port, and let a **VCV Rack** patch sing with it. Think of it as a polite feedback loop between **airframe dynamics** and **synth architecture**.

> No breadcrumbs? No problem. This README is the field manual. Open the playbooks below in order and you’ll know which script to run, which attenuverter to twist, and where the gremlins hide.

* * *

## How to tour this notebook (a.k.a. flight school)
1. **Control Stack Playbook** — soup‑to‑nuts wiring for the pilot rig: MSP→MIDI bridge, CC maps, and per‑drone channels.  
   See: `docs/CONTROL_STACK_PLAYBOOK.md`
2. **Safety Checklist** — punk‑rock preflight liturgy.  
   See: `docs/checklists/SAFETY.md`
3. **Experience Playbook** — rehearsal tactics, musical ranges, OBS scene switching.  
   See: `docs/EXPERIENCE_PLAYBOOK.md`
4. **Assumption Ledger** — what we’re assuming (and how we’ll be wrong).  
   See: `docs/ASSUMPTION_LEDGER.md`
5. **UX Map** — what the audience sees/hears and how controls surface near the patch edge.  
   See: `docs/UX_MAP.md`

Treat that order as gospel for newcomers: prototype → secure → rehearse → reflect → repeat.

* * *

## Why this repo
- **Rapid pilot → ensemble**: start with one whoop and one voice; scale to 2–8 drones mapped to channels.  
- **Open & reproducible**: Betaflight + Python + VCV Rack; no black boxes.  
- **Performance‑ready**: OBS scene collection ships with placeholders; relink and go.

* * *

## Repo layout
```
.
├─ config/                    # YAML maps (single & multi-drone)
├─ docs/                      # Playbooks, ledger, UX map, mappings
├─ software/
│  └─ midi-bridge/            # MSP→MIDI (single + multi)
├─ vcv/                       # Starter patches (1‑ and 2‑drone)
├─ obs/                       # Scene collection (import + relink)
└─ scripts/                   # Launchers
```

* * *

## Quickstart (single‑drone)
1) **Betaflight**: Angle mode, throttle cap, failsafe; MSP enabled on your USB/UART.  
2) **Deps**:
```bash
pip install -r software/midi-bridge/requirements.txt
```
3) **Run**:
```bash
python3 software/midi-bridge/msp_to_midi.py --serial /dev/ttyUSB0
```
This creates a virtual MIDI port **DroneChorus** and streams CCs.
4) **VCV Rack**: load `vcv/DroneChorus_Patch.vcv`, set the **Core MIDI‑CC** device to **DroneChorus**, CH1.  
5) **Tune**: scale with attenuverters; adjust slew/curves in `config/mapping.yaml`.

## Quickstart (multi‑drone, per‑channel)
```bash
./scripts/launch_multi.sh
```
- Edit `config/multi.yaml` (serials, channels).  
- In Rack: one **MIDI‑CC** per drone, set channel 1..N.  
- Load `vcv/DroneChorus_2Drones.vcv` as a template.

* * *

## Telemetry → MIDI map (why the knobs wiggle)

| CC | Signal    | Where we steal it from |
|---:|---|---|
| 14 | roll      | `MSP_ATTITUDE` → Betaflight roll (deg) |
| 15 | pitch     | `MSP_ATTITUDE` → Betaflight pitch (deg) |
| 16 | yaw rate  | RC yaw channel, scaled around 1500 µs |
| 17 | altitude  | `MSP_ALTITUDE` baro height (meters); if we go deaf for >1.5 s we fake it from throttle so synth pads don’t flatline |
| 18 | RSSI      | `MSP_ANALOG` RSSI byte |
| 19 | VBAT      | `MSP_ANALOG` battery volts / 10 |
| 20 | throttle  | RC throttle channel (1000–2000 µs) |
| 64 | arm gate  | Throttle > 1050 µs means “go” |

Treat the table like a live notebook: tweak `config/multi.yaml` to adjust min/max curves when the band (or the wind) demands it.

* * *

## OBS
Import `obs/DroneChorus_SceneCollection.json`, then relink: **FPV Capture**, **VCV Rack (Window)**, **Program Audio**. Studio Mode recommended.

* * *

## License
MIT for code, CC‑BY 4.0 for docs.

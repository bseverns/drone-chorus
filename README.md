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
├─ config/                    # YAML maps (ensemble config; trim for solo)
├─ docs/                      # Playbooks, ledger, UX map, mappings
├─ software/
│  └─ midi-bridge/            # MSP→MIDI (multi-capable bridge)
├─ vcv/                       # Starter patches (2 voices; mute one for solo)
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
3) **Trim the multi config down to one voice**:
   - Open `config/multi.yaml`.
   - Keep the first block under `drones:` and either delete or comment out the rest.
   - Point `serial` at your flight controller (`/dev/ttyUSB0`, `COM5`, etc.) and lock `channel: 1`.
   - Leave the `norm` table alone unless you want to go full mad scientist.
4) **Run the bridge** (same launcher as the ensemble rig, just feeding one entry):
```bash
./scripts/launch_multi.sh
```
   That script spins up `software/midi-bridge/msp_multi_to_midi.py`, which publishes a port named **DroneChorus**.
5) **VCV Rack**: load `vcv/DroneChorus_2Drones.vcv`, set the first **Core MIDI‑CC** module’s device to **DroneChorus** on channel 1, and either mute/delete the second voice or keep it handy for when you invite a friend.
6) **Tune**: scale with attenuverters in Rack; sculpt slews/curves in the shared `norm` table inside `config/multi.yaml`.

## Quickstart (multi‑drone, per‑channel)
```bash
./scripts/launch_multi.sh
```
- Edit `config/multi.yaml` (serials, channels).  
- In Rack: one **MIDI‑CC** per drone, set channel 1..N.  
- Load `vcv/DroneChorus_2Drones.vcv` as a template.

* * *

## OBS
Import `obs/DroneChorus_SceneCollection.json`, then relink: **FPV Capture**, **VCV Rack (Window)**, **Program Audio**. Studio Mode recommended.

* * *

## License
MIT for code, CC‑BY 4.0 for docs.

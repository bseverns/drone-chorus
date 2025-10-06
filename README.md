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

## Quickstart (single‑drone bench test)
1) **Betaflight**: Angle mode, throttle cap, failsafe; MSP enabled on your USB/UART.
2) **Deps**:
```bash
pip install -r software/midi-bridge/requirements.txt
```
3) **Run the one‑off bridge** (perfect for tuning a fresh quad or rehearsing solo):
```bash
python3 software/midi-bridge/msp_to_midi.py --serial /dev/ttyUSB0
```
   - Default MIDI port: a virtual **DroneChorus** device. Override with `--midi-port MyHardware --no-virtual` if you want to hit a physical DIN box.
   - Reuse the shared scaling map from `config/multi.yaml`; drop a YAML of tweaks via `--norm-overrides path/to/my_overrides.yaml`.
4) **VCV Rack**: load `vcv/DroneChorus_Patch.vcv`, set the **Core MIDI‑CC** device to **DroneChorus**, Channel 1.
5) **Fine tune**: ride attenuverters; if you need deeper changes, clone `config/multi.yaml` and point `--norm-config` at your remix.

## Quickstart (multi‑drone, stage rig)
This is what you launch when you’re spinning up the full chorus—multiple craft, locked CC maps, each on its own channel.

```bash
./scripts/launch_multi.sh
```
- Edit `config/multi.yaml` (serial path per drone, 1‑based channel, optional `norm_overrides`).
- The launcher spawns one thread per entry, all sharing the same smoothing map.
- In Rack: instantiate one **MIDI‑CC** per drone and set channels 1..N.
- Load `vcv/DroneChorus_2Drones.vcv` as a template and keep scaling consistent.

* * *

## OBS
Import `obs/DroneChorus_SceneCollection.json`, then relink: **FPV Capture**, **VCV Rack (Window)**, **Program Audio**. Studio Mode recommended.

* * *

## License
MIT for code, CC‑BY 4.0 for docs.

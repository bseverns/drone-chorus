# OBS Scene (Import & Relink)

This scene collection is the broadcast/control nerve center for Drone Chorus. Use it for livestreams, rehearsal recordings, or classroom demos where students need to see telemetry and patch moves in real time.

## Import steps

1. OBS → Scene Collection → **Import** → select `obs/DroneChorus_SceneCollection.json`.
2. Switch to **DroneChorus Performance**.
3. Relink sources in **Properties**:
   - **FPV Capture 1** → your VRX capture device (HDMI capture card, USB dongle, etc.)
   - **VCV Rack (Window)** → the Rack window or screen region hosting the synth patch
   - **Program Audio** → your audio interface or virtual loopback bus
4. (Optional) Add a **MIDI Monitor** window capture if you want to visualize CC traffic for workshops.

## Audio routing (protect ears + recordings)

- Feed the bridge audio into a DAW or directly into OBS via the Program Audio source.
- Engage a **Limiter** filter on Program Audio (-1 dB ceiling) to prevent feedback spikes from wrecking your stream or your monitors.
- Use OBS **Monitor and Output** mode sparingly—feedback hunts are fun in theory but will fry tweeters in practice.
- If you’re running a classroom, hand out earplugs and keep SPL under 90 dB. Document your gain staging in `logs/` after each session.

## Scenes included

- **Flight Deck** — FPV feed dominant with Rack inset; great for audience view.
- **Patch Lab** — Rack full screen plus picture-in-picture FPV; perfect for teaching signal flow.
- **Telemetry Solo** — clean layout for bench testing with recorded MSP playback.

Duplicate and remix these scenes, but keep the originals untouched so you can import updates from future commits without merge chaos.

## Safety + redundancy tips

- Keep a **Fallback Slate** scene handy with a tone generator muted at -20 dB. If the quad crashes or you need to pause, switch scenes and avoid dead air.
- Log every OBS change (source switches, filter tweaks) in your pilot log so you can reconstruct issues later.
- Test capture sources with the props **off** using the `obs/telemetry` playback instructions before inviting an audience.

## Teaching hooks

- Pair this README with the [Experience Playbook](../docs/EXPERIENCE_PLAYBOOK.md) and have students run scene changes while another group pilots.
- Screenshot your scene layouts and drop them into `docs/` if you invent a new workflow worth sharing.

# Patch Card — DroneChorus_Patch

- **Name**: Drone Chorus — primary patch card
- **Screenshot**: ![DroneChorus_Patch rack sketch](media/DroneChorus_Patch.svg)

- **CC Mappings**:
  - MIDI-CC module (ch 1) listens on CC 14–20 + 64. Patch these into the left VCO/VCF/VCA as needed; attenuverters recommended to keep gestures tame.
  - MIDI-CC module (ch 2) mirrors CC 14–20 + 64 for the right voice. Great for mirroring a second drone pilot.

- **Musical Intent**:
  - Two fundamental voices meant to be flown as foreground/texture partners. Let channel 1 own the melody-ish drift while channel 2 holds a slowly moving pedal tone.
  - The included Delays are floating in the rack as bonus space-makers—patch them in when you want dubby feedback swells.
  - Punchy, slightly punk: encourage performers to overdrive filters gently but keep an eye on the mixer headroom.

- **Gain Staging + Safety Notes**:
  - Fundamental Mixer feeds Core Audio directly. Keep channel faders around noon and trim master if you start stacking delays.
  - No limiters wired—add one downstream if you’re feeding a PA. Aim to leave 6 dB headroom on the mixer meters.

- **Setup Quirks**:
  - Requires only Core + Fundamental plugins. The .vcv file ships without widget positions, so the screenshot is a schematic sketch of the module lineup.
  - MIDI device label is `DroneChorus`; channels are 1 (left voice) and 2 (right voice). Wire CC outs into filters/amps manually to taste.

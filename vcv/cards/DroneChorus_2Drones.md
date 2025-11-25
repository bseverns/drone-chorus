# Patch Card — DroneChorus_2Drones

- **Name**: Drone Chorus — two-drones formation card
- **Screenshot**: ![DroneChorus_2Drones rack sketch](media/DroneChorus_2Drones.svg)

- **CC Mappings**:
  - CC bus A: channel 1 on CC 14–20 + 64. Treat it as the lead drone; map CC 14/15 to filter cutoff/resonance and 16/17 to VCA CV for breathy swells.
  - CC bus B: channel 2 on the same CC stack. Copy mappings from A or repurpose CC 18/19/20 for detune, delay feedback, and wet/dry once you cable the delays.

- **Musical Intent**:
  - Built for paired pilots: one steers harmonic content, the other rides dynamics and space. Keep oscillators near octave offsets for quick contrast.
  - Use the free Delays as send-return shuttles between the voices; cross-patch for chaotic chorusing when you’re feeling bold.
  - The goal is a thick, slow-moving bed that can lurch into noise if you slam the filters—embrace the grit but land the plane safely.

- **Gain Staging + Safety Notes**:
  - Mixer outputs hit Core Audio unprotected. Run conservative mixer gains (<50%) and add a limiter in your host or at the end of the rack.
  - Delay feedback can runaway if you wire it; stage attenuators in between to keep things civilized.

- **Setup Quirks**:
  - Same dependency set as the primary patch: Core + Fundamental only. Layout metadata is missing, so the embedded image is a faithful schematic of the module roster and MIDI channeling.
  - MIDI device is `DroneChorus`; remember channel 1 = left/lead, channel 2 = right/support. Wire CC outs manually depending on who is flying what.

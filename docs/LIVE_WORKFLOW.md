# Live Performance Workflow

This is the soup-to-stage checklist we use when turning telemetry into noise in
front of actual humans. Read it like a studio log: every section explains why
the step exists so you can remix it without inviting chaos.

## 1. Bench proof (no props, no audience)

1. **Clone + install deps**: `pip install -r software/midi-bridge/requirements.txt`.
2. **Spin up a fake drone**:
   - Rehydrate the MSP capture with the commands in
     [`software/midi-bridge/README.md`](../software/midi-bridge/README.md#bench-playback-no-props-required).
   - Watch the bridge spew CCs in the console; tweak norms or slew until it
     feels musical.
3. **Patch VCV Rack**: open `vcv/DroneChorus_Patch.vcv`, confirm the MIDI device
   shows up as `DroneChorus`, and verify each CC lane moves something audible.
4. **Document quirks**: log latency notes, clipping, or surprises in `logs/` with
   a timestamp so the rest of the crew can follow along.

## 2. Hardware wake-up (props still off)

1. **Arm the flight stack** on USB power only. Confirm Betaflight Configurator
   sees the craft and that MSP packets increment.
2. **Run the bridge** against the real serial port. Compare behavior against the
   bench capture: if the MIDI scaling feels wildly different, fix it *here*.
3. **Check safety systems**: review [`docs/checklists/SAFETY.md`](checklists/SAFETY.md)
   and make sure the emergency kill switch is within reach.

## 3. Musical shaping

1. **Dial in attenuverters** inside Rack so full stick travel maps to tasteful
   modulation. Remember: punk is expressive, not reckless.
2. **Layer voices** if you're running multiple drones. Use `msp_multi_to_midi.py`
   and pan or EQ each voice so the audience can tell who's doing what.
3. **Record dry runs** straight from Rack or your DAW. Save take names in
   `logs/` so later editing isn't a guessing game.

## 4. OBS + showcraft

1. **Load the OBS scene** (`obs/DroneChorus_SceneCollection.json`) and confirm the
   telemetry overlay is alive.
2. **Route audio**: set Rack/DAW to feed the same bus OBS expects. Run a quick
   clap test to make sure there's no drift between visuals and sound.
3. **Title the performance** in OBS and start a local recording. If we're live
   streaming, coordinate with the person handling chat.

## 5. Go time

1. **Props on, cage clear.** Run the final call-and-response from
   [`docs/checklists/SAFETY.md`](checklists/SAFETY.md).
2. **Arm and hover**; verify throttle still gates CC64 so the patch breathes with
the craft.
3. **Perform**. Keep that notebook open—jot the wild settings you discover so the
   next gig starts from wisdom, not guesswork.
4. **Debrief** immediately afterward: note drift, RF problems, or musical ideas.

> The ethos: half lab, half punk show. Capture everything, then break it again on
> purpose.

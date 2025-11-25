# Telemetry Bench Captures (MSP)

Welcome to the poor-man's drone simulator. This folder is where we stash raw
MultiWii Serial Protocol (MSP) logs so you can rehearse the bridge without
spinning props. Treat it like a tone bank for the flight controller: each file
is a byte-perfect capture you can squirt back at the bridge to coax MIDI out of
thin air.

## `bench_hover.mspbin`

* **What it is**: 14 kB of MSP frames recorded while a Betaflight whoop idled on
the bench. Throttle blips, gentle stick wiggles, and the usual heartbeat packets
are all in there, so the bridge sees a believable hover session.
* **Encoding**: Raw binary MSP at 115200 baud. Nothing fancy—open-loop serial
as if you were plugged into the UART on the FC.
* **Use cases**:
  - **Practice the pipeline** when the quad is grounded or you're teaching in a
    classroom with zero RF noise tolerance.
  - **Regression test** MIDI mappings after tweaks to `msp_bridge.py` or the
    normalization YAMLs.
  - **Demonstrate** the project to folks without making them stare at a spinning
    death frisbee.

### Record your own captures

1. **Prep the flight controller.** Connect Betaflight Configurator (GUI or `betaflight-configurator --cli`) and run `set msp_displayport = ON` if you want richer HUD vibes piped over MSP.
2. **Wire it up on the bench.** USB tether the quad, props off, and clamp the frame if you're anywhere near spooled motors. MSP logging is chill, but a flailing quad is still a blender.
3. **Fire up the capture script.** We ship `scripts/capture_msp.sh`, a thin wrapper around `python -m serial.tools.miniterm --raw` that spits a timestamped `.mspbin` wherever you point it. Examples (pyserial required):

   ```bash
   # default 115200 baud, drops obs/telemetry/20240101-235959_ttyUSB0.mspbin
   scripts/capture_msp.sh /dev/ttyUSB0 obs/telemetry

   # crank the baud to a million on a Windows COM port, naming the file yourself
   MSP_BAUD=1000000 scripts/capture_msp.sh COM5 logs/custom_hover.mspbin
   ```

   The second argument can be a directory (the script invents `YYYYMMDD-hhmmss_PORT.mspbin`) or an explicit file path if you want to curate the name yourself. The script refuses to overwrite files on purpose; move or rename anything precious first.
4. **Skip the helper if you want.** The raw command is `python -m serial.tools.miniterm --raw <PORT> <BAUD> > yourfile.mspbin`. Turn off terminal translations/line endings if your shell tries to be “helpful” with binary streams.
5. **Document it.** Name files with the format `YYYY-MM-DD_context.mspbin`, add a few bullets about flight mode, pack voltage range, and any weirdness you noticed, then drop it in this folder and update the table above so future bridge jockeys know what tone palette they're about to ingest.

Keep props off for bench captures. If you must record in the field, secure the quad, remove props, and observe the same safety perimeter you would during live flights. Tape a note to the lipo that says “NO PROPS” if you’re forgetful—future-you is clumsy.

## Replaying the capture

The short version: stream the file into a pseudo-serial port, point
`msp_to_midi.py` at that port, and patch VCV Rack or your DAW to the virtual MIDI
output. The [bridge README](../../software/midi-bridge/README.md#bench-playback-no-props-required)
walks through platform-specific commands using `socat` and
`python -m serial.tools.miniterm`.

If you want to loop the file indefinitely for long jams, wrap the `socat`
command in a `while true` shell loop (macOS/Linux) or rerun the Windows PowerShell
one-liner whenever the music stops. Keep a notebook handy and jot down what
sonic mutations each tweak causes—future-you will thank punk-you.

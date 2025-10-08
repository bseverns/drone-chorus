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

- Connect Betaflight Configurator or `betaflight-configurator --cli` and run `set msp_displayport = ON` if you need richer HUD data.
- Use `scripts/capture_msp.sh` (coming soon) or `python -m serial.tools.miniterm --raw` to dump the serial stream to a file.
- Name files with the format `YYYY-MM-DD_context.mspbin` and add a short README snippet noting flight mode, pack voltage range, and any anomalies.
- Drop the file here and document it in the table above so collaborators know what sonic personality it carries.

Keep props off for bench captures. If you must record in the field, secure the quad, remove props, and observe the same safety perimeter you would during live flights.

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

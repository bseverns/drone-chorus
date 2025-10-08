# MSP → MIDI Bridge Studio Notes

Welcome to the synth-nerd pit crew. This folder contains the Python that turns
Betaflight telemetry into modulation you can actually jam with. Treat this as a
combo lab notebook and zine—the goal is to help you *understand* the flow so you
can mangle it into your own rig.

## Files at a glance

| File | What it does | Why you should peek |
| --- | --- | --- |
| `msp_bridge.py` | Core plumbing: reads MSP frames, smooths/normalizes values, and blasts MIDI CCs. | The inline comments read like a wiring diagram—start here if you're learning the protocol. |
| `msp_to_midi.py` | Command-line launcher for a single drone. | Shows how to load the YAML norms, open a MIDI port, and kick the bridge loop. |
| `msp_multi_to_midi.py` | Threaded launcher for multi-drone ensembles. | Demonstrates sharing one MIDI port while isolating each craft on its own channel. |

## Dependencies (keep your rig in tune)

The bridge only leans on three external libraries, all pinned in
[`requirements.txt`](./requirements.txt) so your bench tests match mine exactly:

- **`mido==1.3.3`** — MIDI plumbing without the mystery smoke.
- **`PyYAML==6.0.3`** — loads the normalization maps you scribble in `config/`.
- **`pyserial==3.5`** — keeps the MSP serial link from getting cranky.

Drop into a shell and run `pip install -r software/midi-bridge/requirements.txt`
before you start hacking; future-you (and your collaborators) will thank you.

## Study guide

1. **Normalization maps live in `config/multi.yaml`.** The scripts load them and
   optionally merge override files. Copy the block, tweak ranges, and pass your
   remix via `--norm-overrides` while testing.
2. **Smoothing is your friend.** `Smoother` in `msp_bridge.py` clamps step size
   so your CCs glide instead of sputter. Experiment with the `slew` values to
   feel how the synth responds.
3. **Gate logic rides on throttle.** When the craft is armed (throttle > 1050),
   we send CC64 = 127. Patch that into envelopes, VCAs, whatever keeps your
   patch honest.

## Quick experiments

- **Run a dry rehearsal** by pointing `--serial` at a log playback tool like
  `socat` piping from a file. The bridge doesn't care where the bytes originate.
- **Add a new telemetry field** by editing `_STATE_TEMPLATE`, `_CC_MAPPING`, and
  `update_state_from_msp`. The new CC will appear automatically once you map it
  in Rack.
- **Teach the class**: have students clone this repo, annotate their own copies
  of the YAML, and compare how different scaling curves feel on the same patch.

> Bonus punk tip: keep a notepad next to your controller and jot down the
> wildest sounds each change summons. Science + noise forever.

## Bench playback (no props required)

You can rehearse the entire MSP→MIDI chain without powering a quad. The trick is
to fake a serial port, squirt the capture through it, and let the bridge chew on
the bytes. Below are battle-tested recipes for each OS using `socat` and
`python -m serial.tools.miniterm` so students can follow along with stock tools.

### Linux (Debian/Ubuntu)

1. **Install helpers**: `sudo apt install socat`. PySerial already ships with
   `miniterm` once you install `requirements.txt`.
2. **Spawn a virtual port pair**:
   ```bash
   socat -d -d -lf /tmp/msp-pty.log \
     PTY,raw,echo=0,link=$HOME/.tmp_msp_in \
     PTY,raw,echo=0,link=$HOME/.tmp_msp_out
   ```
   Leave this running; it bridges whatever hits `_in` over to `_out`.
3. **Replay the capture** from another terminal:
   ```bash
   python -m serial.tools.miniterm --raw --exit-char=3 \
     $HOME/.tmp_msp_in 115200 < obs/telemetry/bench_hover.mspbin
   ```
   When the command exits, the MSP bytes will have traversed to `_out`.
4. **Run the bridge** against the other end:
   ```bash
   python software/midi-bridge/msp_to_midi.py --serial $HOME/.tmp_msp_out
   ```
   You should see CC spam in the console and on your MIDI monitor. Rerun step 3
   whenever you want another pass; wrap it in a `while true` loop to create an
   infinite hover jam.

### macOS (Homebrew)

1. **Install helpers**: `brew install socat`. `miniterm` is available after
   `pip install -r software/midi-bridge/requirements.txt`.
2. **Create the PTY pair** (mac devfs prefers the `tty.` prefix):
   ```bash
   socat -d -d -lf /tmp/msp-pty.log \
     PTY,raw,echo=0,link=$TMPDIR/msp_in,perm=0600 \
     PTY,raw,echo=0,link=$TMPDIR/msp_out,perm=0600
   ```
3. **Stream the capture**:
   ```bash
   python -m serial.tools.miniterm --raw --exit-char=3 \
     $TMPDIR/msp_in 115200 < obs/telemetry/bench_hover.mspbin
   ```
4. **Launch the bridge**:
   ```bash
   python software/midi-bridge/msp_to_midi.py --serial $TMPDIR/msp_out
   ```
   Bonus: open a second terminal and run `python -m serial.tools.miniterm` on
   `$TMPDIR/msp_out` to *watch* the bytes while the bridge listens—perfect for
   lessons about MSP framing.

### Windows 10/11 (PowerShell + pyserial)

We lean on PySerial's socket handler plus `miniterm` so you don't need extra
kernel drivers.

1. **Start a TCP streamer** that dribbles the capture at MSP-ish timing:
   ```powershell
   python - <<'PY'
   import pathlib, socket, time

   payload = pathlib.Path('obs/telemetry/bench_hover.mspbin').read_bytes()
   server = socket.create_server(('127.0.0.1', 7000), reuse_port=True)
   print('Streaming MSP capture on tcp://127.0.0.1:7000')
   conn, _ = server.accept()
   with conn:
       for byte in payload:
           conn.sendall(bytes([byte]))
           time.sleep(1/115200)  # approximate wire rate
   print('Done. Ctrl+C to quit or rerun to loop.')
   PY
   ```
2. **Sanity-check the stream** from another PowerShell window:
   ```powershell
   python -m serial.tools.miniterm --raw socket://127.0.0.1:7000 115200
   ```
   Hit `Ctrl+]` when you see the MSP gibberish scroll by.
3. **Aim the bridge** at the same socket URL:
   ```powershell
   python software/midi-bridge/msp_to_midi.py --serial socket://127.0.0.1:7000
   ```
   Re-run step 1 any time you want another pass; tweak the sleep value if you
   need faster/slower playback for experiments.

> Teaching tip: have everyone run the playback simultaneously, then compare how
> their Rack patches respond. Same telemetry, wildly different art.

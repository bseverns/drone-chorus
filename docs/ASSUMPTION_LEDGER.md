# ASSUMPTION LEDGER

Cross-check these assumptions against:

- [CONTROL_CONTRACT.md](CONTROL_CONTRACT.md) for the current control truth
- [CURRENT_STATE.md](CURRENT_STATE.md) for maturity labels by surface

- **A1: Slew‑limited CCs will sound more musical than raw telemetry.**  
  *Mitigation*: default slews in `config/*`; keep attenuverters < 50% until tuned.
- **A2: Per‑drone channels are simpler than per‑drone ports.**  
  *Mitigation*: one virtual port (`DroneChorus`), channels 1..N; name voices in Rack.
- **A3: Analog FPV latency is acceptable for audience mapping.**  
  *Mitigation*: keep delay effects musically under control; use latency aesthetically in OBS when desired.
- **A4: VBAT as tone control is legible.**  
  *Mitigation*: compress range in mapper; document target semantics in the UX card.

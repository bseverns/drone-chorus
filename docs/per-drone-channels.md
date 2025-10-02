# Per-Drone MIDI Channel Strategy

Assign each drone a dedicated **MIDI channel** on one virtual port (**DroneChorus**). In VCV Rack, use one **Core > MIDI-CC** per drone and set its channel accordingly.

**Example**
- Drone A → Channel 1 → Voice A
- Drone B → Channel 2 → Voice B
- Drone C → Channel 3 → Voice C

All drones share CC numbers (14–20, 64) so the patching stays consistent; channels keep lanes separated.

# Assumptions and Notes

## What this packet assumes
### Airframe scale
- **2.0 inch ducted indoor frame**
- overall outline based on a rounded-square plate
- center-to-center motor spacing in X and Y: **78 mm**
- resulting motor-to-motor diagonal: **~110.3 mm**

### FC / stack
- **25.5 x 25.5 mm** mounting pattern
- assumed M3-compatible holes at that pattern
- top deck is drawn to reuse the **same FC stack hardware** where practical

### Motor assumption
This packet assumes an **1105-class motor with a 9 x 9 mm M2 pattern**.

That is a **working assumption**, not a universal truth.
Before cutting a final plate, compare the actual motor drawing to:
- the 9 x 9 hole pattern
- screw diameter
- screw head clearance
- stator / bell diameter relative to any local plate edges

If you choose a different 1105 or 1204 motor, revise the motor islands first.

### Duct / guard reference
- duct ID guide circle: **52 mm**
- duct OD guide circle: **57 mm**

These circles appear in the overlay and bottom plate as **references**.
They are there to help shape future guards / duct structures.
They are not automatically the only correct duct answer.

### Battery intent
- **2S**
- preferred starter pack envelope: roughly **18–22 mm wide** and **55–70 mm long**
- the strap slots are deliberately simple and should be checked against the actual chosen pack and strap width

### Camera
This packet does **not** pretend to know your exact analog camera.
Instead it provides:
- a forward camera zone in the overlay
- a separate **camera bracket blank**
- centerline references so you can adapt it once the actual camera is chosen

That is more honest than baking in the wrong hole pattern.

## Why this geometry is the way it is
The SpeedyBee board is relatively large for a 2.0 inch build.
So the frame is biased toward:
- central mass
- short wire runs
- minimal decorative bulk
- reusing existing stack hardware where possible

## Firmware-oriented note
A target named **`SPEEDYBEEF745AIO`** exists in the iNav source tree and includes:
- multiple UART definitions
- onboard barometer support
- SPI flash blackbox support
- LED strip support
- MSP rangefinder and MSP optical-flow declarations

Reference:
https://github.com/iNavFlight/inav/blob/76809d7f11deb08faccdd3d593d84fa67f2bf791/src/main/target/SPEEDYBEEF745AIO/target.h

That does not make the airframe design “done,” but it is a good sign for your longer arc.

## What to verify before cutting real material
1. Exact AIO board outline and keep-out zones
2. Exact motor mount pattern
3. Actual battery dimensions
4. Actual camera body and lens protrusion
5. VTX location and antenna exit path
6. Whether top-deck clearance is enough for wiring bends
7. Whether the FC can comfortably share hardware with the top deck in your chosen stack scheme

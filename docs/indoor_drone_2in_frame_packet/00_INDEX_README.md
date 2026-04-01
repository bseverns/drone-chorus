# Indoor Drone 2.0in Frame Packet
This packet splits the first-pass frame work into separate editable files so the geometry remains readable and adaptable.

## Files
- `00_INDEX_README.md` — this overview
- `01_ASSUMPTIONS_AND_NOTES.md` — what was assumed, what must be verified
- `10_BOTTOM_PLATE.svg` — first-pass structural bottom plate drawing
- `11_TOP_DECK.svg` — top deck / bridge drawing using the FC stack holes
- `12_LAYOUT_OVERLAY.svg` — non-cut planning overlay for wiring, camera zone, and reserved spaces
- `13_CAMERA_BRACKET_BLANK.svg` — front camera bracket blank to adapt to the actual camera
- `20_HOLE_SCHEDULE.csv` — coordinates and hole notes

## Intent
This is not presented as a production-ready drone frame. It is a **legible, editable first-pass** around:
- 2.0 inch ducted indoor build
- SpeedyBee F745 35A BLS 25.5x25.5 AIO
- 1105-class motors as the first assumption
- 2S 450–550 mAh battery intent
- analog FPV
- ELRS
- restrained version-1 lighting

## Coordinate convention
All SVG dimensions are in **mm**.
Origin is the **top-left** of each drawing.
The bottom plate drawing is centered in a **150 x 150 mm** canvas.

## Fabrication posture
Prototype first in:
- birch aircraft ply
- or G10 / FR4 if your extraction / PPE situation is truly good

Only harden the design after:
- board fit is confirmed
- battery fit is confirmed
- motor pattern is confirmed
- wire paths are confirmed

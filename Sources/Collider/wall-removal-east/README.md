# East-wing concrete screen removal — 27 October 2026

Removed the matching east screen at plan e 1500..1524, n -160..160,
z 0..164. Both freestanding wing screens are now absent.

The existing guarded migration accepts `--side east` and stages into
`output/collider/wall-removal-east`. It removes exactly 12 triangles and one
collision box from the currently installed structure, preserving every other
OBJ/ModelDoc byte. The minimap is updated from published collision after the
pre-edit radar passes an exact pixel comparison. The generator no longer
places either screen. Matching primary build-stage files are synchronized.

The native importer preserves the existing unsaved scene and does not save
or rewrite its document. The capture accepts the four base models alongside
additional authored props, including the concurrent automatic-door leaves.

The model compiles and is current. Nine rays through this wall are clear,
and the nine reference rays through the previously removed west wall remain
clear. All 68 authored positions retain support, clearance and reachability.

This removal opens two Retakes A spawn sightlines: defender plan
(-1120,100,257) to attacker positions (1640,-100,1) and (1640,0,1).
Both are confirmed clear by native standing-eye traces. Spawn positions are
outside this wall-removal migration; the finding is recorded in validation.

Run `Sources/Collider/wall-removal/verify.py --side east` for the final receipt
in `installed.json` and `output/collider/wall-removal-east/validation.json`.

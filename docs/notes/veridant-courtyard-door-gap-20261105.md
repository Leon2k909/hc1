# Veridant operations courtyard doorway gap — fixed 2026-11-05

The north door of the operations hall (plan e=280..360, n=-336..-320)
showed the sea/void at its foot. Two surfaces were absent: the hall floor
through the wall reveal, and the south-facing riser of the raised courtyard
deck (n=-320, z=0..14.5). The deck's cap already covers z=14.5..16.

`Tools/veridant_door_threshold.py` builds a four-triangle patch using the existing
`vr_floor` and `vr_stone` materials. It preserves the buildings UV origin.
The native editor imported and compiled the asset and saved one renderer named
`Operations courtyard doorway threshold` in `veridant.scene`.

The original ground collider already covers the doorway at z=0; a downward native
trace at world (-328,-320,12) hit Ground at (-328,-320,0). No extra collider was added.
`Tools/veridant_map.py` now emits both surfaces directly for future map regeneration;
a regenerated scene replaces the separate repair object with those baked faces.

Matched-camera before/after images and a pre-edit scene backup are in
`output/veridant/door-threshold-fix/`. The scene was saved and play mode restored.

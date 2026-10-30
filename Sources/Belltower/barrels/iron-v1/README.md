# Barrel hoop finish — 27 October 2026

The private `barrel_hoop_rust.vmat` now uses the existing weathered iron colour,
normal and roughness maps, a restrained charcoal tint and metalness 0.4. This
replaces the broad red rust finish while retaining scattered brown corrosion
and small worn-metal marks. Both town halves already reference this material.

`Tools/belltower_barrels_v3.py` preserves the finish on regeneration. Publication
used the native editor, with the original material and checksums backed up under
`output/belltower/barrel-iron-v1/stage/before`. Native compilation and the
up-to-date asset check passed. Installed native views are in
`output/belltower/quality/barrel-iron-v1-installed/`: `clock-west-north.png`
and `yard-daylight.png`. The earlier `clock-west.png` view was obstructed.

Only the private material and its generator definition changed. Shared Stillhouse
materials, texture files, barrel geometry and collision were not edited. No scene
save was performed; the shared editor's existing unsaved work was preserved.

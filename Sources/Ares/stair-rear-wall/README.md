# Ares stair rear closures

Added steel cladding to the missing tall rear faces of both hall and both wing
stairs on 26 October 2026. The existing stair wedge already provides collision;
these panels sit inside it and add no colliders. Their top meets the underside
of the landing at z 192. Shallow sheet joints, edge angles and a floor kick close
the formerly open box. The separate asset contains 1,872 triangles.

Corrected on 30 October 2026, after the user saw a corner z-fighting. As first installed, the panels' end caps lay exactly
on the stair walls, on both sides of all four stairs, and the bottom sheet overlapped the floor kick a quarter inch apart.
The generator now leaves those end caps out and starts the sheet above the kick. `Tools/ares_refresh_stair_cladding.py`
rewrites the installed OBJ (the old one is in `output/ares/stair-rear-wall/before-zfight-fix/`), and
`Sources/Ares/audit_overlaps.py` lists faces that nearly coincide. Checked in the engine from the same side as the report.

`Tools/ares_stair_cladding.py` builds the closures. `ares_map.stair()` calls the
same helper for future full map builds. The installed map uses one separate
`Stair Rear Closures` ModelRenderer child of `Structure`, referencing
`models/maps/ares/stair-rear-wall/ares_stair_rear_closures.vmdl`.

The existing hall VMDL, canonical OBJ and private base import were not changed.
The separate asset was registered and compiled through the native editor, then
placed with its undoable `spawn_model` tool and saved with `save_scene`.
All 40 physics traces match their before results, including the routes behind
the landings. The editor camera and stopped play state were preserved.

Receipts, the original scene backup, input hashes, staged model sources and
before/after screenshots are under `output/ares/stair-rear-wall`.
The native save also refreshed one prefab-root mapping key in each of the two
game-mode instances; every mapped instance ID and all other existing object
properties were retained. No game-mode or prefab sources were edited.

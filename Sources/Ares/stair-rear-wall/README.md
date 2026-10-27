# Ares stair rear closures

Added steel cladding to the missing tall rear faces of both hall and both wing
stairs on 26 October 2026. The existing stair wedge already provides collision;
these panels sit inside it and add no colliders. Their top meets the underside
of the landing at z 192. Shallow sheet joints, edge angles and a floor kick close
the formerly open box. The separate asset contains 1,936 triangles.

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

## Spillway's yard pallets v2 (`pallet_v2`, by container 02, 2026-11-03)
- The old "pallet" in `spillway_map.cargo_yard()` was seven flat grey slabs (`rv_desk` boxes) floating 2 in off the floor beside
  container 02, with no collision. Picked from s&box shots of the yard's props, as the crudest one there.
- `models/maps/spillway/pallet_v2/pallet.vmdl` is a used 48 x 40 x 4.75 in stringer pallet: notched stringers, seven top and three bottom
  boards, nails, a chipped corner and one paler mended board, off-centre so pallets turned end for end differ. 964 / 482 / 192 triangles
  (LODs at 30 and 80), one 2048 atlas at 25 px/in, painted from Poly Haven's CC0 `wood_planks` scan in `materials/forestbase/scans/` at
  true scale, each board face from its own stretch of plank. One box collider, surface `wood`.
- Installed at the user's word ("Yes, install it") after same-camera before and after shots in s&box, in sunlight and in place:
  the slabs' 84 faces are cut from `spillway_cargo.obj`, and the scene has `Yard Pallet 1-4` under `Spillway`: singles at plan e -258 and
  -139, a stack of two at e -198, n about -688. `Tools/spillway_map.py` places the same four in `scene()` and no longer draws the slabs,
  but the map's script isn't rerun (as for the control desks, note 178).
- New collision: players step over them (4.75 in, 9.5 for the stack) and bullets stop on them, where the slabs had none.
- Checked in s&box in an isolated editor scene loaded from the installed scene file: 4 pallets with colliders, no error models, the slabs
  gone, and 7 rays as expected. Not seen in a match.
- Sources and how to rerun: `Sources/Spillway/cargo-props-v2/README.md`. Rollback copies of the OBJ and scene:
  `output/asset-improvement-20261030/spillway-cargo/retired/`.
- For clearer comparisons of a prop merged into a map model: `Materials.SetOverride( slot, material )` on the map's renderer, with an
  alpha-tested material that cuts everything (`F_ALPHA_TEST 1`, translucency 0), hides just that prop's slot. An `F_TRANSLUCENT` one at
  opacity 0 still drew dark boxes. `compare2.py` did this, with the old prop cut into its own model for a sunlit pair beside it.

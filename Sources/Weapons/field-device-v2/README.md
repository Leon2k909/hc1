# Field device v2

Created 2026-10-30. The rebuilt Tactical Defuse objective prop. The user compared it with the old one and chose it ("yeah new
one is better"), so `vm_c4`, `wm_c4`, `planted_c4`, `mount_c4` and `weapon_c4.prefab`, `c4.equip` and
`Tools/configure_defuse.py` and `configure_defuse_world.py` now use it. The old `Assets/Weapons/C4/field_device/` is still
there, unused, as the rollback: to go back, change those eight files' path back. `Tools/build_field_device.py` still makes it.

The old model is 2,160 triangles and one colour map, with flat canvas boxes and a metal plate with its display painted on.
This keeps its layout and rebuilds it: a moulded rubber tray with corner bumpers and grip ribs, three padded canvas pouches
pulled down by two webbing bands, cam buckles, a cast housing, a control plate with a real keypad well and a window recess,
keys within 0.03 of the old centres at the old size, and socket screws where the old fasteners were.

It stays a fictional sealed prop: no ports, no wiring, nothing that opens. All lettering is invented and plainly descriptive
("FIELD UNIT 04", "SEALED ASSEMBLY", "LOT 7731 D", a made-up hexagon mark). The old panel's "RAZED" is gone, because the brief
asked for no game brands. Say if you want the game's own name back on it.

## What changed in the layout

- Bands moved from x = 4.8 to 5.2 and narrowed from 1.15 to 1.0, because at the old position they ran through the housing's edges.
- The buckles moved with them, and the bands come down into the corner bumpers rather than separate blocks.
- Bounds are the old model's within 0.002: 12.4 x 11.4 x 4.17, same origin and axes (`verify_device.py` prints both).

## Files

- Triangles: 29,258 / 10,844 / 4,341 / 1,170 (LOD 0-3). LOD 0 keeps 9,138 faces no one can see, so its shells stay closed for
  `check_outward.py`. They still cost draw time, and the other LODs drop them.
- One material, `fd_device`, one 2048 atlas: colour, normal, roughness, metalness, AO, and a glow mask for the window and
  lamp. About 44 px/in, and 75 on the plate, keys, window and data plate. The old panel is 70 by 85 in a 1254 atlas, so the
  plate is about level with it, not sharper. Canvas, straps and housing are where the gain is.
- `device.py` builds, bakes and exports. `paint_device.py` paints. `render_device.py` and `make_sheets.py` make the
  comparison. `verify_device.py` checks the files. They import `Sources/Gameplay/capture-flag-v2/`'s `build.py` and `paint.py`.
- Rerunning the build can change the unwrap, so bake and paint after it. The export refuses to run otherwise.
- Work files and renders are in `output/asset-improvement-20261030/field-device/`.

## Checked

From the files, by `verify_device.py`: 0 of 122 solid pieces inside out on LOD 0 (it caught a real one in the first build, the
extrude's leftover lid over the keypad well), bounds, normals, UVs in range, key positions, every texture and mesh the vmat
and vmdl name exists, and all eight users ask for v2 and not the old path. I looked at Blender renders of LODs 1-3 from one
angle: no holes.

## Not checked

- **Seen in the editor only, on the floor beside the old one**, on 2026-10-30, and the user kept it. That look found the data plate's lettering mirrored, since fixed. It hasn't been seen in a match, in a player's hands or planted.
- The sheets' images are Cycles renders of the exported files, with ray-traced light that flatters any asset, and the old model
  is given the kinder reading of its missing normals.
- Whether it fits the hands in first person. The size and origin match, but no one has seen it in the view model. The sheets'
  "operator's side" camera is an estimate, not the game's.
- The vmat's self-illumination (`F_SELF_ILLUM` and the mask) compiled alongside `F_METALNESS_TEXTURE`, but hasn't been seen lit.
- `switch_threshold`s (40, 120, 300) are estimates, set high so the first LOD change shouldn't happen in the player's hands.
- `planted_c4.prefab`'s `Wires` line renderer wasn't checked against the new shape.
- `weapon_c4.prefab`'s stored `Mins` and `Maxs` were already stale for the old model and are left as they were.

## Known weaknesses

- The window washes out to pale blue at three-quarter and operator's-side angles under the renders' open sky, with the amber
  line low in contrast. From above it's crisp. It depends on what the surface reflects, so judge it in a map. If it stays pale,
  raise `g_flSelfIllumBrightness` or darken the film's roughness.
- Close up, the plate is cleaner and plainer than the old one's painted grit. The keys are soft and rounded, which is a choice
  you may not share.
- The red seal and white lot block are the loudest things on it. Both are paint only, so they're cheap to remove.
- Faces that take no atlas, including the whole underside, are plain dark rubber.
- LOD 3 has no keys, screws or guards, so the keypad is a dark square in the plate. It's meant for far away, but the distance is
  an estimate.

## Packing

The toolkit's shelves fill only about a third of the atlas here, because the big plate island wastes its row. Blender's own
packer did worse (AABB 37 px/in, exact shape 41, shelves 44), so the shelves stay. A proper packer is the way to more
density if the plate ever needs it.

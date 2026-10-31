# Boxyard skip v2: review candidate

Created 2026-10-30 for the user's review. **Nothing plays this model yet, and it isn't in Assets.** `boxyard_map.skip` still draws the old
skip into Boxyard's merged props. Nothing is committed.

Why this one: it was the crudest thing left in Boxyard, a tight map where players stand right next to its props. The old skip, 154 faces, is four
flat slabs, a rim and two stubs.

The new one is welded up like a real chain-lift skip: dented plate walls with pressed ribs, a knocked-about square rim, corner posts, lifting trunnions on
gussets, forged rings on the raked ends, two runners, cross members, and some rubble left on its floor. Paint is fleet green over an older yellow over
steel, with gouges, rust rising from the bottom and streaks running down from the rim. The inside is scoured back to brown steel.

- Triangles: 9,668 / 5,800 / 3,026 / 1,554 (LOD 0-3). One placed.
- Same size: bounds are within 0.02 in of the old skip's. Its origin is on the ground at its centre, where the old one had none of its own (see below).
- Collision is the old skip's: the same four wall hulls (checked point by point) and the same floor box. The rubble has no collision, so a player who
  climbs in stands on the floor with their feet in it. It's only a few inches deep.
- One material: colour, normal and roughness at 4096, metalness and AO at 2048. About 17 px/in on the outside.
- Every word is made up. TARVEN is invented, and 01632 960xxx is the UK phone range set aside for fiction.

## Files

- `skip.py` builds, bakes and exports. `paint_skip.py` paints. `render_skip.py` and `make_sheets.py` make the sheets. `verify_skip.py` checks the files.
  `finish.ps1 [-Build]` runs them in order at idle priority.
- Toolkit: `Sources/Gameplay/capture-flag-v2/`'s `build.py` and `paint.py`, imported, not edited.
- Work files, renders, sheets and the export are in `output/asset-improvement-20261030/skip/`. `skip_v2/` there is laid out like Assets.
- Rerunning the build can change the unwrap, so bake and paint after it. The export refuses to run otherwise.

## Checked, from the files only

`verify_skip.py` passes: `check_outward.py` reports 0 inside out on LOD 0, bounds match, the collision hulls match the old hull file's points, every
texture and file the vmat and vmdl name exists, and the old skip's own 154 faces are as committed. The lettering was read in the renders.

The old skip's walls have a face on each side in one plane, which Cycles can't tell apart, so its renders move each old face 0.03 in along its own normal.
Without that the walls came out black or missing, which the engine wouldn't show.

## Not checked

- **Never compiled or seen in s&box.** No `_c` files exist for it. The images are Blender Cycles renders, which flatter any asset.
- The LOD switch distances (15, 40, 90) are estimates.
- Collision has only been compared as numbers, never walked into or shot.
- Its lighting in Boxyard, which is a different scene from the renders' plain yard.

## To adopt it

1. Copy `output/asset-improvement-20261030/skip/skip_v2/models` and `materials` into `Assets`.
2. In `Tools/boxyard_map.py`, remove the `skip( m, -555.0, 675.0, 0.0 )` call from `props()`, and add a scene object with
   `models/props/boxyard/skip_v2/skip.vmdl` at engine (675, 555, 0), turned -90 degrees so its +X is the map's east, with a renderer and a collider.
3. Rebuild the map, compile, and check it in Boxyard.

# Riverside's teddy v2

Created and installed on 2026-10-31 at the user's word ("Yes, install it") after a before and after rendered by s&box. Seen as installed in an editor capture under the map's own light, but
**not yet in a live match**. Nothing is committed.

## Why this one

Candidates were picked by looking at them as the game draws them, in an isolated editor scene under the map's own light. The teddy from the reference picture was the worst:
`riverside_parts.teddy` makes it from eight 8-sided lumps (720 triangles) with visible facets and no face, so it doesn't read as a bear at all. It sits in the mud beside the cooler,
by the player spawn. The propane bottles and crates are crude too, and are worth doing next.

## What it is

A child's plush bear, sat where it was dropped with its head tipped over. One soft skin from metaballs, so its limbs run into its body like stuffed cloth. It has a stitched nose and mouth,
one button eye with the other hanging by a thread, a faded red ribbon with a knot, and stuffing coming out of a split seam. Short, even brown fur in the old teddy's colour, paler felt on the
muzzle, ears and foot pads, painted seams, and dark matted mud only low down. No lettering.

## Numbers

- Triangles: 4,770 / 2,384 / 748 (LOD 0-2), against 720 and no LODs. One on the map.
- One material, one 2048 atlas: colour, normal, roughness, metalness, AO, at about 42 px/in. That's generous for one small prop, and close-up fur is why. It could drop to 1024.
- Faces local +x, origin on the ground under its seat. It belongs at engine (-215, 24, 96), yaw -153.43, which is where and how the old one faces.
- Height 18.9 against 17.3. It reaches 10.1 forward against 5.9, since its legs now stick out in front, and 8.8 to each side against 7.2. Nothing is in the way of that.
- No physics, as the old one had none: players walk through it, as they do now.

## How it's installed

- `riverside_parts.teddy` now only records a placement, and `riverside_map.py` writes a `Teddy` object beside the `Cooler`. `riverside_parts.blob`, which only the teddy used, is gone.
- **`riverside_map.py` wasn't rerun, because that isn't safe now** (note 163). `install_teddy.py` cuts the 720 `rs_teddy` and `rs_teddy_dark` triangles from `riverside_pad.obj` and adds the
  object to the scene. It stops if the faces aren't the old teddy's, and it's safe to rerun.
- The old materials are still there, now unused.
- To roll back: restore those faces in `riverside_pad.obj` from git (`riverside_pad-before-install.obj` in the work folder has them), remove the scene's `Teddy` object, and restore `teddy` and
  `blob` in `Tools/riverside_parts.py` and its call and `teddy_objects` in `Tools/riverside_map.py`. A plain `git restore` of those files would take the burn drums and cooler out too, unless they're
  committed first.
- `old_teddy.py` and `capture_engine.cs.txt` need the old teddy still in the pad, so they no longer run as they are. Their results are kept in the work folder. `capture_installed.cs.txt` shows it now.

## Files

- `Assets/models/zombies/teddy_v2/`, `Assets/materials/zombies/teddy_v2/`: the model and maps.
- `teddy.py` builds, bakes and exports, with `drum_pack.py` from the burn drum's folder. `paint_teddy.py` paints. `old_teddy.py` cuts the old teddy from `riverside_pad.obj`, reading only.
- `capture_engine.cs.txt` and `make_engine_sheets.py` make the engine comparison. `render_teddy.py` is the quick Blender look used while working. `verify_teddy.py` checks the files.
- Work files and shots: `output/asset-improvement-20261030/teddy/`, with the engine's in `engine/`.

## Checked and not checked

From the files (`verify_teddy.py`): `check_outward.py` on LOD 0 (19 solid pieces, 0 inside out), the bounds and ground contact of every LOD, every file the vmdl and vmat name, no physics, the
scene places it, and the old faces are gone.

In s&box 26.10.27c, in an isolated editor scene built from `riverside.scene`'s own moon, sky, fog, lights and post-processing, with exposure held at the map's ceiling of 3.5 for a matched before
and after. The old teddy's materials were hidden on the pad's model for "after", and nothing was saved:

- It reads as a teddy close up, from a player's eye height and from across the pad, and sits right beside the cooler and lantern.
- The engine showed three faults Blender hadn't, all fixed: ribbon corners jutting out over the shoulders, felt patches reading as flat pale discs, and a visibly octagonal nose.
- As installed, from `riverside.scene` and the recompiled pad model: the new teddy is there, the old one is gone from the pad, and there are no error models. `riverside_pad.vmdl` and `riverside.scene`
  recompiled by themselves within two seconds of the install.

**Not checked:**

- **A live match.** Play was left alone, so real auto-exposure is unseen.
- Whether the LOD thresholds (0, 20, 60, copied from the town house doors) switch at sensible distances.
- The stuffing, the side of it that faces away in these shots, was only seen in Blender.

# Riverside's cooler v2

Created 2026-10-30 and installed on 2026-10-31 at the user's word ("23. cooler new better") after they compared the two side by side in s&box. Seen in
the engine under the map's own light in an editor capture, but **not yet in a live match**. The 2026-11-04 detail pass is approved
and installed at the same model path; obsolete model and comparison files have been removed.

## Why this one

It's in Riverside's reference picture, standing in the dog run's gate by the player spawn, with SOME THINGS SHOULD STAY FORGOTTEN in marker inside its
lid. `riverside_parts.cooler` made it from three boxes and four cans (136 triangles).

## What it is

A moulded ice chest: rounded, drafted walls with a band round them, a hollow liner, and a hollow lid hinged open at the old angle. It has swing handles, a
drain plug, latch keepers and steel hinge pins, with five cans floating in old meltwater and a tide mark up the liner. The plastic is sun-chalked and
scuffed, with mud up its sides, and the lid has yellowed.

The lid's lettering is the reference picture's words in the same hand, cropped from `rs_signs` by `old_cooler.py`. The only other marking is a moulded
"100 QT", which is invented.

## Numbers

- Triangles after the 2026-11-04 detail pass: 4,328 / 2,582 / 624 (LOD 0-2), up from 2,968 / 1,766 / 624. One on the map.
- One material, one 2048 atlas: colour, normal, roughness, metalness, AO. About 34 px/in on the lid's underside and 22 on the body. That's generous for one
  small prop, so it could drop to 1024 if texture memory matters.
- Same axes as the old one once placed (its length along x, its open side +y, origin on the ground under its middle), and the same lid angle. Its bounds are
  within half an inch of the old one's in every direction.
- No physics in the vmdl: the box in `riverside_pad.vmdl` stays its collision.

## How it's installed

- `riverside_parts.cooler` now keeps only its collision box and records a placement, and `riverside_map.py` writes a `Cooler` object beside the "Burn Drums"
  group, at (-170.87, 23.45, 96), yaw 165.5.
- **`riverside_map.py` wasn't rerun, because that isn't safe now** (note 163). `install_cooler.py` asks the map's code where the cooler is, cuts exactly its
  136 triangles from `riverside_pad.obj`, and adds the object to the scene. It stops if the faces aren't the old cooler's, and it's safe to rerun.
- The old materials are all still there. `rs_cooler` and `rs_cooler_white` are now unused.
- To roll back: restore the cooler's faces in `riverside_pad.obj` from git, remove the scene's `Cooler` object, and restore `cooler` in
  `Tools/riverside_parts.py` and its call and `cooler_objects` in `Tools/riverside_map.py`. `git restore` of those whole files would take the burn drums
  back out too, unless they're committed first.
- The obsolete `models/compare_old/old_cooler.vmdl`, its mesh inputs and the gallery's OLD cooler group were removed after approval.
  Validation keeps only the retired cooler's recorded bounds, so it no longer needs the old mesh.

## Files

- `Assets/models/zombies/cooler_v2/`, `Assets/materials/zombies/cooler_v2/`: the model and maps.
- `cooler.py` builds, bakes and exports, with `drum_pack.py` from the burn drum's folder. `paint_cooler.py` paints. `render_cooler.py` and `make_sheets.py` make
  the Blender comparison. `verify_cooler.py` checks the files. `install_cooler.py` swaps it in.
- `capture_engine.cs.txt` and `make_engine_sheet.py` make the engine comparison, and `collision_check.cs.txt` tests collision, both in an isolated editor scene.
- Current work files: `output/cooler-detail-20261104/work/`; approved native shots: `output/cooler-detail-20261104/after/`.

## Detail pass (2026-11-04)

- Each can now has a raised ring pull tab and anchor, with scored lid detail and less mirror-like aluminium on the end panel.
  The tabs are built in each can's own frame, so they follow its tilt. The closer can meshes use 16 sides instead of 12.
- The cooler's swing handles have moulded centre grips with ribbed surface detail. They extend about 0.11 inches farther
  than the previous handles; the footprint still fits the existing collision. The far LOD remains 624 triangles.
- Mesh inputs and all five atlas maps were rebuilt at the existing asset paths; `export-meshes` preserves the ModelDoc
  and material resources. The lid lettering, placement, and map collision stay the same.
- Native full model/material compilation succeeded. Approved isolated engine captures are in
  `output/cooler-detail-20261104/after/`, with the current build and bake inputs in `work/`.
  Offline checks passed for bounds, outward winding (38 solids), asset references, scene placement, and collision.
- `verify_cooler.py` accepts both string and structured model references, and compares the pad's actual physics blocks
  and hull files so another prop's material-remap edits do not falsely report a collision change.

## Checked and not checked

From the files (`verify_cooler.py`): `check_outward.py` on LOD 0 (38 solid pieces, 0 inside out), bounds of every LOD against the old one, ground contact, every
file the vmdl and vmat name, no physics in the vmdl, the scene places it, the old faces are gone, and the pad's collision files are unchanged.

In s&box 26.10.27c, in an isolated editor scene built from `riverside.scene`'s own moon, sky, fog, lights and post-processing, with exposure held at the map's
ceiling of 3.5 for a matched before and after:

- Under the map's dark light it reads well, and no brightening was needed. The old body nearly vanishes into black there; the new one reads as a blue cooler,
  with the lid's lettering clear and the cans visible, from both close up and a player's walking distance (`engine/`).
- The "100 QT" reads the right way round. It's faint, as a moulded mark should be.
- Collision, by rays against the compiled map: the top at z 112 in plastic, the front 8.5 in out, and the ground beside it still dirt at z 96.
- `riverside_pad.vmdl` and `riverside.scene` recompiled by themselves within a second of the install, with no errors for them in the log.

**Not checked:**

- **A live match.** Play was left alone, as other sessions share the editor. So real auto-exposure and a player walking up to it are unseen: the capture holds
  exposure at 3.5 rather than letting it settle.
- Whether the LOD thresholds (0, 20, 60, copied from the town house doors) switch at sensible distances. The LODs themselves were only seen in Blender.
- The water is an opaque glossy surface, not transparent. In the map's light it reads as near black, which suits it, but it's a judgement call.

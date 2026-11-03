# Spillway yard hose v2

Built and **installed 2026-11-03**, following approval of the matched comparison. Nothing committed.

Selected from s&box's Spillway prop captures after the canvas cover installation. The current hose in `cargo_yard()` is three separate,
closed elliptical rings made from five-sided rod segments: 930 triangles, with conspicuous joins and no hose ends or couplings. It is
centred at plan e 90, n -1080 on the yard floor, roughly 106 x 54 in across. Its material is the cargo model's shared `rv_dark` slot.

The replacement is one continuous 2.65-turn rubber hose, about 51.6 ft along its centreline, with two loose ends, a hollow female cam
coupling and male adapter, crimp ferrules, folded cam arms, retaining rings, inner lining and a seal. The material adds subtle rubber
grain, scuffs and floor grime, dull cast alloy, steel pins, a faded yellow identification wrap and restrained WATER TRANSFER / 50 mm
lettering. No logos, external textures, image generation, or new libraries.

- Engine units are inches, origin on the floor; place with no rotation at engine `-1080,-90,0`.
- Bounds in local engine axes: X -23.49..25.51, Y -49.57..48.78, Z .05..3.85. It fits inside the original plan footprint.
- Triangles LOD 0/1/2: 16,132 / 8,066 / 2,818, thresholds 30 / 80. One material, one 2048 atlas, 23.7 px/in and 66% coverage. The count
  includes the real hollow couplings and close-up geometry; it is substantially higher than the original rings.
- No physics shapes or collider. The old hose had no collision; installation keeps that behaviour.
- Native s&box asset compilation succeeds. Outward-face check: 23 connected pieces, no inside-out triangles. Five matched cameras
  (standing, low, above, fittings, far) rendered in an isolated editor scene from Spillway's saved visual roots. No saved scene edits,
  no gameplay session, no active viewport changes. Exposure held equally before and after. Model atlas streamed at 2048, map at 1024
  to keep editor memory use down.

Sources: `hose.py` uses the pallet's verified build/bake/OBJ pipeline and the capture flag's mesh toolkit. The hose gets its own unrolled
UV strips with seams underneath before real-scale packing. Intermediate Blender objects, bake array names and `pallet.json` retain the
shared pipeline's internal prefix. Descriptive hose dimensions are in `hose.json`. `paint_hose.py` uses the baked world position,
normal, part identity and AO; maps are all procedural. Export explicitly removes the generic pipeline's pallet physics block.

From the canonical project root, run these sequentially (Blender helper runs hidden at idle priority on four threads):

```powershell
rtk proxy powershell -NoProfile -File Sources/Belltower/props/pew-v2/blender_idle.ps1 -Script C:/sbox-projects/hc1/forked-shooter-main/Sources/Spillway/hose-coil-v2/hose.py -Log C:/sbox-projects/hc1/forked-shooter-main/output/asset-improvement-20261030/spillway-hose-build.log C:/sbox-projects/hc1/forked-shooter-main/output/asset-improvement-20261030/spillway-hose C:/sbox-projects/hc1/forked-shooter-main build bake
rtk python Sources/Spillway/hose-coil-v2/paint_hose.py C:/sbox-projects/hc1/forked-shooter-main/output/asset-improvement-20261030/spillway-hose C:/sbox-projects/hc1/forked-shooter-main/Assets/models/maps/spillway/hose_coil_v2
rtk proxy powershell -NoProfile -File Sources/Belltower/props/pew-v2/blender_idle.ps1 -Script C:/sbox-projects/hc1/forked-shooter-main/Sources/Spillway/hose-coil-v2/hose.py -Log C:/sbox-projects/hc1/forked-shooter-main/output/asset-improvement-20261030/spillway-hose-export.log C:/sbox-projects/hc1/forked-shooter-main/output/asset-improvement-20261030/spillway-hose C:/sbox-projects/hc1/forked-shooter-main export
rtk python Sources/Spillway/hose-coil-v2/prepare_review.py
rtk python Sources/Spillway/hose-coil-v2/review.py compile
rtk python Sources/Spillway/hose-coil-v2/review.py capture
rtk python Sources/Spillway/hose-coil-v2/sheets.py
rtk python Sources/Spillway/hose-coil-v2/review.py check
```

All work/captures: `output/asset-improvement-20261030/spillway-hose/`; main sheet `matched/comparison.png`. `native.py` attaches to the
existing editor, puts scripts in that session's exchange directory, disconnects, and removes the exchange files. It never owns or closes
the editor. The comparison script destroys its isolated scene in `finally`.

Temporary comparison resources: `Assets/models/compare_old/spillway_hose_v2/old_hose.*` and `cargo_dark_rest.*`. They preserve all original
UVs and normals. For "after", the cargo model's shared `rv_dark` slot is hidden with the existing shared `hidden.vmat`, then the 4,258
other dark faces are put back unchanged; only the 930 hose faces disappear. Keep the shared hidden material for other reviews.

Installed by guarded `install.py` while the editor was closed: exactly 930 faces removed, all other OBJ lines unchanged, one `Yard Hose`
renderer added under `Spillway` at the placement above, and the generator updated without rebuilding the map. Static checks confirm the
saved scene differs only by that object and no collider was added. Native installed checks and comparison archive are pending editor
startup. Pre-install backups of the mesh, scene and generator are in `output/asset-improvement-20261030/spillway-hose/retired/`.

`check_installed.py --static` rechecks those exact changes; without the switch it also renders the saved installation and checks three
floor rays in an isolated s&box scene. `archive_review.py` archives just the hose-specific comparison resources through the editor.
The one-time installer refuses a changed input or rerun. Do not rerun the whole map generator.

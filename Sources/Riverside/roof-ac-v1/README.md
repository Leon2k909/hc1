# Office rooftop air conditioner v1

Approved and installed 2026-11-04. The user requested replacement, deletion of the old model and another improvement.
Exactly 24 old AC faces were removed from the current pad OBJ through the editor; the new three-LOD renderer is saved under
`Roof Air Conditioners / Office Rooftop AC`. No other scene data changed. The pad ModelDoc and its physics are byte-for-byte preserved.

The office trailer's original rooftop unit is two boxes, 24 triangles. The replacement has a hollow chamfered shroud,
a recessed fan well with four twisted blades and a motor, concentric wire guards, side intake louvers, exposed coil fins,
a removable service cover, screws, mounting hardware, gasket and a flexible curb fitted to the office's shallow roof pitch.
Its plastic housing uses authored color, roughness and normal maps; metal, rubber and the service label have separate materials.
No brand names. The fan is stationary geometry.

LODs: 3,796 / 1,940 / 868 triangles, switching at 12 and 35 using the existing ModelDoc convention. Six materials.
The horizontal footprint is 30.46 x 34.42 in in engine axes against the old 30 x 34. The top reaches 12.87 in above the
old base, against 13.5 before. The flexible curb extends down 1.742 in to meet the office roof; the previous boxes floated above it.
No new physics: this is visual dressing, and the office's existing collision stays intact.

Resources: `models/props/riverside/roof_ac_v1/roof_ac.vmdl`, `materials/riverside/roof_ac_v1/`.
The candidate origin is the old box's base at engine `-640,524.23195,219.5`, rotation zero.
The private `pad_without_ac` comparison removes exactly the original 24 triangles from a copy of the active pad input.
It is a review background and must not be installed wholesale after the shared pad changes.

Workflow, from the canonical checkout:

1. `rtk python Sources/Riverside/roof-ac-v1/build.py`: writes staged source assets under `output/riverside/roof-ac-v1/stage/`.
2. `rtk python Sources/Riverside/roof-ac-v1/review.py import`: native editor import guarded by staged and source hashes; compiles the resources.
3. `rtk python Sources/Riverside/roof-ac-v1/review.py isolated`, then `... context`: native studio and map-light captures in isolated worlds/scenes.
4. `rtk python Sources/Riverside/roof-ac-v1/verify.py`: checks triangle counts, winding, degeneracy, source preservation, collision and compile receipts.
5. `rtk python Sources/Riverside/roof-ac-v1/compose.py`: lays out native images without recoloring them.

Work, manifest, imports, screenshots and checks: `output/riverside/roof-ac-v1/`. Native checks preserve the user's active scene,
dirty flag and play state. Map captures hold exposure at 3.5. Geometry checks found no inverted or degenerate triangles in any LOD.
Nine resources compiled successfully. The original pad OBJ, pad ModelDoc and saved scene are hash-checked as unchanged.

`prepare_install.py`, `install.py` and `finish_install.py` contain the guarded installation and cleanup. Receipts:
`native-install.json`, `installed.json`, `installed-capture.json`; installed roof captures are in `output/riverside/roof-ac-v1/installed/`.
The twelve temporary comparison files (`legacy_ac.*`, `pad_without_ac.*`) were removed from Assets, with copies outside runtime
resources under `retired-review-assets/`. The saved scene comparison permits only the new group and renderer.

`P.trailer(..., roof_ac_model=True)` records the approved model placement while preserving the random draws and collision.
Only the office call opts in; `ROOF_ACS`, `carry()` and `roof_ac_objects()` retain it in future builds. A generator-only check confirms
that only the twelve old AC polygons disappear and all other generated geometry and collision stay identical. No map regeneration
was run. The historical review builder and pre-install verifier expect the old faces and must not be rerun against the installed map.

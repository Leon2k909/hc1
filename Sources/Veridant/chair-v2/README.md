# Veridant bistro chair

The support geometry in this version is superseded by
`Sources/Veridant/chair-v3/README.md`, which fixes posts and collars crossing the
wicker. The texture work and repaired shared base described below are retained.

`Tools/veridant_chair.py` builds the curved woven chair at the original scale:
17.5-inch seat, approximately 33.4-inch overall height, four grounded feet.
`veridant_parts.chair()` delegates to it, including future map exports.
`veridant_materials` now generates a 1024-pixel wicker colour, normal and
roughness set instead of the original solid brown material.

The published scene has 12 chairs at four tables. Each replacement is 4,248
triangles. Two bounded imports in `Assets/models/maps/veridant/chair-v2/`
hold six chairs each; the existing dressing VMDL references them. Scene
objects, camera state, collision nodes, hulls and chair placements are preserved.

The geometry plan is `output/veridant/chair-v2/stage-v7/manifest.json` and the
final install plan is `output/veridant/chair-v2/stage-v8/manifest.json`.
The geometry plan retains the intervening table revision by replaying its guarded replacement
against the pre-chair mesh, then removes the old chairs. The retained base is
losslessly compacted with equality checks on every face's material, position,
UV and normal. The current lounger replacement remains a separate import.

The final base import is `models/maps/veridant/chair-v2/dress-base.obj`.
A fresh path was necessary because the engine retained a memory-mapped copy
of the previous base even after successful compilation. The new base is a
byte-identical copy of the repaired, compacted stage-v7 base. Final front,
rear and terrace images are in `output/veridant/chair-v2/final/`.

Veridant's existing OBJs interleave table declarations and faces. New vertex,
UV and normal tables must be appended after all old declarations. Inserting
them before the first `usemtl` shifts indices in later declarations. The chair
patcher now appends safely; its final checks resolve all 13,824 wicker triangles
back to their exact authored positions before installation.

`import.cs.txt` runs through the native CLI from its exchange directory. It
guards target hashes, replaces memory-mapped files atomically, and compiles
the material and dressing VMDL. `capture.cs.txt` uses an isolated editor scene
for comparison images without moving the user's view or saving their scene.

# Veridant authored dining chairs

Status: published and verified in the native s&box editor on 26 October 2026.
All twelve chairs use the authored replacement. The material and parent model
compiled successfully; front, side, rear and terrace captures were reviewed.
The user's Ares scene remained open, saved and stopped throughout verification.

The replacement is James Ray Cock's Dining Chair 02 from Poly Haven, licensed
CC0. `SOURCE.md` identifies the source and license. `fetch.py` downloads only
this model and its maps and verifies the provider's file sizes and MD5 digests.
The original glTF and textures remain unchanged alongside their API manifest.

`preview.py` imports the real model in Blender, preserves its original UVs and
uses its PBR textures. The two renders in `output/veridant/chair-v5/view-a.png`
and `view-b.png` are actual 3D model renders, not generated concept images.

`prepare.py` stages four imports for the twelve existing chair placements,
with three chairs per import. Each chair has 22,013 triangles; the total is
264,156. Each import uses 38,673 position/UV/normal entries. The model stays at
physical scale (metres converted to inches), with its seat centre aligned to
the existing placement and its feet at the existing floor. Its overall size
is about 17.1 inches wide, 22.7 deep and 38.3 tall. The upholstered seat is
about 18 inches high. The chairs tuck slightly farther under the tables than
the previous shallow frames. Final placement subtracts the source mesh's
1.285 mm minimum Z offset so the lowest soles meet each existing floor exactly.

The stage adds one material with the original 2K diffuse, OpenGL normal,
roughness and AO textures. It changes only the chair nodes and their material
binding in the latest shared model document, preserving all physics bytes.
The table, bench, case, pool and gate imports are retained. The staged chair
entry point delegates future generation to `Tools/veridant_chair_authored.py`;
the existing `vr_chair_` material-preservation rule supports its binding.

The initial publication and original model-document backup are recorded in
`output/veridant/chair-v5/stage-v1/`. The final floor correction is `stage-v2/`;
it updates only the four chair meshes. To stage a further revision, use the next
unused stage name. No shared resources are written by staging. The native
`import.cs.txt` reads `publish-stage.txt`, guards every intended target/source
hash, atomically publishes the scoped edits and compiles the material and
parent model. If a mutation times out, inspect hashes and native resource
state before retrying.

`installed.json` records the successful native publication. `native-import-floor/`
contains the final import call; `native-after/` records the final engine capture.
Matched comparison images are in `before/` and `after/`. The latter show the
actual map renderer, distinct from the earlier Blender studio preview.

`verify.py` checks all twelve placements against the authored mesh data, retained
UVs/normals, source hashes, unchanged physics and other prop imports, successful
native compilation, and unchanged editor state. Its recorded result is
`output/veridant/chair-v5/validation.json`; the final floor error is zero.

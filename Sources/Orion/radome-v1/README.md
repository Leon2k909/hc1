# Orion hilltop radome — retained alternative, original in use

**User decision (2026-11-04): keep both versions and continue using the original.** This is a distant
background prop with little visible detail during play. The rebuilt version is retained as an unused
alternative; do not install it or delete either version unless the user requests a change.

Existing-model audit checked Orion sources and all project radar/radome/geodesic references and model
filenames. No suitable replacement was found. Stillhouse's boat radar housing and Forest Base's open
dish are different props. The baseline was matched by material and rounded vertex positions against
all 1,812 original radome triangles in the current `orion_vista.obj`; this rules out a hidden baked upgrade.

Rebuilt the texture-grid sphere as separately formed, inset geodesic panels with recessed weather seals.
Added anchored I-columns, base plates/hex bolts, gussets, angle braces, an external maintenance catwalk
with handrails, a caged access ladder and a framed equipment-shelter door/louvres. Original 340-inch
radius, 200-inch support height and approximately 784.8-inch total local height retained. Catwalk and
ladder fit inside the original dome's horizontal envelope. Shared materials are untouched.

**Retained, unused alternative.** `models/props/orion/radome_v1/radome.vmdl` has three LODs:
23,586 / 13,706 / 3,284 triangles, initial thresholds 0/75/180. No added collision, lights or gameplay.
The saved Orion scene and vista remain byte-identical to their starting state for this model.

`build.py` stages model/material inputs outside Assets. Import and compilation use the native editor.
`audit_baseline.py` confirms the actual map baseline; `verify.py` checks source/import hashes, protected
files, finite attributes, triangle areas/winding/bounds, references, native LOD counts and compile receipts.
Native views use identical cameras/lights/ACES/exposure for both variants; all three LODs rendered.
The isolated scene is destroyed and active scene/play state preserved. `compose.py` only crops/resizes
matched views and labels them. Evidence is in `output/orion/radome-v1/`.

No match or frame-time benchmark is claimed. The original 1,812-triangle radome remains baked into
the public vista and its source generator remains in use. No replacement or cleanup is pending.

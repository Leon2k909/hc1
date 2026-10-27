# Veridant forecourt gates

The apparent brown infill panels were the two closed east-boundary gates at
plan E=1900, N=-300 and N=500. Each now has paired folded steel leaves,
recessed frames, strap hinges with separate knuckles, a lever/escutcheon,
drop bolt and a small engraved resort plaque. The four lamp piers use
individually eased limestone courses, mortar cores, plinths and shaped caps.
The coating is a restrained satin green; low-angle warm light changes its
appearance naturally. Texture variation is kept small to avoid a dirty,
cloudy finish.

`Tools/veridant_boundary_wall.py` builds the visual assemblies and seven
materials. `forecourt()` calls it and retains the old four pier collision
boxes and lamp calls. `configure()` preserves the module's material paths.
No full-map regeneration is required to install this change.

The guarded first import is `output/veridant/boundary-wall-v1/stage-v2/`.
It removes exactly 72 legacy gate/pier triangles from the actual current
`chair-v2/dress-base.obj`, keeping every other original byte and index.
One dedicated render import and seven material remaps are added to the
current dressing VMDL. Its entire physics suffix is identical to the
pre-import document. Original sources are backed up inside that stage.

The final art/material refinement is `stage-v4`, with 9,236 triangles across
both gates. Refinements touch only `gates-v1` assets; the base import and
VMDL remain protected. Native publishing atomically replaces changed files
and checks source/target/backup hashes. It does not write the scene, lights,
foliage, buildings, cases, benches or chairs.

All seven materials and the dressing model compiled successfully. Both
final assemblies were visually reviewed in the native editor, in sunlight
and shade. The capture helper restores the editor camera, exposure, scene
camera reference and stopped play state; each capture has a restoration
receipt. Existing background scenery remains outside this change.

- Final images: `output/veridant/quality/gates-v1-complete/`.
- Validation: `output/veridant/boundary-wall-v1/validation.json`.
- Source preparation: `Tools/veridant_stage_boundary_wall.py`.
- Native review preparation: `Tools/veridant_gate_review.py`.
- Verification: `Tools/veridant_check_boundary_wall.py`.

Other chats saved the scene and an unrelated foliage model during review;
their observed hashes are recorded without replacing their work. The task
did not write those files. No frame-rate or multiplayer benchmark was run.

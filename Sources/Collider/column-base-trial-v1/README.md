# Collider column base — isolated proposal, 2026-10-30

The user approved the cooling unit, requested replacement of the old unit, and
asked for another asset improvement. That installation is recorded separately at
`Sources/Collider/cooling-unit-trial-v1/installed.json`. This new proposal selects
the plain base under the column at plan **(-960, -500, 0)**.

`build.py` matches all **12 saved base triangles** in `collider_structure.obj` and
copies their positions, UVs, normals and material. The base is originally an
88 × 88 × 8-inch solid slab. The candidate has **35,002 triangles**: a chipped
grout bed, bevelled painted steel plate, eight threaded anchors with open washers
and hexagonal nuts, six stiffeners and continuous weld beads. PBR maps contain
coating loss, exposed metalness, fine scratches, bolt-centred oxidation/dirt and
rough mortar aggregate. A small attached identification plate completes the detail.

The rest of the actual H-column is **unchanged render context**: 36 saved triangles,
with their real UVs, normals and original material. That context OBJ/material map
is outside Assets under the output folder and appears identically in both renders.
The close-up deliberately frames the base; the column continues above the frame.
The original column is not part of the candidate being proposed for replacement.

Additional clarification view (requested 2026-10-30): the user could not tell which
parts changed in the contextual view. `prepare_base_only.py` / `render_base_only_low_impact.py`
produce a matching before/after pair under `base-only-review/`, with the unchanged
column hidden in both images. This exposes exactly the component proposed for
replacement: anchors, stiffeners, welds, plate and grout. Both source meshes and all
map sources remain byte unchanged. `verify_base_only.py` verifies the additional
view and links it from the original review receipt. The context is hidden only for
explanation; it is not removed from the model/map.

Nothing is installed in the map by this proposal. The original base and all prior
accepted assets remain unchanged. Source guards cover the four packed model sets,
saved scene, prior accepted private assets and the shared materials/textures used
by the baseline and context. Neither standalone variant authors collision. New
hardware fits the existing 88-inch base footprint and 76-inch column clip above
it; the identification tag uses a sub-0.12-inch surface-detail allowance.

Run with `rtk proxy python -X utf8`, in order:

1. `Sources/Collider/column-base-trial-v1/build.py`
2. `Sources/Collider/column-base-trial-v1/verify.py`
3. `Sources/Collider/column-base-trial-v1/prepare_render.py`
4. `Sources/Collider/column-base-trial-v1/render_low_impact.py`
5. `Sources/Collider/column-base-trial-v1/finalize_review.py`

The renderer reads the exported mesh/UVs/normals and native material inputs,
including the plate's metalness texture. Before and after share the actual column,
camera, physical scale, lights, exposure and 1400 × 1050 / 32-sample settings.
The wrapper confines one idle-priority Blender process to two logical CPUs and
two Cycles CPU threads, with no GPU rendering. It waits for the process to exit.
No editor, browser, background compiler or development server is used.

Evidence: `output/asset-improvement-20261030/column-base/`. The images are actual
source-mesh previews, not engine screenshots. Engine import, native appearance,
LOD/performance and final in-game checks remain pending. Do not install this
candidate or delete the original base until the user approves this proposal.

# Veridant courtyard reflecting pool

The existing square pool now has 28 individual coping sections, small bevels
and edge spalls, 42 basin floor slabs, and two fractured stone meshes. The larger
rock protrudes above the water; the smaller rock remains submerged at its
original elevation. Their surfaces use the installed Spillway CC0 seaside-rock
scan set, with separate dry, damp and wet materials.

`Tools/veridant_pool_detail.py` builds the pool. `veridant_map.pool` delegates to
it and `configure` retains its material overrides. The water material generator
also delegates to this module, so ordinary map regeneration retains the change.
Existing pool collisions, light definitions, water plane, footprint and routes
are retained. The final pool render mesh contains 39,524 triangles; FPS was not
benchmarked.

The dedicated shader in `water.shader` uses moving filtered normals,
depth-dependent absorption, guarded screen refraction, direct-light reflections
and subdued local-probe reflection. It changes only `vr_pool.vmat`; the sea and
shared Lowtide shader are untouched.

## Publication and verification

The initial `stage-v1` removed exactly 746 original pool triangles from the
active `chair-v2/dress-base.obj`, retaining all other original bytes and indices.
A separate `pool-v2/pool.obj` render import and eight material remaps were added
to `veridant_dress.vmdl`. Its physics section and collision source meshes were
preserved. `stage-v3` refined the rock shapes, wet materials and water shader;
`stage-water-v5` is the final water-only revision. Other staged variants are
diagnostics and should not be published.

Publication used the native editor connection and `import.cs.txt`. Source,
backup and destination hashes guard each publication. No scene file was written
by this task. Other work saved Veridant and updated the shared dressing model
during the task; those changes were retained rather than reverted. The final
receipt records the current shared-file hashes separately from the staged ones.

The nine materials and dressing model compiled successfully. The custom shader
compiled successfully through `Editor.EditorUtility.CompileShader`; do not use
the generic `asset_compile` tool for a shader source. After a shader edit,
**force a full compile of `materials/veridant/vr_pool.vmat`**: an incremental
material compile retained an older shader program during this session.

`verify.cs.txt` confirmed nine valid loaded materials, two valid models, the pool
render import and the original physics bytes. Both final captures were visually
reviewed. Each capture restored the scene camera, view transform, exposure and
editor state. Final images:

- `output/veridant/quality/pool-v2-final/pool.png`
- `output/veridant/quality/pool-v2-final/player-height.png`

`output/veridant/pool-v2/validation.json` and `installed.json` record the result.

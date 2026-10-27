# Grand-stair planter vegetation

The one courtyard planter beside Veridant's grand stair now uses the authored
`facepunch.tree_oak_small_a#288917` tree. Its native model renderer retains the
original bark and foliage materials and all five LODs. World position is
`239,-272,42`, yaw 24 degrees, uniform scale 0.45. The highest LOD is 6,092
triangles. This is an ornamental broadleaf tree replacing the old procedural
olive, not a newly sculpted olive asset.

`Tools/veridant_courtyard_olive.py` defines this placement and the surrounding
soil, small mulch pieces and three rosemary clumps. `veridant_map.courtyard`
generates that planting; `write_scene` includes the native tree and exact cloud
package revision, so a source regeneration retains the change.

The scoped asset patch removed exactly 332 old tree/understory triangles from
the active `pergola-flowers-v2/foliage-base.obj`. Every retained byte and original
vertex/UV/normal index is preserved. The new planting is a separate 18,967-triangle
render import. No collision geometry changed. Existing scene objects are
preserved; one model-only child was added under Veridant through `spawn_model`
and the scene was saved through `save_scene`.

The first procedural replacement was rejected during visual QA for its sparse,
regular shoots. Its unused assets are archived outside Assets under
`output/veridant/foliage-hero-v2/discarded-assets/`. The authored tree and its
planting total 25,059 triangles at highest detail; frame rate was not benchmarked.

Publication: initial legacy extraction `stage-v3`, authored-tree integration
`stage-v5-authored`, final render-import/material cleanup `stage-v6-final`, all
under `output/veridant/foliage-hero-v2/`. Import receipts, native compilation,
live material/LOD checks and `validation.json` record the result.

Reviewed engine captures:

- `output/veridant/quality/foliage-hero-v2-before/courtyard.png`
- `output/veridant/quality/foliage-hero-v2-authored/courtyard.png`
- `output/veridant/quality/foliage-hero-v2-authored/detail.png`

Capture helpers restore the view, exposure and scene state. Other authorised
work saved the shared scene during this task. The saved exposure is the map's
authored 2.1–2.4 range, rather than the temporary fixed 2.2 capture setting that
appeared in an intermediate disk snapshot. The scene comparison records this
normalisation separately from the added tree.

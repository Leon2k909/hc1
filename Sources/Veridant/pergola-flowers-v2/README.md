# Pergola flowering vine

`Tools/veridant_bougainvillea.py` replaces the six overlapping flower-atlas cards
with woody canes, folded leaves and small papery bracts. The canopy grows around
the beam and hangs in unequal sprays. `veridant_parts.bougainvillea()` delegates
to the new builder; `veridant_map.configure()` preserves its material bindings.

The existing foliage model retains its path. Its RenderMeshList now uses
`pergola-flowers-v2/foliage-base.obj` and `pergola-flowers-v2/flowers.obj`.
The base preserves every original OBJ record except the 24 triangles belonging
to the six flower panels. Original vertex/UV/normal indices remain unchanged.
The shared original OBJ, atlas, scene and gameplay collision are preserved.

Final publication: `output/veridant/pergola-flowers-v2/stage-v5/manifest.json`.
The planting has 1,160 leaves, 126 flower clusters and 936 folded bracts, at
58,272 triangles. Frame-rate impact was not benchmarked. Six material compiles
and the foliage model compile passed in the native editor.

Matched front views and a final angled view are under
`output/veridant/quality/pergola-flowers-v2-final/`. The original matched view is
`output/veridant/quality/pergola-flowers-v2-before-clear/front.png`.
Camera, main-camera selection, exposure and scene state restore after captures.
See `output/veridant/pergola-flowers-v2/validation.json` for the verification receipt.

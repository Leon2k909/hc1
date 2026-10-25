# Veridant lounger upholstery and timber

The eight placed loungers now use crowned foam with shallow compression,
asymmetric cloth outlines, seam puckering, piping and small stitches. Rounded
teak sections have sanded ends, slight bowing and taper, varied grain alignment
and a less orange, rougher finish. Each placement has deterministic variation.

`Tools/veridant_lounger.py` calls `veridant_lounger_soft.py`; the map's existing
`veridant_parts.lounger()` hook therefore keeps the new geometry on regeneration.
The current two `lounger-v2/*-replacements.obj` imports and reusable prop retain
their resource names and seven material bindings. Use the active RenderMeshList
when preparing subsequent baked-mesh edits.

The final publication is `output/veridant/lounger-v3/stage-v3/manifest.json`.
The first publication verifies every triangle in the original dedicated imports;
the smoothing revision verifies the previously published mesh hashes. All three
model documents, their physics, the scene and unrelated map imports are protected.
Shared canonical map OBJs are preserved. `previous-lounger.py` records the original
geometry implementation.

Final density is 15,482–15,512 triangles per lounger, with each map import below
80,000 triangles. Frame-rate impact was not benchmarked. Seven materials and all
three models compiled natively. Verification and camera-restoration evidence:
`output/veridant/lounger-v3/validation.json`. Matched garden captures and the final
rooftop close-up are under `output/veridant/quality/lounger-v3-final/`.

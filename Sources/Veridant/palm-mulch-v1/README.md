# Veridant palm-bed soil and bark

Replaces the red-tinted gravel in all ten promenade palm planting beds with a neutral brown soil-and-bark surface. The existing 1,760 stone-border triangles retain their original bytes and vertex/UV/normal indices. The task adds no colliders and does not write the scene or model document.

`Tools/veridant_palm_mulch.py` supplies the shallow settled fill, 120 embedded irregular fragments per bed and the material writer. `veridant_parts.palm_pit()` delegates its interior to that helper. The `derived` material build in `veridant_materials.py` uses the dedicated writer, so regeneration retains the replacement.

The generated colour image is preserved unchanged in `soil-bark-albedo-generated.png` and published as `Assets/materials/veridant/palm-mulch-v1/soil-bark-color.png`. It was made with the built-in imagegen tool; the complete prompt is in `imagegen-prompt.md`. The generated image is 1254 square. Normal and roughness maps are derived at 1024 square to satisfy the engine's packed-normal mip compiler. These are small visual relief estimates, not scanned height data.

Final publication: `output/veridant/palm-mulch-v1/stage-v3/manifest.json`. The native importer replaces directory entries atomically and checks current targets, backups, protected files and source hooks before writing. The staged OBJ removes only the 720 original fill faces, preserves all remaining original bytes, and appends the new tables and faces at the end to retain every existing index allocation. The fill has 29,600 triangles in total, with 1,200 fragments across ten beds; frame-rate impact was not benchmarked.

Both the material and model compiled successfully in `compile-v3/call_tools.json`. The matched before/after capture at `output/veridant/quality/palm-mulch-v1-{before,after}/palm-bed.png` uses identical camera, projection, exposure and scene hash; all restoration flags passed. The optional second-bed capture was discarded after a concurrent save changed the scene hash. Its camera, tone, object and asset restoration flags passed, and the shared scene was left untouched. The final editor remained in stopped, saved Veridant with a successful code compile.

`output/veridant/palm-mulch-v1/validation.json` records hashes, bounds, retained bytes, compile receipts and the accepted capture.

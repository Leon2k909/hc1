## Steel drum v2 (`models/maps/boxyard/oil_drum_v2`, `Sources/Boxyard/oil_drum_v2/`, 2026-10-30)
- Replaced Boxyard's five drums at the user's word after a before/after: three as cover on bomb site B, two in the south-west corner.
- `Tools/boxyard_map.py`'s `drum()` keeps writing the hull it always did into the merged props, with no faces (`lathe` with paints of
  None), and `drum_object()` places the model in the scene with no collider. Other maps' drums are their own code and aren't touched.
- That's the pattern for swapping a script-built prop in a merged model: keep its hull, and place a model in the scene.
- To apply a map script's change without rewriting everything: redirect `OUT_DIR`, `SCENE_FILE` and `MINIMAP_FILE` to a scratch folder,
  run its `main()`, compare, and copy across only what changed. Boxyard's models come out identical on a re-run. Its radar PNG doesn't.
- Built offline. **Not yet compiled or seen in s&box**: see the folder's README.

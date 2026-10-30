## Capture flag v2 (`models/gameplay/capture_flag_v2`, `Sources/Gameplay/capture-flag-v2/`, 2026-10-30)
- The Domination and Hardpoint point model: a field mast with stays, sandbags, a halyard and a torn flag, replacing
  `flag_pole_base` at the user's word after a before/after. Same origin, height and +X fly. LODs 31,910 to 894 triangles.
- Only `cf_cloth` takes `ModelRenderer.Tint`, so team colours work as before. The managers add no `ModelCollider`, so
  players walk through it, as they did through the old one.
- Built offline and **not yet compiled or seen in s&box**: see the folder's README for that, the pipeline, and what's
  still an estimate (LOD thresholds). Rerunning `build.py` can change the unwrap, so bake and paint after it.

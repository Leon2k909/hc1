# Terrace flag cloth — applied review, 2026-11-06

Rebuilt the five-strip cloth with smooth breeze folds and a sagging free edge.
Artwork, atlas direction, hoist dimensions, pole and physics retained. Static
cloth, not animated. 4,608 double-sided triangles. Removed exactly 20 original
cloth triangles from Dressing source imports, retaining every other record
and unchanged physics. Original complete flag/pole remains reusable at
models/props/shared/terrace_flag_original_v1/flag_original.vmdl.
New cloth-only model: models/props/shared/terrace_flag_v1/flag.vmdl.

Source Tools/veridant_terrace_flag.py; flag() generation hook only affects this
terrace placement. Current scene uses one Terrace folded flag 1 object. Native
compilation/model checks passed. Original source and parent snapshots retained
under output/veridant/terrace-flag-v1/before/. Matching actual displayed viewport
before.png/after.png are in the same output folder; no temporary rendering or
changed lighting/display settings.

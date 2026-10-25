# Bistro chair support clearance

This revision supersedes chair-v2's support geometry. The rear posts and binding
collars in that version crossed the visible woven back. `Tools/veridant_chair.py`
now routes the posts around the rear seat edge and behind the backrest. Four
rear spacers mount the panel without entering the woven skin. Under-seat rails
and brackets meet the seat from below.

The stage checks found 180 steel vertices crossing the original back skin and
zero in the corrected geometry. The closest mounting cap stays 0.38 mm behind
the back skin; no steel vertices enter the seat. All 12 existing placements and
the original materials, collision and scale are preserved. Each chair is 4,480
triangles, in two imports of six chairs each under `models/maps/veridant/chair-v3/`.

`Tools/veridant_stage_chair_clearance.py` stages the exact replacement. Its plan,
backups and geometry results are in `output/veridant/chair-v3/stage-v1/`.
`import.cs.txt` guards every changed/protected file and installs through the native
editor connection. The VMDL changes only the two chair import paths; its physics
and the base and lounger imports are preserved. The canonical OBJ is updated
without shifting existing table indices.

`capture.cs.txt` renders an isolated scene with front, side, rear and terrace
views. Before/after images are in `output/veridant/chair-v3/before/` and `after/`.
`output/veridant/chair-v3/installed.json` records successful asset compilation and
unchanged editor scene, unsaved flag and play state.

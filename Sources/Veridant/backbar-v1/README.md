# Veridant back-bar display

The original `counter_shelves()` intended its black and brass cuboids as bottles.
The replacement has separate walnut backing, base cupboards, eased shelf boards,
dividers and integrated narrow warm diffusers. Its 115 bottles have shaped bodies,
shoulders and necks, sealed caps, tinted glass, liquid fills and curved paper labels.

`Tools/veridant_parts.counter_shelves()` delegates to `veridant_backbar.py`.
`veridant_map.configure()` preserves the custom back-bar and transport-case
material overrides during a complete regeneration. `previous-shelves.py` records
the former block construction.

The three shelf spans remain [-520,-424], [-356,-300] and [-46,66] in plan N,
with the existing four-inch doorway margin. All new geometry stays inside those
horizontal bounds and adds no collision. The active buildings base import lost
precisely 1,926 old triangles with all retained bytes and indices preserved. The
current buildings VMDL gains three imports and eleven material bindings; its
complete physics suffix retains its original bytes. The scene and all unrelated
imports remain unchanged.

Final stage: `output/veridant/backbar-v1/stage-v1/manifest.json`. The three new
imports total 83,268 triangles. Frame-rate impact was not benchmarked. All eleven
materials and the buildings model compiled. Twenty-seven native doorway rays
are clear. The matched cafe view and bottle-label close-up were inspected with
complete editor/camera restoration. See `output/veridant/backbar-v1/validation.json`
and `output/veridant/quality/backbar-v1-after/`.

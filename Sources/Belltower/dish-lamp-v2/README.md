# Suspended street lamp v2 — review only

Rebuilt the lamp at plan hook `(-1700,1275,240)` with a pressed enamel shell, separate white inner
liner, closed rolled rim, cable clamp, neck collars, ceramic socket, brass bulb base and rounded globe.
The existing cable and all materials are unchanged. No collision or permanent lighting changes.
Source LODs: 5,356 / 3,420 / 1,368 triangles; the original lamp is 356 triangles.

The private west variant removes precisely the selected old lamp's 356 triangles and preserves
all unrelated source records. Native compilation passed for the candidate and both west variants.
Both comparison definitions are freshly compiled, warmed with discarded renders and captured
with identical camera, framing and temporary inspection lighting. All camera/tone/model/object
and editor state is restored after each capture. Saved scene and shared-source hashes are unchanged.
Effective GPU exposure is not independently measured. An initial capture helper failed to compile
before making changes; the corrected captures are the final evidence.

Build and native review: `build.py`, `review.py`. Verification: `audit.py`, `review.json`.
Evidence: `output/belltower/dish-lamp-v2/{before,after}-final.png`.
Prepared on `codex/belltower-dish-lamp-v2-review`; NOT installed, pending user approval.

Approved and installed in all ten positions (five each side). Removed 3,560 old baked triangles
from eight mesh sources; all seven affected current/historic model definitions compiled.
Deleted thirteen obsolete private review files. Preserved physics, other object IDs and the user's
retained original wall-lantern resource. Native save/load verification passed; see `installed.json`.
Regeneration uses `Tools/belltower_dish_lamps.py`; accepted builds no longer recreate retired files.

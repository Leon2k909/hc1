# Bakery sack pile v2 — review only

Seven filled cloth sacks replace the plain boxes at plan `(-1215,730,0)`, retaining their arrangement
and collision envelope. Rounded bodies, shallow cloth folds, rolled seams and sewn mouths reuse the
existing canvas material. Source LODs: 9,170 / 8,120 / 6,720 triangles; original boxes: 84 triangles.
The far LOD retains the rounded body silhouette; it removes separate seam/stitch details.

All three native model definitions compiled. A private west variant removes only the original
84 render triangles, retaining unrelated source records. The saved scene and shared source hashes
remain unchanged. Fresh baseline and candidate models were warmed with discarded captures.
The final pair uses identical interior camera, framing, tone parameters and temporary inspection light.
Camera/tone/model/object/editor state is restored after each capture; GPU exposure is not independently
measured. Early exterior captures were occluded by the wall and are not review evidence.

Final evidence: `output/belltower/sack-pile-v2/before-interior.png` and `after-interior.png`.
Build/review source and receipts are in this folder. User approved and both bakery piles are installed.

Installed: two mirrored piles, fourteen sacks. Removed 168 old box triangles from four source meshes, deleted nine obsolete review assets, and compiled all seven affected map model definitions. Native save/load and identical regenerated collision checks passed. Saved after evidence: after-installed.png. See installed.json.

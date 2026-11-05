# Reef Hall display pedestal — installed

Approved and installed 2026-11-04 at the reviewed southwest rotunda display beside the walkway/bench,
plan `polar(200,430)`, world `-147.068662,404.067827,0`. Rounded concrete body, recessed service door
with hinges/pull/fasteners, side ventilation, toe plinth, seals, slim tank corner extrusions and formed lid.
Existing concrete/black materials plus two private coating/alloy materials. No new lights or textures.

`models/props/reefhall/display_pedestal_v1/pedestal.vmdl`: three LODs, 3,144 / 3,028 / 712 triangles,
thresholds 0/40/100. Body approximately 44 inches square, 65.2 inches high; small hardware overhang
at most .145 inch on a side and .016 inch above the old lid. One renderer; no new collider.

Exactly 24 original base/lid triangles removed from the current rotunda. Every other mesh line and
the full public ModelDoc/physics remained identical. The latest saved scene was used, retaining the
other accepted changes; semantic comparison proved only one renderer was added under Aquarium.
Glass, aquarium contents, fish avoidance, nearby bench, other pedestals and shared materials remain.
Native rotunda compilation and installed context capture passed; all three LODs render and floor ray
hits z .038. Final capture preserved active scene/play state. No live match or frame-time benchmark.

Source hook: `Tools/reefhall_display_pedestal.py`. `reefhall_map.display_case` preserves the old collider
and glass while omitting only this placement's base/lid; `write_scene` emits its standalone renderer.
Other placements keep their original geometry. `build.py` reproduces approved model/material inputs
outside Assets; `verify.py` validates installed hashes, geometry, references, bounds and source receipts.

Original review resource, old snapshots and before images were deleted after exact-scope proof.
`output/reefhall/display-pedestal-v1/installed-verification.json` retains that proof. Current checks,
build hashes and installed images are alongside it; `capture_installed.cs.txt` reproduces the views.
Do not regenerate the whole map to change this prop.

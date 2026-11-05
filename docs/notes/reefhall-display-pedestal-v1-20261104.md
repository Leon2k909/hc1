# Reef Hall display pedestal — installed, 2026-11-04

Approved rebuilt pedestal/lid at the southwest rotunda display beside the bench. World
`-147.068662,404.067827,0`. Rounded body, recessed service door/hardware, ventilation, toe plinth,
seals and slim framing. Renderer-only `models/props/reefhall/display_pedestal_v1/pedestal.vmdl` has
LODs 3,144 / 3,028 / 712. No added collider/lights.

Exactly 24 old base/lid faces deleted. All other mesh lines and original physics/ModelDoc unchanged.
Latest scene retained, adding only one renderer under Aquarium. Glass, contents, fish avoidance,
nearby bench and other pedestals preserved. Native compilation and installed capture passed.
Old review resources/snapshots deleted; scope proof and installed views remain in output.

Generator hook: `Tools/reefhall_display_pedestal.py`, `reefhall_map.display_case` and `write_scene`.
Build/verify/capture recipes in `Sources/ReefHall/display-pedestal-v1/`. No match/performance benchmark.

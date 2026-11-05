# Orion launch vehicle — installed 2026-11-04

Approved rebuild at world `2800,-694,240`: lined curved bells/cooling rings, engine hardware,
tapered fins, service ducts, access plates and stiffeners. Original dimensions/livery/markings retained.
LODs 43,980 / 22,668 / 6,668. No added physics or effects.

Exactly 1,164 original vehicle render faces removed; every other face and all vertex attributes
preserved. Pad ModelDoc/physics unchanged. One renderer added to saved Orion. Native context capture
passed. Old review resources/snapshots deleted; shared materials untouched.

Source hook: `Tools/orion_launch_vehicle.py`, placement registry in `orion_parts.py`, scene adapter in
`orion_map.py`. Staged source reproduces installed resources exactly. See
`Sources/Orion/launch-vehicle-v1/README.md` and output verification receipts. No match/performance test.

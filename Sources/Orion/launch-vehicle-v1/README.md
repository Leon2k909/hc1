# Orion launch vehicle — installed

Approved and installed 2026-11-04. Lined curved nozzles, rolled lips/cooling rings, carrier/gimbal
hardware, tapered fins/root fillets, service ducts/clamps, access panels, skirt/interstage stiffeners
and fairing seams. Original proportions, white/dark/gold livery and ORN/Orion markings retained.
Shared materials are reused without modification.

`models/props/orion/launch_vehicle_v1/vehicle.vmdl`: LODs 43,980 / 22,668 / 6,668 triangles,
initial thresholds 0/90/200. Renderer at world `2800,-694,240`, scale 1, yaw 0. Height 1,300 inches
above the skirt base; lowest LOD nozzle lip extends 26.55 inches below. No added collision or effects.

Exactly 1,164 old render triangles were matched and removed from the current pad. All other faces and
vertex/UV/normal records were identical. Pad ModelDoc and physics unchanged. Semantic scene comparison
proved the only addition was one renderer. Old review resources and obsolete snapshots deleted.

`Tools/orion_launch_vehicle.py` holds approved geometry and the scene adapter. `orion_parts.rocket`
records placements; `orion_map.write_scene` emits the renderer. Existing chair hooks remain.
`build.py` stages reproducible inputs outside Assets; `verify.py` checks installed hashes, geometry,
references, dimensions, the saved instance and source placement hook. Do not regenerate the whole map.

Native compilation/loading and all LOD renders passed. Installed Orion context images are in
`output/orion/launch-vehicle-v1/installed/`. `installed-verification.json` retains the exact removal proof;
`verification.json` records current geometry/source checks. Native capture preserved active scene/play
state. No match or frame-time benchmark is claimed.

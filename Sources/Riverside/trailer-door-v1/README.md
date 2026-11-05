# Riverside trailer entry door v1 — T2 installed

Installed the user-approved T2 entry door at engine `995,891.826513,30`, yaw 180. One saved renderer under `Trailer Entry Doors`; removed exactly 16 original backing/panel/handle triangles from public lowland geometry. The original lit window retains its position, UVs and emission. Every other lowland OBJ line, complete ModelDoc/physics, steps and door lighting were preserved. The other trailer doors remain as authored.

The replacement has a painted aluminum panel with lower pressing, jambs/header and weather seals, rounded window bezel/gasket, three hinges with knuckles/pins/screws, recessed paddle latch/cylinder, separate deadbolt, kick plate, threshold and rain cap. Wear is concentrated around the latch, hinges and lower edge. The metalwork surrounds the original 16 by 16.72-inch window instead of covering it.

Resource: `models/props/riverside/trailer_door_v1/door.vmdl`. Three LODs: **4,468 / 2,596 / 996 triangles**, thresholds 20/50. One 1024px procedural PBR atlas/material, no external assets. No added collision, lights or opening logic. No gameplay performance or LOD-transition test.

## Retained sources

All shell commands require `rtk`. `build.py .` creates the door assets. `Tools/riverside_parts.py` records `TRAILER_DOORS`, retains the original window cards, and carries the placement with its owner. The optional `entry_door_model` hook is enabled only for T2 by `Tools/riverside_map.py`, which emits the deterministic `Trailer Entry Doors` group. Other sizes/finishes require their own audit. Do not regenerate the whole map.

## Installation evidence

`prepare_install.py .` staged the exact cut from the then-current shared lowland mesh, backed up scene/OBJ/ModelDoc and recorded guarded hashes. `install.cs.txt` edited the existing inactive Riverside editor session, loaded the model, applied the cut/group and called its public `Save(false)`, preserving the active Railhead play session. Public lowland compilation succeeded.

Saved-file verification caught a recently installed camper missing from the stale in-memory Riverside session. `reconcile-camper.cs.txt` restored that saved object. The concurrently approved shop-sign light intensity .20 was retained. `verify-install.py .` passed scene-object, window/mesh, placement, complete ModelDoc/physics and lighting/step checks, accounting for native default/resource expansion on the restored camper. `capture-installed.cs.txt` rendered the actual saved group with no replacement substitution; saved door count 1, new lights/colliders 0.

The subsequent approved hitch installation removed its own 48 faces. `installed/post-concurrent-verification.json` confirms the combined 16 door plus 48 hitch face removal, no other changed lowland lines, unchanged ModelDoc/physics, and the saved door, camper and hitch.

Evidence: `output/riverside/trailer-door-v1/installed/`, including actual saved-group `installed_whole.png`. Native scene values use float precision; the saved sill Y is 891.826538, within 0.00003 inch of the authoring value.

## Historical review

`prepare_review.py`, `review.cs.txt`, `verify.py` and `compose.py` produced matched whole/latch/window comparisons with fixed exposure and temporary matched inspection light, using a disposable scene destroyed in `finally`. The original gate was rejected and retained. During review, the approved aerial/camper installations changed shared files; exact gate-triangle checks confirmed all 82 original gate faces still existed. These comparison scripts and their protected hashes are archival, not the installation workflow. Original images: `output/riverside/trailer-door-v1/compare_whole.png`.

# Sewage main stair treads v1

Staged replacement of the twenty tread assemblies on the main west flight: `(-925,-765,-100,300,0,160)` in Sewage plan coordinates. The new render mesh has actual open steel bearing bars and crossbars, folded end plates, bevelled yellow nosings with raised grip serrations, washer/hex fasteners, and a central stringer. The existing handrails, outer stringers, stair heights and walking collision are preserved.

`Tools/sewage_stair_treads.py` authors this one flight. `Tools/sewage_map.py` calls it only for the matching coordinates; other flights keep their existing geometry.

`build.py` removes exactly 480 original tread triangles, retains all 21,272 other catwalk triangles byte-for-byte in face position/UV/normal terms, and adds 35,292 triangles. It checks finite/non-degenerate geometry, exact retained faces, unchanged ModelDoc physics and the original collision-hull hash. No runtime component is added.

Status: installed and visually approved. Keep both the original `models/maps/sewage/stair-treads-v1/before.vmdl` and new `after.vmdl` variants at the user's explicit request. The new geometry remains active in the public catwalk model. The public model compiled successfully. Native before/after renders show the flight and close tread detail; the capture reports confirm matched cameras/lighting and preserved editor/play state. Geometry checks confirm all unrelated faces and the collision hull remain unchanged.

Resume from the canonical checkout with the project open:

1. Check `editor_status` and verify the checkout path.
2. `rtk python Sources/sewage/stair-treads-v1/native.py script Sources/sewage/stair-treads-v1/import.cs.txt`
3. Compile `models/maps/sewage/stair-treads-v1/before.vmdl` and `after.vmdl` via native `asset_compile`.
4. Run `capture.cs.txt` via `native.py script`, inspect both matched pairs, adjust if necessary.
5. Run `install.cs.txt` via the same wrapper and compile the public `models/maps/sewage/sewage_catwalks.vmdl`.

The guarded installer refuses to overwrite changes made since the baseline snapshot. All captures use an isolated visual scene, which is destroyed afterward; editor scene and play state are preserved.

`check_installed.py` verifies the installed file hashes, exact face splice, unchanged collision-hull hash and completed warning-texture cleanup. It also prepares `capture-installed.cs.txt`, which renders the final public model against the original preview model.

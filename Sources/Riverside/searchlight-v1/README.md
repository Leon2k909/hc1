# Riverside guard-tower searchlight — 2026-11-04

Replaced the simple twelve-sided black cylinder and bare stem with a formed olive enamel housing, tapered rear
casting and cooling fins, a metal lens retaining ring and fasteners, gasket, pressed rain visor, adjustable yoke
and trunnion hardware, rear cable gland, flexible supply cable, ventilation cover and equipment plate. Private
1024px coating/normal/roughness maps provide fine enamel grain and restrained scratches. No external assets or
image generation were used.

The existing luminous lens is retained exactly: all10 original faces, its position, radius8, material and aim
are unchanged. The new visor sits outside the aperture. No searchlight beam shader, material, proxy, target,
intensity or scene lighting was edited. The original tower, collision and other map content stay intact.

`build.py` stages private preview assets. `layout.original` is checked against the published lamp before any
change. `capture.cs.txt` renders before and after with the same native camera, lighting and exposure; the review
models are displayed horizontally for comparison. The map installation retains its existing downward aim.
`context.cs.txt` loads the saved Riverside visual roots into an isolated scene and renders the installed public
model in the original night lighting. Temporary scenes are destroyed, preserving the user's scene and play state.

`prepare_install.py` snapshots current shared inputs and stages a targeted face splice. `install.cs.txt` runs
through native editor MCP, refuses changed inputs and publishes only dressing OBJ/MTL/ModelDoc and the two offline
generator files. Exactly72 old body/mount triangles are removed,10,142 triangles are added and39,978 unrelated
faces are retained exactly, including all29,568 approved transformer faces. The complete ModelDoc physics suffix,
the tower's two collision boxes and all existing lens faces are unchanged. `riverside_parts.guard_tower` now calls
`Tools/riverside_searchlight.py`; the retained generator produces exactly the installed tower faces and head anchor.
Do not rebuild the full map to apply this change.

The public model compiled successfully and `check_public.cs.txt` confirms all five new material bindings on the
loaded resource. The full-compile CLI call timed out while the engine finished; `asset_info` then confirmed it
compiled, up to date and not failed. `verify.py` checks installed hashes, exact retained faces, unchanged lens,
transformers, physics/beam/scene, generator collision and mesh data. It passed with zero invalid or degenerate
triangles. The editor reports zero code compile errors and the original clean, stopped Riverside state.

Evidence and snapshots: `output/riverside/searchlight-v1/`. `before.png`/`after.png` are actual engine renders;
`context/*-installed.png` shows the map installation. `verification.json`, `public-resource.json`, `installed.json`
and native tool logs record the completed checks. The unused `before.*` comparison asset is retired outside the
game in `retired-before/`, with hashes in `retirement.json`; screenshots and rollback snapshots are retained.
The preview import/capture scripts describe the historical review and should not be rerun after retirement.
This is a render mesh upgrade only; no gameplay or collision change and no frame-time benchmark.

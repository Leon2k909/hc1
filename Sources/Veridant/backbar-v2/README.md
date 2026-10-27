# Veridant back-bar detail pass

The three existing bar displays use the same doorway-safe spans and dedicated
`Assets/models/maps/veridant/backbar-v1/shelves-{0,1,2}.obj` imports. Their resource
names are retained; the improved materials are in
`Assets/materials/veridant/backbar-v2/`.

`Tools/veridant_backbar_detail.py` supplies eight bottle profiles, curved printed
labels and small neck bands, separate liquid fills, rolled foil closures,
glassware with interior walls and closed bases, supported stemware racks,
cocktail shakers, jiggers, trays and a fictional drinks menu. The walnut boards
have oriented grain, eased edges, fine brass reveals, door gaps and mounted
handles. The active `veridant_backbar.py` delegates to this implementation.

There are 85 bottles, 16 glasses and two serving sets across the three sections.
Render meshes contain 56,202 / 27,704 / 66,022 triangles (149,928 total).
No new collision is generated. The source's 22 small shelf lights have a
34-inch radius and no shadow maps. The two existing cafe and lower-lounge
reflection probes use freshly baked native cubemaps. No runtime script,
continuous reflection update or frame callback was introduced. FPS has not been
benchmarked; these are geometry and lighting budgets, not an FPS guarantee.

`lighting-installed.json` records the baked room texture paths; `probe_object`
reuses them during source regeneration. `build_into` supplies the corresponding
practical lights through the existing map lighting list. The baked cubemaps live
in `Assets/scenes/maps/Veridant/veridant_scene_data/envmap/`.

The original generated walnut albedo is preserved as
`Sources/Veridant/backbar-v2/walnut-albedo-generated.png`. It was generated with
the built-in imagegen tool; the exact prompt is in `imagegen-prompt.txt`. The
tool returned 1254 x 1254 pixels. The runtime material's albedo, companion pore
normal and roughness maps are resampled/exported at 2048 x 2048 for the engine's
power-of-two normal mip filtering. This is a surface texture on actual 3D
boards; the display itself is not a generated picture.

Final publication uses `output/veridant/backbar-v2/stage-v7/manifest.json`.
The guarded native importer only writes the display's three existing mesh
imports, its material files, and its owned material bindings in the buildings
ModelDoc. Other render nodes and the physics node are preserved. A concurrent
base-mesh edit during staging was retained; unrelated imports are recorded as
reference snapshots instead of treated as inputs to the new dedicated meshes.

Native reflection baking and scene saving add one light group with 22 children
and change only the two existing probes' mode/texture settings. Scene saves may
refresh asset IDs for unchanged resource paths and update unused prefab ID
aliases. The checker verifies every serialized object/component identity and
model path, and retains the concurrent courtyard tree addition and four spa
fixture adjustments recorded in `shared-scene-review.json`.

`Tools/veridant_check_backbar_detail.py` checks file guards, scene scope,
compiled assets, doorway rays, source hooks and capture restoration. Reports and
before/after native captures are under `output/veridant/backbar-v2/` and
`output/veridant/quality/backbar-v2-final-clean/`. The final capture pass uses
only a synchronous exposure override, avoiding a shared-scene save during a
multi-frame exposure trial. The map's original 2.1-2.4 range is restored and
verified. `installed.json` is written only
after final verification passes.

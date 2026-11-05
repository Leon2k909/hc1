# Riverside porch drinks fridge v1 — installed 2026-11-04

User approved the actual-play before/after and requested installation. `riverside_store.vmdl` now imports `drinks-fridge-v1/store_without_fridge.obj` and `drinks-fridge-v1/drinks_fridge.obj`, with nine private material remaps. The first mesh drops exactly 14 old fridge triangles; every other vertex/UV/normal record and face is retained. The original ModelDoc physics section and saved scene are unchanged by this install.

The replacement is 34,152 triangles: 32 individual bottles/cans, wire shelves, glass door, gasket/hinges/pull, recessed liner, base grille and DRINKS plaque. It retains the old 30 × 28 × 72 cabinet size and existing porch light. No new light component was added.

`Tools/riverside_drinks_fridge.py` reproduces the approved OBJ exactly. The porch-only hook in `Tools/riverside_map.py` carries over the legacy collision and light; the three indoor fridges are unchanged. Do not full-regenerate Riverside to install this asset: the shared generator has unrelated ongoing work.

Sources and guarded scripts: `Sources/Riverside/drinks-fridge-v1/`. Play check without runtime substitution: `output/riverside/drinks-fridge-v1/installed.json`, with one player, zero error models, all nine materials loaded and editor state restored. Installed capture: `runtime-installed/fridge-installed.png`. Other recent supply-crate/fire and scene serialization edits were recorded in the install baseline and retained.

Later placement fix, at the user's request: moved the cabinet 64 inches toward the storefront wall, plan centre (96, 560) → (96, 624), leaving a two-inch rear gap.
Only fridge vertex positions and its metal physics-box origin changed; its existing point light moved with it and is the only saved scene change. The porch generator and
private builder reflect the new location. `verify_wall_move.py` confirms unchanged mesh topology/UVs/normals, other physics and scene values, generator agreement and five
native collision rays (including clear old footprint and doorway). Compilation and editor captures passed; the relocation has not been tested in live gameplay.
Current receipts and captures: `output/riverside/fridge-wall-placement-20261104/`. Original install hashes/play capture above are historical and predate this move.

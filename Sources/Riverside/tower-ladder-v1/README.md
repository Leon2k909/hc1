# Riverside guard-tower ladder v1 - installed; original preserved

Selected 2026-11-04 after A's water tank was installed and B was entirely deleted. Installed with user approval. The user
requested preservation of the original ladder for reuse, with a separate texture. Both original wood and galvanized-steel
variants are retained; no original ladder asset was deleted.

Existing-upgrade audit found the approved/installed `models/maps/lowtide/quay-ladder-v1/quay_ladder.vmdl` and its retained recipe
`Tools/lowtide_quay_ladders.py`. That 150-inch quay ladder cannot be stretched to a 520-inch tower without distorting rungs and
hardware. This candidate reuses the approved recipe and all three existing material finishes, extending the straight rails,
repeating anti-slip treads at 12-inch spacing and fitting mounting struts to the tower's rear timber legs. No new textures or
materials. Searches of source/assets/notes and current model chats found no guard-tower ladder replacement; neon sign, taxi
post, tunnel gates, Belltower lanterns and Spillway roof fans were excluded because they are already being handled.

Smooth continuous rails have returned handholds clearing the retained plywood wall, top fixing feet, sealed lower ends,
round-ended treads, wear strips/grip studs, clamps and bolted standoff plates. Four cross-struts connect the standoffs to the
rear timber posts; their ends stay inside the tower's existing footprint. The handholds extend above deck level to clear the
existing 44-inch plywood wall. The original timber structure, approved searchlight/lens/beam, wires, lights and collision stay.

Three LODs: 15,136 / 9,876 / 4,660 triangles, thresholds 25/65. Three approved Lowtide finishes: cast iron, steel and grip metal.
No new physics, climbing behaviour, navigation or lights. Engine root `1684.288713,555.286614,0`, yaw `-163.300756`; plan root
`-555.286614,1684.288713,0`. Ground-to-deck height remains 520 inches, same lean and attachment side. Main geometry reaches
local Z 577 including handhold tube radius.

`build.py` adapts the retained approved recipe in memory; the Lowtide recipe, model and shared material files are hash-checked
and never edited. Stages under `output/riverside/tower-ladder-v1/stage/Assets`. `prepare_review.py` records the transformations
used to create the checked-in native scripts. Import with `review.py import`; capture with `review.py isolated` and `review.py
context`; check with `verify.py`; arrange unchanged native images with `compose.py`. Commands require `rtk proxy python`.

Model `models/props/riverside/tower_ladder_v1/ladder.vmdl`. Private review background removes exactly 450 old ladder triangles
from the active dressing input using their materials and saved world-space vertex signatures. Original rod orientations are
captured directly in the tower's world frame. The real public dressing OBJ/ModelDoc and saved scene stay hash-protected.
Native studio and saved-map captures use isolated worlds/scenes, matching cameras/light and exposure 3.5 in map views. They
preserve the source editor scene/play state and show no error models. Three resources compile; all LODs pass winding and
degeneracy checks. All Lowtide materials and the approved recipe are unchanged.

Work, source hashes, reuse audit, compilation/validation receipts and images: `output/riverside/tower-ladder-v1/`.
Installation saved one native renderer under `Guard Tower Ladders`, removed only the original 450 map triangles and updated
the generator narrowly. Original tower/searchlight geometry, physics, public ModelDoc and all existing scene objects stay.
The original `legacy_ladder.vmdl` remains unchanged. `legacy_ladder_steel.vmdl` uses identical 450-triangle geometry with an
independent galvanized color/normal/roughness material. Shared wood materials were not changed. `preserve_steel.py` reproduces
the variant, checks both models in the engine and creates `output/riverside/tower-ladder-v1/reusable-steel-ladder/` with all
required source assets and README instructions for another s&box project. No climbing behaviour or collision is supplied.
Receipts: installed.json, installed-capture.json, native-install-compile.json and preserved-original.json. Pre-install build and
verify guards will intentionally fail against the installed dressing mesh. Lowtide's installed model remains unchanged.

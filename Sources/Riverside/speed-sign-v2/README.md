# Riverside speed-limit sign v2 — installed

Approved and installed on 2026-11-04 after the sandbag installation. One sign is saved in the Riverside scene at the reviewed transform. Exactly 16 old faces were removed from the current public pad mesh; its ModelDoc and collision were preserved byte-for-byte.

The old speed sign by the dog run has a square solid post and two disconnected flat images. Its front is 24 × 30 inches while its rear image is 30 × 30, so the backing is visibly wider from some angles. It contains 16 published triangles.

The replacement has one thin rounded metal sheet with shallow edge forming and a subtly bent corner, matching front/rear outlines, a folded U-channel post with real holes at two-inch intervals, two through fixings, front washers/hex heads and rear mounting plates/nuts. The fixings sit above and below the text. The existing SPEED LIMIT 15 artwork is preserved; zinc spangle, base corrosion, fixing stains and fine metal normal/roughness are authored procedurally. No external assets or image generation.

Model: `models/props/riverside/speed_sign_v2/speed_sign.vmdl`. Three LODs: **3,504 / 596 / 324 triangles**, switching at 22 and 55. The perforations become a solid web at reduced LODs. These are authored budgets, not frame-time measurements. One shared 1024 × 1024 atlas supplies colour, tangent normal, roughness and metalness. Canonical front engine +X, origin at the post's ground centre. Proposed engine position `-30,85,96`, yaw `-158.19859`; current ground/board height retained.

## Reproduce

Prefix shell commands with `rtk` in this repository.

1. `python Sources/Riverside/speed-sign-v2/build.py <project-root>` builds only the candidate geometry/materials.
2. Historical pre-installation step: `prepare_review.py` extracted the exact 16 published faces, preserving their original UVs/normals while translating/rotating into canonical coordinates. A separate render-only pad copy hid those faces. Do not rerun against the installed pad.
3. `python Sources/Riverside/speed-sign-v2/native.py script Sources/Riverside/speed-sign-v2/review.cs.txt` compiles/loads all three review models and renders matched front, full placement and rear shots in a disposable scene. Front/full views show the map; rear views hide world renderers so the nearby wooden pole does not obscure the mounting. Both variants use the same camera, locked exposure and temporary inspection light. The scene is destroyed in `finally` and the active user scene is preserved. A fresh saved-sandbag capture is also included.
4. Historical `verify.py` checked finite geometry, nondegenerate triangles/UVs, winding, bounded UVs, normalized tangent normals and pre-installation public pad/scene hashes. Passed for all three LOD meshes; its source hashes describe the review baseline.
5. `python Sources/Riverside/speed-sign-v2/compose.py <project-root>` arranges the front/rear native captures without colour edits.

Evidence: `output/asset-improvement-20261030/riverside-speed-sign/`. All models load without errors in s&box 26.11.03a. No gameplay or LOD transition playtest has been run. Installation preserves the old simple post collision and updates only the 16 original faces and the canonical `speed_sign` generator. Avoid full map regeneration.

## Installation

`prepare_install.py` staged a guarded cut against the latest public pad, backed up the source/ModelDoc/scene and generated the deterministic `Speed-Limit Signs` scene group. `install.cs.txt` verified hashes and models, published the narrow OBJ edit through the native editor, created the group in the active editor scene and marked it dirty. Native `save_scene` persisted it; native `asset_compile full=false` successfully compiled the public pad.

`verify-install.py` passed: one saved sign with the reviewed transform, only 16 old face lines removed, every unrelated line preserved, byte-identical pad ModelDoc/collision and all 54 saved sandbags retained. Evidence and backups are in `installed/`. A native capture of the saved installed sign is `output/asset-improvement-20261030/riverside-porch-light/new_installed_sign.png`.

The canonical generator now records `SPEED_SIGNS`, preserves the original simple post collider, carries placements through zone transforms and emits the `Speed-Limit Signs` group. No whole-map regeneration was run.

The earlier duplicate freezer candidate in `Sources/Riverside/ice-freezer-v2/` was archived when another chat installed the user's separately approved `ice-cabinet-v1`. That approved public cabinet was preserved.


The unused comparison background for this earlier review was archived/deleted during the approved porch-lamp retirement (2026-11-04) because it retained a cached dependency on the old lamp material. See Sources/Riverside/porch-light-v2/README.md and its installed/legacy-cleanup/ backups. Keep historical PNGs; do not rerun the original review script without rebuilding its background from current assets. The approved public model is unaffected.

# Riverside road entrance gate v1 — review candidate

Private replacement for the 440-inch-wide gate at plan `(0,-1290,96)`, engine `(-1290,0,96)`. Rejected by the user; retain the original gate. Never installed. Public pad geometry, scene and collision remain unchanged. The existing NO TRESPASSING sign and neighbouring fences remain visible in the comparison.

The original gate is an 82-triangle fence segment with three posts, one top rail, an uninterrupted mesh plane and three wire runs. The candidate has two closed rounded pipe frames, diagonal tension rods/turnbuckles, tension bars with clips/bolts, hinge barrels/pins, capped posts, a centre latch/drop bolt, an interlocking chain wrapped around both meeting rails, a brass padlock and twisted barbs on the three top wires. It is static dressing; no opening mechanism or gameplay changes.

Model: `models/props/riverside/entrance_gate_v1/gate.vmdl`. Three LODs: **20,652 / 13,632 / 3,464 triangles**, thresholds 30/70. One procedural 1024px colour/normal/roughness/metalness atlas and one new metal material; the existing `rs_chainlink` material supplies the mesh. No external assets. No new collision or lights in the candidate. These are authored budgets, with no gameplay performance or LOD-transition test.

All shell commands require the `rtk` prefix. Pass the canonical project root as the Python argument:

1. `build.py .` creates only private model/material assets. Coordinates are authored in engine axes then converted through the existing map kit.
2. `prepare_review.py .` generates the original gate in memory and matches its exact 82 published triangles by material and vertex positions. It hides those faces only in a private render-only pad copy; the original sign, neighbouring fence and all other pad geometry remain. It records production hashes in `output/riverside/entrance-gate-v1/review.json`.
3. `native.py script Sources/Riverside/entrance-gate-v1/review.cs.txt` compiles/loads both private models and captures old/new whole, centre hardware and hinge views with matching cameras, fixed exposure and temporary matched inspection light. It uses a disposable editor scene destroyed in `finally`; no active scene/play changes.
4. `verify.py .` checks finite/nondegenerate geometry, winding relative to normals, finite/nondegenerate UVs, normal-map validity and unchanged public hashes. Repeating UVs are intentional for the shared chain-link texture. All three LODs passed; both native models loaded without errors.
5. `compose.py .` lays out before/after captures without changing their exposure or colour.

Evidence: `output/riverside/entrance-gate-v1/`. For a later approved installation, recheck production hashes, remove only the 82 matched original render faces through the editor, place this model at engine `-1290,0,96`, retain the complete pad ModelDoc/physics and original sign, update the retained generator narrowly, save through the editor, and read back the result. Do not regenerate the entire map.

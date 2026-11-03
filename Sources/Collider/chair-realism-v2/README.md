# Collider chair v1 + v2 comparison

Both versions are retained for the user's in-game decision (2026-11-01).
V1 remains at its accepted location in the Structure mesh: world (-55,-1723,256).
The revised v2 stands 75 inches beside it: world (20,-1723,256), yaw 90 degrees.
Find them in the upper east control area, at the east console/desk row.

V2 is a separate saved scene object named:
Chair comparison - Revised v2 (woven / stitched)

To remove v2 later, remove that object (or disable it) in the Collider scene.
Also remove scene-addition.json to prevent the source generator adding it back.
Keep the private v2 assets while any other scene or prefab still references them.
V1's original source assets, all Structure geometry and map physics are preserved.
If v2 is preferred, v1 can subsequently be extracted/replaced as a separate change.

installed.json records object IDs, placement, source hashes and scope checks.
rollback/ contains the exact scene and generator before this addition. Do not restore
whole files over later unrelated edits; remove only the v2 object/generator addition.
The project was closed in the editor during this offline installation. In-engine
appearance and collision traversal need review when the project/map is next opened.

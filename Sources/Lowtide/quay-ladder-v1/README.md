# Lowtide quay ladder — installed

Approved and installed on 2026-11-03 after an actual offline play-mode check.
All six canal ladders (three on each bank) use the approved geometry. Only the
east/west architecture ModelDoc render imports/remaps changed; all original
physics and the saved scene are unchanged. Six fresh installed play-mode captures
have no error models and show a local player present. The menu and play state
were restored afterward. See `output/lowtide/quay-ladder-v1/installed.json` and
`runtime-installed/`. `Tools/lowtide_quay_ladders.py` retains the approved mesh
exactly and `lowtide_map.py` calls it for all six placements. Do not replay the
one-time installation over the installed imports.

The original ladder is at plan `(235, -1450)`, spanning z -132..18 inches on the
east canal wall. Its 168 triangles are square rails, flat rungs and two simple
brackets. The candidate uses continuous smooth rails and curved handholds,
round-ended anti-slip treads, wear strips, grip studs, wall standoffs, clamps,
bolted fixing plates and sealed tube ends. It uses existing Lowtide marine iron,
steel and cast metal finishes. No new textures or materials are introduced.

The replacement is 5,152 triangles. It remains visual dressing: no climbing,
collision, navigation, lights or gameplay components are added. Performance has
not been benchmarked. The curved returns and foot plates stay in front of the
existing railing: their maximum e is 241.5, ahead of its nearest post face at
241.8. Installation, if approved, must preserve the map's collision and routes.

`build.py` writes a guarded staging package. A review-only copy of the installed
east architecture removes exactly the original ladder triangles, preserving all
other vertex, normal, UV and face records and the ModelDoc's entire physics
suffix. `import.cs.txt` imports only the new review folder through the editor.
`review.py` compiles both models and captures before/after views in an isolated
copy of Lowtide's visual scene, destroyed in `finally`. The user's menu/editor,
play state and camera are left intact.

The comparison uses matching cameras, ACES, exposure 2.4 (within Lowtide's saved
2..3 exposure range), and identical ambient occlusion and bloom. Texture streaming
settles for 90 rendered frames per view, with no forced mip residency. `verify.py`
checks original source hashes, exact preservation of unrelated geometry and
physics, native error models and compiler health, then creates labelled sheets.

From the canonical checkout, run sequentially:

```powershell
rtk python Sources/Lowtide/quay-ladder-v1/setup.py
rtk python Sources/Lowtide/quay-ladder-v1/build.py
rtk python -u Sources/Lowtide/quay-ladder-v1/review.py
rtk python Sources/Lowtide/quay-ladder-v1/verify.py
```

Evidence and labelled comparisons: `output/lowtide/quay-ladder-v1/`.
Do not regenerate the whole Lowtide map to install this prop.

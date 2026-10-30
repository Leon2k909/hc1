# Collider fabrication and floor detail

The subsequent `Sources/Collider/wall-seams-v1/` correction trims coplanar accelerator-shell faces. Its receipt supersedes only this pass's machine OBJ hash and adds the regeneration hook; all craft materials, structure geometry and collision remain installed.

Installed in the canonical C: checkout on 2026-10-27. This pass addresses the repeated flat railing profiles and uninterrupted floors called out in the Depot comparison.

The accepted asset candidate is `output/collider-detail-v3-20261027/stage-v6`. `installed.json` records all nineteen source hashes, native review hashes, menu image, geometry counts and preserved editor state. The saved scene remains SHA256 `bf6a9feabd22b988276ec8cdb80f383e734e2ac733f38a4f923d404a14729802`.

## Construction

- Twenty guardrail runs, including eight stair runs: closed round tubes with smooth shading and cylindrical UVs, separate anchor washers/nuts, isolation pads, weld collars, occasional run joints and thin folded toe plates. Shared corner posts are deduplicated.
- Dedicated powder-coat color, normal, roughness and metalness maps. Hand-contact wear follows the upper circumference of the handrail. Background guards behind the accelerator glass keep round silhouettes with simpler fittings.
- Two actual floor openings with recessed steel drainage grilles and support bars; two split service covers with cut handle pockets, flush lifting rings, gaskets, screws and metal rims.
- Three shallow irregular spalls with exposed lower concrete, fractured lips and small aggregate pieces. The accepted depth is 0.68 inches. The original pale, pointed trial was rejected during close native review.
- Thirteen narrow control joints cut below the floor surface. They replace the floor triangles in their footprints rather than overlaying coplanar strips.

The structure changes from 109,614 to 169,073 triangles and the machine from 165,594 to 136,410. The unchanged detail/glass models contribute 132,960 / 84; the four base static models total 438,527 versus 408,252 previously, a 7.4% increase. This is source geometry accounting, not a frame-rate benchmark.

Original attribute tables and unaffected face lines are preserved. Both model physics suffixes, convex hull sources, gameplay placement and the saved scene are unchanged. The openings are shallow visual construction details, retaining the established walkable collision. The earlier two exposed Retakes A sightlines remain a separate documented layout issue.

## Native verification

Both models compiled successfully; the five new materials are valid. All 68 authored positions passed native support, player-box clearance and Complete navmesh paths, with no missing models/materials. Saved-scene validation also passes resource/dependency, stable-ID/reference, mode isolation, objectives and navmesh-setting checks across 420 objects/components.

`verify.py` independently checks exported geometry, winding, retained faces/attributes, physics suffixes, current installed hashes, protected resources and generator hashes:

```powershell
rtk proxy python -X utf8 Sources/Collider/craft-v1/verify.py --stage output/collider-detail-v3-20261027/stage-v6 --baseline output/collider-detail-v3-20261027/stage-v2/before --installed
rtk proxy python -X utf8 Tools/collider_validate.py --scene Assets/scenes/maps/Collider/collider.scene --report output/collider-detail-v3-20261027/scene-validation.json
```

The scoped native importer backs up targets and verifies exact before/after hashes. It locates the existing Collider document without selecting it, preserves the selected document and dirty/play state, and refuses play mode. Veridant remained selected during final import and publication. No scene was rewritten or saved, and no temporary objects, play session or background service were created.

GI `lighting-v6` and reflection cubes v4 are retained from the preceding pass. This pass does not claim a fresh lighting bake, full live-match, manual traversal, multiplayer test or performance benchmark.

## Capture quality

The user's comparison correctly exposed lower screenshot quality. The old path rendered a separate 1600x900 bitmap; it did not copy the final viewport image. Engine inspection confirmed the editor camera's anti-aliasing flag was enabled, so this evidence does not establish that the user's MSAA setting was off.

The canonical `Sources/Collider/editor/capture.cs.txt` now defaults to two times the requested dimensions, renders ordinary native camera frames, then filters down to the requested output. Current reviews render at 3728x1832 and resolve to 1864x916. Both native and resolved PNGs are retained. Material mips are warmed using the engine's [texture usage API](https://sbox.game/api/Sandbox.Texture/MarkUsed), and a disposable `EditorUtility.DisableTextureStreaming` scope requests full textures during rendering, following the installed editor's asset-preview implementation. Original current-view projection is preserved, and camera pose/FOV/axis/size/orthographic state is restored. No game quality preference is changed.

Background capture exposed a second issue: the sign atlas was sharp in native mip-zero readback but blurred when rendered while Veridant's editor session was active. Full texture requests alone did not fix it. `session.MakeActive(false)` for the synchronous render, followed by restoration in `finally`, corrected the signs without bringing Collider's tab forward. The helper refuses changed editor state after warming and records successful restoration. This is an observed editor-session context dependency, not evidence of a damaged texture file. Earlier background captures with blurred signs are superseded by the final corrected views.

Seven accepted views are in `output/collider-detail-v3-20261027/captures-final/`. Their report records the nineteen source hashes and verifies they did not change during capture. `rail-after.png` has a matched earlier view in `captures/rail-before.png`. Early floor/hatch shots were obstructed by cases and are excluded from presentation; use the final close views. Historical trial outputs are not the accepted result.

## Authoring and regeneration

`Tools/collider_craft.py` owns the rail geometry, location-aware floor details and coating maps. Hooks in `collider_detail_geometry.py`, `collider_map.py` and `collider_materials.py` preserve them in future generation. Existing photographic concrete maps from finish-v1 and Railhead's hardware normal/roughness maps are referenced unchanged; their provenance remains with their original source manifests.

`collider_stage_craft.py` matches old rail triangles at the OBJ writer's actual three-decimal precision, preserves unrelated geometry, clips floor polygons with interpolated UVs, and stages assets only. The retained original railing authoring is `original-detail.py.txt`. Cached rail call sites are source-hash guarded. Output uses the canonical logical path because this checkout's output folder is an offloaded junction.

All nineteen owned assets and the menu image were synchronized to the primary build stage under guards. Its pre-existing scene was deliberately preserved. The old native-v2 archive remains historical; packaging requires resolving that scene and refreshing the required evidence.

Keep `stage-v2/before/` for original model/MTL/physics rollback and `stage-v6/assets/` for the accepted result. The menu preview and canonical capture helper have before copies in this task's output directory. Restore assets through the editor while it is open, reviewing any newer work before rollback. The existing finish-v1 receipt is a historical checkpoint after these model changes.

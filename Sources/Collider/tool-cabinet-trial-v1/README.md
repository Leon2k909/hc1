# Collider approved maintenance cabinet

Installed on 2026-10-31 following explicit user approval of the right-hand native comparison. The selected
case at plan (-650,160,0) is replaced, including its old full-height box. Approved visible geometry and
materials are unchanged. The installed 39 boxes and ten hulls keep the underside and handle gaps open.
Four tyre collision hulls now use 32 sampled original points each; all 25 native installed-model checks
pass, including tyre contact rays that exclude the structure floor. The combined model is compiled and
up to date. Unrelated map geometry/physics and the saved scene are unchanged.

Current evidence: installed.json and output/collider-tool-cabinet-accepted-20261031/.
Regeneration: Tools/collider_tool_cabinet.py, accepted-physics.json and the exact selected hardcase branch.
Use finalize_install.py for current source verification; preview verifiers below guard historical inputs.
Rollback is outside Assets in the acceptance output. The active play session was not stopped or edited.

Private whole-object replacement for the saved equipment case at plan `(-650,160,0)`, near the lower-hall stairs. The before model is extracted from all 2,420 actual saved triangles with their UVs and normals. Its original `PhysicsShapeBox` is read from the saved detail ModelDoc and checked against the exported before resource. This describes the historical preview; the installation is recorded above.

The replacement has a fabricated steel shell, six returned drawer fronts, recessed runners, hollow metal pulls, a rolled stainless worktop and rubber mat. Four profiled rubber tyres, pressed swivel forks, mounting plates, cast hubs and forward brake tabs meet the ground. The rear includes a service panel and recessed ventilation details. Seven private materials supply position-based UVs, geometry-derived edge wear, fine coating relief, metalness and directional abrasion. Broad dark mottling is deliberately avoided.

Collision is authored alongside the render geometry: separate rounded body/worktop hulls, four profiled tyre hulls, four caster-pivot hulls, and individual drawer-front, fork, mounting-plate and grip boxes. There is no full-height box under the cabinet or solid rectangle behind either type of handle. Fine screws, mat ribs and labels do not create extra blockers. Small bevels are represented by close-fitting low-cost shapes. `verify.py` reads the exported ModelDoc and hull meshes and passes 46 geometry/collision probes. A separate running-game check passes 26 native physics rays, including solid drawer fronts, tyre/pivot bodies, ground contact and open underside/handle gaps.

The earlier offline reference renders use the actual OBJ/PBR channels with identical cameras, lighting, scale and exposure. Their Blender process has stopped. At the user's request, the current comparison was captured in the running Collider map: original left, proposed right, both at scale one in a single shared view. A temporary camera copied the player's post-processing and map exposure. Native 3840x2160 images are filtered to 1920x1080; front and oblique views show both whole objects without the first-person weapon. The temporary Collider document was discarded, and the original Ares document and previous Spillway runtime map/play state were restored. No exact match/round state restoration is claimed.

Native import exposed a normal/RMA mip-generation failure on 2046x1364 atlases. Native bitmap filtering produced 2048x2048 `_engine.png` maps while retaining normalized UVs and raw authoring maps. Six cabinet materials and four materials on the already approved pump now compile successfully. Geometry and physics are byte unchanged. `native-import-fix.json` records every material edit and original backup. Of the original 495 protected sources, 491 are unchanged and only those four explicitly archived pump imports differ; the updated guard also protects their sixteen new texture dependencies. Both authoring generators now produce supported atlas maps.

```
rtk proxy python -X utf8 Sources/Collider/tool-cabinet-trial-v1/build.py
rtk proxy python -X utf8 Sources/Collider/tool-cabinet-trial-v1/verify.py
rtk proxy python -X utf8 Sources/Collider/tool-cabinet-trial-v1/prepare_render.py
rtk proxy python -X utf8 Sources/Collider/tool-cabinet-trial-v1/render_low_impact.py
rtk proxy python -X utf8 Sources/Collider/tool-cabinet-trial-v1/finalize_review.py
```

Evidence is under `output/asset-improvement-20261030/tool-cabinet/native-review-20261031/`; `finalize_native_review.py` binds native images, source hashes, import fixes, native physics and cleanup evidence. The offline finalizer preserves an existing native review. The final export has 39 boxes and ten disconnected hulls. `collision-refinement/change.json` proves the earlier drawer/pivot refinement changed only the physics ModelDoc and metal hull mesh, preserving the visible OBJ and ModelDoc material remaps. Installation must replace the selected original visual and collider together after approval; retaining the old full-height case box would defeat the open underside. Other placements and map blockers must remain unchanged.

# Collider maintenance cabinet proposal

Private whole-object replacement for the saved equipment case at plan `(-650,160,0)`, near the lower-hall stairs. The before model is extracted from all 2,420 actual saved triangles with their UVs and normals. Its original `PhysicsShapeBox` is read from the saved detail ModelDoc and checked against the exported before resource. The map, scene and earlier accepted assets remain unchanged pending approval.

The replacement has a fabricated steel shell, six returned drawer fronts, recessed runners, hollow metal pulls, a rolled stainless worktop and rubber mat. Four profiled rubber tyres, pressed swivel forks, mounting plates, cast hubs and forward brake tabs meet the ground. The rear includes a service panel and recessed ventilation details. Seven private materials supply position-based UVs, geometry-derived edge wear, fine coating relief, metalness and directional abrasion. Broad dark mottling is deliberately avoided.

Collision is authored alongside the render geometry: separate rounded body/worktop hulls, four profiled tyre hulls, and individual fork, mounting-plate and grip boxes. There is no full-height box under the cabinet or solid rectangle behind either type of handle. Fine screws, mat ribs and labels do not create extra blockers. Small bevels are represented by close-fitting low-cost shapes. `verify.py` reads the actual exported ModelDoc and hull meshes, checks their positions/axes/dimensions, tests solid and empty-space probes, ground contact, fit within the original visible footprint and player-width clearance outside it. These are offline checks; native collision and appearance remain pending.

The two comparison views use the actual OBJ and four PBR channels with identical cameras, lighting, scale and exposure. `render.py` renders the whole before and after cabinet from the front, plus the full proposed rear. All work stays offline; a single hidden Blender process uses CPU rendering, two threads, idle priority and two logical CPUs. No editor is opened or connected.

```
rtk proxy python -X utf8 Sources/Collider/tool-cabinet-trial-v1/build.py
rtk proxy python -X utf8 Sources/Collider/tool-cabinet-trial-v1/verify.py
rtk proxy python -X utf8 Sources/Collider/tool-cabinet-trial-v1/prepare_render.py
rtk proxy python -X utf8 Sources/Collider/tool-cabinet-trial-v1/render_low_impact.py
rtk proxy python -X utf8 Sources/Collider/tool-cabinet-trial-v1/finalize_review.py
```

Evidence is under `output/asset-improvement-20261030/tool-cabinet/`. Installation must replace the selected original visual and collider together after approval; retaining the old full-height case box would defeat the open underside. Other placements and map blockers must remain unchanged.

# Ares bulkhead lamp — private review

This is an isolated replacement proposal for the lower-hall wall lamp at Ares plan
`(-1100, -300, 120)`, world `(-300, 1100, 120)`. It is not installed. No file under
`Assets`, game reference, light, collision or map generator is changed.

The before is all 24 saved triangles, UVs and normals extracted from the actual
`models/maps/ares/crate-v2/dressing-base.obj` import used by `ares_dressing.vmdl`.
`provenance.json` records the source, position and original dimensions.
`source-guard.json` fingerprints 389 original files, including the Ares scene,
active ModelDoc/import and existing Ares materials.

The new mesh has a stepped closed casting, actual lens retaining lip, separate
EPDM seals, a closed moulded prismatic glass volume, internal warm light bars,
curved protective cage, captive socket fasteners, wall anchors, side entry plug,
cooling ribs and a fictional service plate. It fits within the existing
10 × 6 × 4.2 inch envelope. Tiled PBR maps and the plate texture are private to
this proposal.

The comparison uses real model geometry rendered in Blender Cycles, with identical
camera, scale, wall, area lights, exposure and color management. These are offline
review renders; they do not represent native engine appearance or performance.
The screenshot `native-before.png` independently confirms the original lamp in
the existing editor scene. The temporary capture camera is destroyed by its
existing Bridge handler; editor scene/play/compile state remains unchanged.

Run from the canonical checkout:

```powershell
rtk proxy python Sources/Ares/bulkhead-lamp-trial-v1/prepare.py
rtk proxy python Sources/Ares/bulkhead-lamp-trial-v1/run_render.py
```

`run_render.py` owns one background Blender process, runs it at idle priority on
four logical CPUs, renders on CPU, and waits for/cleans up that process. The
existing interactive Blender process is left alone.

Final outputs: `bulkhead_lamp_review.blend` (packed textures and comparison scene),
`bulkhead_lamp_after.glb`, `bulkhead_lamp_after.obj`/MTL and `textures/`. The
exported candidate uses metres, +Z up and front -Y in the Blender/OBJ source.
The glTF exporter applies glTF's usual +Y-up conversion.

Review pictures and render settings are in
`output/asset-improvement-20261030/bulkhead-lamp/`. Native import, native materials,
LODs, collision policy and performance checks remain for a separate integration
step after the picture is approved.

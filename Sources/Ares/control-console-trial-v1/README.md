# Ares control console — private model review

An isolated rebuild proposal for the existing floor console beside Ares's central
processing column: plan `(230,-440,0)`, world `(-440,-230,0)`.
No game model, material, collision, light, scene or generator is changed.
The previously reviewed bulkhead lamp is preserved and remains uninstalled.

`before.json` copies all 40 saved triangles, UVs and split normals from the active
`models/maps/ares/crate-v2/dressing-base.obj` import used by `ares_dressing.vmdl`.
`provenance.json` records its origin and source hash. The selected console uses the
existing CORE / THERMAL screen tile. Its approved atlas is cloned byte-for-byte;
the candidate retains the saved screen UVs and full original picture dimensions,
lowered 1.38 inches along the original screen plane to accommodate a physical bezel.

The replacement has separate folded cabinet panels, a grounded plinth and neoprene
feet, gasketed service door, hinges, recessed latch, kick plate, open formed louvres,
an enclosed angled display chassis, retaining bezel, trunnions, rear cooling ribs,
individually modelled keycaps and legends, trackball, tactile switches, status lenses,
rotary selector, mushroom stop, side handles and rear cable glands/retained cables.
Private PBR maps distinguish powder coating, instrument finish, brushed steel,
rubber, keycaps and control materials. All dimensions fit inside the original
60 × 34 × 64 inch outer envelope.

Comparison images are offline Blender Cycles renders with identical camera, scale,
floor, lighting, exposure and view transform. The baseline display uses its original
no-specular setting, as the installed material specifies. These images do not claim
native engine appearance or performance. `native-before.png` independently shows
the original console in the current Ares editor scene. Its temporary capture camera
is removed by the existing Bridge handler; the editor remains clean and out of play.

Reproduce from the canonical checkout:

```powershell
rtk proxy python Sources/Ares/control-console-trial-v1/prepare.py
rtk proxy python Sources/Ares/control-console-trial-v1/run_render.py --validate-only
rtk proxy python Sources/Ares/control-console-trial-v1/run_render.py
rtk proxy python Sources/Ares/control-console-trial-v1/verify_export.py
```

One owned idle-priority Blender process uses four CPU threads; it renders without
GPU use and exits on completion. Existing editor and interactive Blender processes
are preserved. The final GLB joins the candidate into one mesh with material groups
and embeds its textures. The `.blend` retains editable individual parts and packed
images. OBJ/MTL and private textures are also supplied. Blender/OBJ source uses
metres, +Z up and front -Y; glTF applies its usual +Y-up conversion.

Outputs are `control_console_review.blend`, `control_console_after.glb`,
`control_console_after.obj`/MTL and `textures/`. Pictures, geometry/export checks and
render settings are in `output/asset-improvement-20261030/ares-control-console/`.
Native materials/import, LODs and performance validation belong to a later approved
integration step. `source-guard.json` checks 410 original files, including the Ares
scene/model/materials and the earlier lamp's sources and artifacts.

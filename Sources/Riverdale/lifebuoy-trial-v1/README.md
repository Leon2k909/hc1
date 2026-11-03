Riverdale lifebuoy — approved and installed, 2026-10-31

After the user approved the preview, all six original lifebuoys were replaced with shared instances of `models/maps/riverdale/lifebuoy_v2/lifebuoy.vmdl`. The native model uses the exact approved LOD0 geometry (42,468 triangles), with 9,342- and 1,910-triangle distance LODs. Six materials and their textures live under `Assets/materials/riverdale/lifebuoy_v2/`. The wall anchors and facing are preserved, with a quarter-inch stand-off to clear the raised epoxy coating. The original lifebuoys were visual only, so the new ones remain visual only.

The same approval requested a pipe overlap repair. The two horizontal service lines intersected the south vertical risers on both side walls. Four nested bypasses now route around the risers, with staggered cross-wall legs so the service pipes also clear each other. Including the raised insulation bands, the minimum clearance is 11.6 inches to the risers and 2.193 inches between the two service lines; the previous worst penetration was 9.4 inches. Four old straight-run collision proxies were replaced with twenty proxies following the new paths. The upper pipe markers remain outside the rerouted area and keep their original positions.

Only the 3,756 original buoy triangles and the changed pipe faces were removed from the published hall OBJ. Verification confirms every unrelated face, UV and normal was preserved. The scene gained the Lifebuoys group and the replacement pipe proxies; all other scene data was preserved. The generator records the new instances and bypass geometry, so a later map regeneration retains both fixes. Concurrent unrelated Riverdale edits were incorporated before installation. No editor commands or play-state changes were used.

The installation receipts, source backups and verification reports are in `output/asset-improvement-20261031/riverdale-lifebuoy/`. `verify_installed.py` checks the current mesh, all six scene instances, collision proxies, materials and generator hooks. `stage-validation.json` records fidelity to the approved geometry (maximum vertex error below 0.000001 inch) and winding checks. Native model compilation and an in-game visual check have not been performed; loading the updated scene must import the new model. The pipe comparison images are explicitly offline renders of verified source geometry.

The following describes the original review stage and its reproduction steps; the original extraction should not be rerun over the installed hall, where the old buoy faces have been removed.

Original review — 2026-10-31

Private model proposal for the wall-mounted lifebuoy in the Riverdale reactor hall. Nothing from this proposal has been installed into the game. The work uses offline geometry and renders, with no editor commands, scene edits or play-state changes.

The before mesh is extracted from the saved `Assets/models/maps/riverdale/riverdale_hall.obj`, including its original UVs and split normals. All 626 triangles match the existing `life_ring` geometry at plan wall position (1000, 300, 64), facing (-1, 0, 0). The saved scene has an enabled identity ModelRenderer for the hall ModelDoc. This is an existing player-visible prop, rather than an unused asset or a deliberately simplified stand-in. The original ring uses 16 radial segments and an eight-sided cross section; its grab line uses five-sided short segments.

The replacement has a continuous smooth moulding, separate thin white bands, a closed three-strand grab line, four retention straps with edge stitching, a stainless backplate and formed J hook, a protective hook sleeve, countersunk fasteners and soft wall bumpers. Six PBR materials use private 1K colour, roughness, metalness and normal maps. It keeps the same ring diameter, centre and wall anchor. The complete review mesh has 42,468 triangles. This is a close-view proposal; native material conversion, game LODs and in-engine checks belong to a later approved installation.

The images in `output/asset-improvement-20261031/riverdale-lifebuoy/` use the same camera, scale, exposure, neutral wall and lights. They are Blender Cycles renders, not native game screenshots. Original VMAT materials are approximated in Cycles; constant tint values receive sRGB-to-linear conversion. Lighting, tone mapping and the wall therefore differ from the user's game capture. No paint-over or generated replacement image is used.

`lifebuoy_after.glb` is the self-contained model export. `lifebuoy_after.obj` and its MTL are an alternative export; `lifebuoy_review.blend` contains editable parts and the matched review setup. Blender works in metres; the modelling recipe uses inches, with local +X right, +Z up and front -Y, wall at Y=0. These exports are not a direct replacement for the entire hall model.

Reproduce from the canonical project directory:

```powershell
rtk proxy python Sources/Riverdale/lifebuoy-trial-v1/prepare.py
rtk proxy python Sources/Riverdale/lifebuoy-trial-v1/run_render.py
rtk proxy python Sources/Riverdale/lifebuoy-trial-v1/verify_export.py
rtk proxy python Sources/Riverdale/lifebuoy-trial-v1/recheck_source.py
```

The render wrapper owns one hidden, idle-priority CPU-only Blender process on four logical CPUs, waits for completion and cleans up its own process on failure. It leaves existing interactive Blender processes alone.

Validation covers finite geometry, positive triangle area, assigned materials, wall-facing bounds, a single GLB mesh at identity, normals and UVs on every primitive, embedded textures, image hashes and the original material dependencies. The exact before snapshot is guarded as well. `recheck_source.py` confirms all original saved lifebuoy positions, UVs and normals and its enabled scene placement. Other work saved the live scene, regenerated compiled texture caches and changed unrelated hall geometry during this review; broad file hashes are recorded separately rather than claiming the whole map stayed unchanged. This task wrote no original game files. Any later installation should splice only the original buoy triangles and update the generator to preserve unrelated hall changes.

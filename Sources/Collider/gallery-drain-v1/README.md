# Collider gallery grate junctions

Narrow correction for the user's disconnected gallery grates and flat silver straps, 2026-10-27.

`Tools/collider_gallery_trench.py` replaces only the old four gallery strips and twenty broad silver straps. The transverse covers now meet the long covers at all four junctions, closing the original eight-inch breaks. The covers have a continuous bevelled galvanized rim, narrow paired metal panel lips, small dark installation seams and flush screw heads. The original grating surface remains in use. This is a fitted cover detail; it does not claim a new excavated drainage channel.

The new private `materials/collider/co_drain_frame.vmat` uses Railhead's existing galvanized color, normal and roughness textures, with metalness 0.8. Shared `co_silver` and the original grating material are unchanged. Red light still tints the steel naturally. Generator hooks in `collider_map.py` and `collider_materials.py` retain the correction.

Only `collider_detail.obj`, its MTL/ModelDoc and the new material are imported. The bounded migration removes exactly 288 matched old triangles, retains all other face lines and original attribute tables, and adds 9,280 triangles. The detail model changes from 132,960 to 141,952 triangles. PhysicsShapeList bytes and convex hull sources are unchanged. No scene, structure model, machine model, lighting, camera setting or gameplay placement is published by this task.

Both the material and model compiled successfully in the existing native editor. `verify.py` independently checks the exported geometry: no degenerate or reversed new triangles, original retained faces/attributes preserved, installed hashes matching the stage, and byte-identical physics source. Three matched native before/after views review a junction and a panel joint on the west gallery and the opposite gallery junction. Camera, active document, scene dirty flag and game state are restored. No new live-match, networking or performance result is claimed.

Evidence and rollback: `output/collider-gallery-drain-20261027/`. Keep `stage-v1/before/` and `stage-v1/native-before/` for the exact original assets, `stage-v1/assets/` for the reviewed candidate, and `before/` / `after/` for native 2880x1800 captures resolved to 1440x900. `installed.json` records accepted hashes and guarded synchronization of only the four owned files to the primary build stage; newer unrelated staged files are preserved. The existing staged scene and map preview are untouched. Restore any assets through the native editor, checking for newer work first.

The independent mesh check can be repeated with:

```powershell
rtk proxy python -X utf8 Sources/Collider/gallery-drain-v1/verify.py
```

`prepare.py` preserves its first baseline and refuses to overwrite an existing stage. Use a fresh candidate revision for subsequent changes rather than rerunning the import over an already installed result.

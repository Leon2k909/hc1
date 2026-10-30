# Collider environment finish v1

Installed in `C:\sbox-projects\hc1\forked-shooter-main` on 2026-10-27 after comparing the custom maps with Depot's construction detail, material transitions and localized wear. This is the first map's environment pass; the other maps have not received this pass.

## Accepted changes

- Matched concrete floor albedo, GL normal, roughness and AO at a physical 2 m repeat; cast-concrete wall/column relief at 1.805 m. Matte soffits replace the floor finish previously used overhead.
- Closed chamfered portal surrounds, smaller fasteners, gasket breaks, coved skirting and flush screwed stainless thresholds. Existing hazard boots remain.
- Restrained trolley scuffs near doors and footwear marks in circulation areas, with transparent atlas borders. Experimental coplanar floor-joint strips were removed after native review.
- Threaded suspension rods, nuts and ceiling shoes for existing hanging fixtures. No additional lights, runtime components or shaders.
- Native two-pass DDGI `lighting-v6`, 15 x 21 x 7 probes, with unchanged runtime settings/exposure. Four refreshed `reflection_*_v4.vtex_c` textures use ordinary camera faces and native sky-texture compilation; the known crashing GPU GGX route was not used.

The structure changed from 71,372 to 109,614 triangles: 1,440 old flat portal triangles were replaced and 39,682 detail triangles added. Original attribute tables, retained faces, the complete physics-definition suffix and convex-hull source are preserved. The detail, machine and glass model sources are unchanged. Existing automatic door objects remain.

`Tools/collider_finish.py`, `collider_map.py` and `collider_materials.py` retain the finish in regeneration. `Sources/Collider/lighting/` now retains the native-saved v6/v4 objects. The menu image is the final native `art.png` view.

## Verification and evidence

Accepted assets and guards are in `output/depot-finish-20261027/stage-v8/manifest.json`; `installed.json` records final installed hashes. The final native scene is SHA256 `bf6a9feabd22b988276ec8cdb80f383e734e2ac733f38a4f923d404a14729802`.

- Native asset import and root-model compilation succeeded. Six model renderers are valid, with no missing models or materials.
- All 68 authored positions passed floor support, player-box clearance and Complete navmesh paths after the final bake. `native-validation.json` identifies the exact saved scene.
- `verify.py --installed` independently checks finite geometry, added-face winding, retained source data, original collision definitions, installed asset hashes, protected resources and generator hashes.
- `scene-validation.json` passes all resource/dependency, stable-ID, internal-reference, mode isolation, Retakes role, objective and navmesh settings checks across 420 objects/components.
- `scene-owned-changes.json` verifies the only scene differences against the pre-pass native snapshot are three GI textures, four reflection textures and four recorded prefab-instance mapping key updates made by native saving. All other scene content compares equal; the mapping updates are retained, not hand-reverted.
- All 81 non-scene bake inputs still match their recorded hashes. The saved scene changed only through the verified native light-reference updates.
- Final photographs are `captures/{west-lab,east-lab,atrium,gallery}-after.png` and `captures/art.png`; matched earlier views use `-before.png`. Captures restore camera, selected document, dirty and game state. Reflections were captured immediately before the final removal of the experimental floor strips; materials were unchanged.

Run from the canonical project directory:

```powershell
rtk proxy python -X utf8 Sources/Collider/finish-v1/verify.py --installed
rtk proxy python -X utf8 Tools/collider_validate.py --scene Assets/scenes/maps/Collider/collider.scene --report output/depot-finish-20261027/scene-validation.json
```

No full live-match, manual traversal, multiplayer or performance benchmark was repeated for this pass. The earlier two exposed Retakes A sightlines from screen removal remain documented in `wall-removal-east`; this pass does not change that layout. The 20 earlier screen/sight rays were not repeated after the editor closed; collision preservation and the final native 68-position checks are the evidence for this visual pass.

## Publication and editor state

Native scripts in this folder perform the scoped asset import, GI bake, reflection capture/adoption and position checks. They attach to the existing stopped editor; use current native tool schemas and the session exchange directory. Do not reuse a timed-out mutation without inspecting its outcome.

The editor was closed after the final native captures. `finalize.py` therefore exports derived regeneration caches and the PNG from the exact saved scene while refusing any open editor. It never rewrites a scene, model or material. It checks native capture/navigation hashes, source and protected asset hashes, seven lighting files and the allowed scene differences before publication. It is safe to rerun with the editor closed and unchanged inputs.

All 36 owned asset/lighting/preview files were synchronized to `output/collider/stage`. Its existing `collider.scene.json` had a different hash and was preserved. `reviewed-collider.scene.json` beside `published.json` is the accepted saved scene snapshot; resolve the existing staged scene deliberately before packaging. The old native-v2 archive is historical and was not rebuilt. No play session, browser or background service was started by this pass; the editor was not relaunched solely to restore the original Depot tab.

## Source attribution

The retained `scans/manifest.json` contains source URLs and SHA256 checksums. Five downloaded source maps match their retained originals:

- [Hangar Concrete Floor](https://polyhaven.com/a/hangar_concrete_floor), Dimitrios Savva, CC0: diffuse, GL normal, roughness and AO; 2000 x 2000 mm.
- [Concrete Wall 009](https://polyhaven.com/a/concrete_wall_009), CC0: matching GL normal; 1805 x 1805 mm. The existing Spillway diffuse scan is referenced unchanged. Existing DX normals and unrelated scans are preserved.

## Rollback inputs

Keep `output/depot-finish-20261027/stage-v4/before/`, the original pre-pass source payload. Stage-v8 retains the final installed candidate. `lighting-cache-before/` and `map-art-before.png` preserve the replaced caches/preview; `output/collider/lighting-v5/visual-scene.json` preserves the pre-pass native scene. Review newer scene work before any rollback and restore through the native editor when it is open. Superseded trial payloads were removed only inside this pass's output directory; their manifests/evidence remain.

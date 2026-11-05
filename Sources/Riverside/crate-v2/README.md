# Riverside supply crate v2 — installed

Built 2026-11-03, verified in s&box 26.11.03a, and installed with user approval on 2026-11-04. All twelve supply crates now use the new model, scaled to their original three sizes. Their original collision boxes remain in the zone models.

The original is `riverside_parts.crate`: a flat, brown box with six timber trim pieces and a label. The new model is the 30 × 24 × 22 inch supply crate by the pad's loose tyre, at engine `(-80, -140, 96)`, yaw `-73.300756`. There are also smaller crate sizes elsewhere in the map; those need matching dimensions at installation.

The rework has individual slightly bowed boards, actual narrow joints, bevelled edges, corner battens, a five-plank lid with two cross battens, a floor, and 42 rusty nail heads. Different boards have different wood grain and tones, with end grain at the sawn ends. The lower boards and upright feet have mud and water staining. The front's invented shop stencils read `LUCKY STOP` and `DRY GOODS`, abraded through to the grain.

- Asset: `models/props/riverside/crate_v2/crate.vmdl`.
- Triangles: 4,368 / 1,938 / 496, with LOD switches 25 and 70 (estimates, no performance playtest).
- One 2048 × 2048 PBR atlas at about 30 px/in, one material. Wood and nails share colour, tangent normal, roughness, metalness and AO maps.
- Bounds: `(-15.03, -12.06, 0)` to `(15.03, 12.06, 22.06)`. Origin is bottom centre; engine X is the long side.
- No collision in the model asset. The map retains each original crate's collision box.

Wood crops come from the project's existing CC0 `brown_planks_03` scan by Rob Tuytel / Poly Haven, with matching normal, roughness and AO. Attribution and original file hashes are in `Sources/Belltower/scans/manifest.json`; source: https://polyhaven.com/a/brown_planks_03 . Crops avoid the photographed board joints, which are geometry here. Wear, end grain, ink and nails are authored by `build.py`.

## Reproduce and review

1. `python Sources/Riverside/crate-v2/build.py <project-root>` builds only the new assets.
2. `python Sources/Riverside/crate-v2/prepare_review.py <project-root>` makes a separate review pad model with exactly the original crate's 86 triangles removed. The original OBJ is never written. It snapshots hashes of the live pad and scene.
3. `python Sources/Riverside/crate-v2/native.py script Sources/Riverside/crate-v2/review.cs.txt` copies the script into the native session exchange directory, compiles/imports the candidate and renders in a disposable editor scene. It leaves the user's tab, selection and play state alone. It loads only nearby map models/lights, disables navmesh and avoids forcing every map texture to full resolution. The scene is destroyed in `finally`.
4. `python Sources/Riverside/crate-v2/verify.py <project-root>` checks finite/nondegenerate geometry, outward winding, valid UV triangles, normal-map unit length, and matching live-file hashes. It passed all three LODs.
5. `python Sources/Riverside/crate-v2/compose.py <project-root>` creates the labelled comparison from engine captures; it only arranges/resizes the images.

Evidence lives in `output/asset-improvement-20261030/riverside-crate/`. `old_*.png` and `new_*.png` show the original night lighting. `old-lit_*.png` and `new-lit_*.png` use the same temporary inspection light in the isolated scene. `before-after.png` explains that extra light. The current native script emits inspection-light captures; the original night captures are preserved from the preceding run. Every native model loaded without errors and used the intended material. No live match has been tested.

The earlier Blender `studio-*` captures were an intermediate check; some predate the corrected stencil UVs. Use the native captures for the final review.

## Installed result

`install.py` matched the old crates' authored vertices rather than using broad bounding boxes. It removed exactly 1,032 old triangles from the live pad, store and dressing OBJs (2, 3 and 7 crates respectively). It also cleaned the old crate faces from two unpublished comparison backgrounds so the obsolete material could be deleted without leaving dependants. All retained mesh lines and collision settings were verified against backups in `output/asset-improvement-20261030/riverside-crate/installed/before-install/`.

`install-editor.cs.txt` imports the revised models, removes the obsolete remaps and adds the `Supply Crates` group to the active Riverside scene. Scripts must explicitly set the editor session's `HasUnsavedChanges` before native `save_scene`; otherwise that tool can report success without writing script edits. The saved file was read back and verified to contain all twelve instances. `verify-install.py` checks placements, scales, model paths, preserved existing object IDs, exact removed face counts and unchanged model collision/settings.

The native dependency audit reached zero dependants for `materials/riverside/rs_crate.vmat`. `delete-legacy.cs.txt` deleted that asset through `Editor.Asset.Delete()`, including its compiled file and metadata. Shared `rs_wood` and `rs_signs` materials remain in use elsewhere. The materials generator no longer creates `rs_crate`.

`riverside_parts.CRATES`, `crate` and `carry`, plus `riverside_map.crate_objects`, retain the installation on future rebuilds. Do not regenerate the whole map for this change: the shared kit has drifted (CLAUDE note 094).

`capture-installed.cs.txt` read the saved scene and rendered the pad crate, store stack and north row with a temporary inspection light, without any added replacement props. It found twelve valid models and zero loading errors. Captures are under `installed/`. The active Riverside tab was left clean and out of play mode. No live match was tested.

The earlier comparison builders/capture scripts are historical and should not be rerun against the installed map. Use `capture-installed.cs.txt` and `verify-install.py` now.


The unused comparison background for this earlier review was archived/deleted during the approved porch-lamp retirement (2026-11-04) because it retained a cached dependency on the old lamp material. See Sources/Riverside/porch-light-v2/README.md and its installed/legacy-cleanup/ backups. Keep historical PNGs; do not rerun the original review script without rebuilding its background from current assets. The approved public model is unaffected.

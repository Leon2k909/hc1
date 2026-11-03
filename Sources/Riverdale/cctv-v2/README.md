# Riverdale reactor hall CCTV

Status: **installed and verified**, following the user's visual approval on 2026-10-31.

The camera keeps all ten wall anchors, aiming directions and the original scale. The replacement has
a chamfered aluminium enclosure, folded sunshield with turned-down edges, sealed front/rear covers,
recessed coated optics, a cast tilt mount, stainless captive screws, strain relief, cable and side ID plate.
Six dedicated PBR materials use restrained paint variation, rubber, metal, optical glass and a printed label.
There are no emissive lights, collision changes, gameplay changes or post-processing changes in the map.

`Tools/riverdale_camera.py` is the geometry source. The published `riverdale_hall.camera` now delegates to it;
`riverdale_map.configure` preserves the six dedicated material paths and UV scale. Runtime models remain
`models/maps/riverdale/riverdale_hall_detail.vmdl` and `riverdale_hall_fine.vmdl`, with existing scene references.
Materials are under `materials/riverdale/cctv_v2/`. Assets under `cctv_v2_review/` are historical previews.

## Review and preservation

`output/riverdale/cctv-v2/` holds native before/after captures (hero, wider context, south-wall camera and
rear inspection), the geometry manifest and the prepared install transaction. Captures use a disposable
editor scene, the saved Riverdale visual objects, identical viewpoints and exposure for both versions.
The disposable scene is destroyed in `finally`; the user's current scene, camera and play state are preserved.
An upper-walkway diagnostic view is occluded by existing map geometry and is not a useful review image.

Only the camera function's original 600 triangles are removed. The candidate adds 28,576 triangles across
ten cameras (~2,858 each). Every other published face retains its exact positions, UVs, normals and material.
The surrounding map was not regenerated. Installation spliced the reviewed camera delta into the latest
published meshes, preserving independent area monitor, notice board and first aid edits. Exact face counters
against pre-install backups confirm that all non-camera geometry is unchanged. Both published models compiled
successfully through native `asset_compile`, loaded successfully and exposed all six camera materials.
The installed native render reports zero error models and preserved editor/play state; its screenshot was
visually checked against approval. Project compilers report zero errors. Full gameplay performance was not benchmarked.

`installed.json`, `installed-source-verification.json` and `installed-native-verification.json` record these checks;
`installed-hero.png` is the native render. `retired/` retains pre-install copies of all eight changed files,
including the two generator modules. No scene edit or save was needed. No background helper or browser was left running.

## Commands (from the canonical project folder)

All shell commands must retain the user's `rtk` prefix.

```powershell
rtk python Sources/Riverdale/cctv-v2/verify_installed.py
rtk python Sources/Riverdale/cctv-v2/native.py script Sources/Riverdale/cctv-v2/capture_installed.cs.txt
```

`build.py` and `prepare_install.py` are historical, one-time migration tools and intentionally refuse an
already installed camera. Preparation splices the isolated camera delta into current published geometry,
preserves the latest material remaps and validates both generator edits. The native transaction checks all
source hashes before its first write, retains backups under `retired/`, and replaces files atomically.

`native.py script` copies C# scripts to the native session exchange directory. `capture_installed.cs.txt`
loads only the published assets in a disposable hall scene, without loading the review models or changing
the user's scene. It destroys the disposable scene in `finally`.

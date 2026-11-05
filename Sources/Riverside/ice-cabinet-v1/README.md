# Lucky Stop ice cabinet — installed 2026-11-04

User approved installation. The public store ModelDoc now includes the cabinet at all three LODs, with original physics preserved. Actual offline Riverside gameplay capture passed with one player and no error models. See `output/riverside/ice-cabinet-v1/installed-in-game.png`.

Branch: `codex/riverside-ice-cabinet-v1`. The public store ModelDoc now imports the cabinet with private `icev1_` material aliases. The saved Riverside scene and original physics section remain unchanged. Existing store and drinks-fridge meshes retain LOD mask 7; cabinet meshes use masks 1/2/4.

The original 14-triangle cabinet becomes a chamfered insulated cabinet with a gasket, pull handle, lock, three hinges, compressor louvers, service cover, fasteners and feet. Worn painted enamel uses color, roughness and normal textures. No emissive door panel.

- LODs: 4,692 / 2,444 / 1,248 triangles, switching at 0 / 20 / 45 engine distance thresholds.
- Original box collision: 38 × 30 × 60 inches; visual handle extends slightly beyond it.
- Local origin: base center; map placement: `622,-160,20`.
- New cabinet: `models/maps/riverside/ice-cabinet-v1/ice_cabinet.vmdl`.

## Authoring and original review workflow

`Tools/riverside_ice_cabinet.py` in the canonical checkout is the approved authoring helper. `install_generator.py` verified that it reproduces all three approved OBJ meshes exactly and patched only the ice-cabinet hook in `Tools/riverside_map.py`. No full-map regeneration was run. The original porch light and collision are retained.

The following original review steps target the pre-install baseline. Their source hashes and old-triangle guards intentionally prevent applying the replacement again to an installed store. Original installation inputs are retained under `install-before`.

Run `rtk proxy python Sources/Riverside/ice-cabinet-v1/build.py --project-root C:/sbox-projects/hc1/forked-shooter-main` against the pre-install baseline. The generator matches the original 14 cabinet triangles in the active store ModelDoc inputs, preserving the existing drinks-fridge upgrade and physics.

Copy `import.cs.txt` to the native CLI session exchange directory and invoke `run_csharp` with that path. It checks the manifest, imports only the unique candidate resource directories, and preserves editor state. Never overwrite the original store automatically.

For preview, copy `isolated-review.cs.txt` to the exchange directory and invoke it with `run_csharp`. It renders the original cabinet and candidate in separate temporary SceneWorlds with identical light and camera settings, then deletes both worlds. It works without stopping the user's running match. No computer-use automation or generated illustration is involved.

Run `rtk proxy python Sources/Riverside/ice-cabinet-v1/verify.py` to check finite geometry, triangle indices, unit normals, nonzero triangle area, native LOD triangle counts, collision dimensions and original source hashes. This also composes the two native captures into `output/riverside/ice-cabinet-v1/comparison.png` without changing the rendered images except resizing.

Installed evidence: `installed-runtime.json`, `installed-state-restored.json`, `installed-source.json`, `generator-verified.json`, and `installed.json`. `capture_installed.py` and `runtime-installed.cs.txt` check the public installed model in actual offline Riverside play, with existing map lighting, gameplay camera effects and no runtime model substitution. The old atlas panel is absent in the installed capture. Editor scene/play state is restored after checking.

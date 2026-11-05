# Railhead east-yard cable reel — installed

Reworks the wooden reel beside the goods shed at plan (1878, -1632, 0.3), with its axle along e. The original 47.2-inch diameter and 30.8-inch overall timber width are retained. The 260-triangle original is replaced in this private preview by a 28,904-triangle assembly with eighteen separate timber planks, narrow seams, chamfered rims, a true open axle bore, metal sleeves/washers/nuts, small fixing nails and twelve continuous cable windings.

After user feedback, the timber retains the original scanned wood material without tint changes. The original installed flange UVs supply its texture scale and offset; grain direction follows the new physical boards. All three timber aliases now use the exact original material text. The first proposal's geometry, normals and topology are unchanged; only wood UVs and material tints were revised. Three additional constant materials supply the rubber cable, aged steel and dark recesses. No lights or capture-only materials are added. The original single-box collision remains unchanged in the preview ModelDoc.

The preview removes exactly the old reel's 260 triangles from the currently installed east-yard source mesh. All other faces and vertex/UV/normal records remain untouched. The public east dressing ModelDoc's other mesh imports, including the approved barrier and extinguisher, are retained. The scene and all public assets are unchanged by the proposal.

From `C:\sbox-projects\hc1\forked-shooter-main`:

```powershell
rtk python Sources/Railhead/cable-drum-v1/build.py
rtk python Sources/Railhead/cable-drum-v1/setup.py
rtk python Sources/Railhead/cable-drum-v1/review.py
rtk python Sources/Railhead/cable-drum-v1/verify.py
```

Build stages outside Assets. Import uses the connected editor and source-hash guards, with incremental compilation. Review runs the actual offline map with a player and copies the gameplay camera effects. Both variants share the camera, lighting and exposure; normal streaming is allowed to settle. The runner then stops its own play session and restores the prior scene.

Artifacts: `output/railhead/cable-drum-v1/drum-comparison.png`, `validation.json` and `play-state-restored.json`. This is a visual/model-integrity check, not a frame-rate benchmark.

The first preview and mesh are retained under `output/railhead/cable-drum-v1/first-review/` so the texture revision can verify exact shape preservation.

Approved and installed on 2026-11-04. The public east dressing model imports `east_without_drum.obj` plus `installed_cable_drum.obj`, whose distinct `rh_cd_` aliases preserve the existing barrier's steel material. The approved standalone geometry/UVs/normals remain identical. `Tools/railhead_cable_drum.py` freezes the approved mapping and geometry in the east-only generator hook; the west reel stays as authored. The legacy collider is carried over. No saved scene edits or full map regeneration were required.

`verify_installed.py` compares the saved public model and the approved standalone proposal within the same actual play session: mean pixel error was below 0.6/255 for the timber face and cable windings. All six materials loaded, no error models, one player present, editor scene/play state restored. Receipt: `output/railhead/cable-drum-v1/installed.json`; screenshot: `runtime-installed/drum-installed.png`. The original preview verifier is a pre-install check.

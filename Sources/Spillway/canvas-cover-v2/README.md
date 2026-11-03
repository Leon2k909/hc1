# Spillway's canvas cover v2

Created and **installed 2026-11-03**, following the user's approval in Claude. Nothing is committed.

The old one is `spillway_map.equipment_cover` on the B2 loading deck (plan e 1480..1620, n -1770..-1640, z 128..218): five sheets of sagging
cards round a box, 11,520 triangles of `sw_tarp`, with two strap boxes of `rv_dark` over it. In s&box it reads as a flat mustard crate,
with an open seam down one corner and the straps as black bars. It was picked from s&box shots of Spillway's props (`Sources/Spillway/
cargo-props-v2/candidates.py`): the tanks, containers, jersey barriers, wall units and cases were fine.

The new one is a mustard-khaki cotton canvas thrown over a generator set on its skid, from Orion's tarp pipeline (`Sources/Orion/
tarp_pile_v2`): Blender's cloth solver drops a real 24 x 25 ft sheet on the load, and four walls tuck its hem in short of the deck's
railings (30 in off at the map's south, 40 in at its west). Two orange ratchet straps lie where the old strap boxes were, with steel
ratchets on the north side and hooks at the skid. Seams, stitched hem, brass grommets, corner patches, storage creases, water staining and
a faded stencil, B2 GEN 2 (the map's own deck name), are painted on the flat sheet so they follow the folds.

- Triangles, LOD 0-2: 24,059 / 10,103 / 3,331 (thresholds 30 and 90). One 2048 atlas, about 6 px/in on the sheet, 48 on the straps.
- Bounds: x +-87, y +-92, z 0 to 90.4 in, against the old 140 x 130 x 90 box. Its X is the map's n and its Y the map's -e, so it's placed
  at engine (-1705, -1550, 128) with no turn.
- Its colour is the old cover's as the game draws it: the live `materials/spillway/sw_tarp.vmat` is `canvas_plain` tinted 0.78, 0.69, 0.54,
  not the green canvas `spillway_map.py` names. A first paint in plain khaki read olive beside it.
- No physics: the old cover's collision box (in the east model's hulls) is what the load fills, so it stays and cover doesn't change. The
  skirt spreads up to about 22 in past it at deck level, with no collision.
- Every cloth face turns to face away from the load: the engine lights a back face as if it faced the way its front does, and folds of
  the skirt that turn over had drawn as a dark blot.

Files: `make_canvas_py.py` writes `canvas.py` from Orion's `tarp.py` (each change must match once); `canvas.py` (sim, clay, build, bake,
export); `paint_canvas.py`; `finish.ps1` runs them at idle priority. `cut_old.py` writes temporary models into `Assets/models/compare_old/`
(the old cover with its straps, the rest of the east model's `rv_dark` faces, and `hidden.vmat`); `compare.py` / `compare.cs.txt` shot
matched before and after in an isolated copy of Spillway, hiding the east model's `sw_tarp` and `rv_dark` slots and putting the other
`rv_dark` faces back for "after". The ten cover-specific comparison source files and metadata were archived out of Assets after installation;
their two compiled model caches were also archived. The shared `hidden.vmat` remains for other comparisons. Work and shots:
`output/asset-improvement-20261030/spillway-canvas/`, sheets in `matched/sheet_1.png` and `sheet_2.png`.

## Installed state and checks

- `spillway_east.obj` has only the old cover's 11,520 `sw_tarp` faces and the 48 strap faces removed. Its collision and all other lines
  match the pre-install copy byte for byte after those cuts.
- The saved scene adds exactly one `B2 Canvas Cover` under `Spillway`, at `-1705,-1550,128`, with one renderer and no collider. Everything
  else matches the scene backup. The open editor also contains that one valid model at the same position, and has no unsaved changes.
- `Tools/spillway_map.py` retains the original invisible collision box in `east_works()` and places the new model in `scene()`, so a future
  rebuild keeps the replacement. The generator was syntax-checked, not rerun over the map.
- Native s&box check of an isolated copy loaded from the saved scene: 1 cover, 0 cover colliders, no error models. Rays hit the old box's
  top at z 218 and north face at n -1640; rays beyond its sides hit the deck at z 128. Four installed renders were checked, including the
  low side and distant view. Not playtested in a match; the user's edit/play state was preserved.
- Code compilation succeeds with zero errors; existing project/library warnings remain. The post-validation console check had no new
  errors. A prior buffered `IndirectLightVolume` texture-read error predates these checks.

Rerun the installed check from the project root: `rtk python Sources/Spillway/canvas-cover-v2/check_install.py [folder]`. It uses a native
MCP connection, writes its script in that session's exchange directory, destroys its isolated scene, and disconnects without closing the
user's editor. It streams the cover atlas at 2048 and other map textures at 1024. Results: `installed/native-validation.json`,
`installed/static-validation.json`, and `installed/installed_*.png` under the work folder above.

`install_canvas.py` is the guarded one-time installer Claude already ran. Do not rerun it to install again or hand-edit an open scene;
its expected-face and duplicate checks now stop it. Rollback copies: `retired/spillway_east.obj` and `retired/spillway.scene` under the
work folder. The retired scene includes the earlier four pallets and four control desks. Restore through the editor as appropriate,
and reverse the cover-specific generator edits if rolling back. Archived comparison assets are in `retired/comparison_sources/`;
`cut_old.py` expects the original east mesh, so it cannot recut from the installed mesh.

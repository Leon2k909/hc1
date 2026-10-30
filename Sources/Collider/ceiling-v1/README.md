# Collider ceiling and beam-mounted luminaires

Installed in the canonical C: checkout on 2026-10-27. Accepted assets and the guarded import are in `output/collider-ceiling-v1-20261027/stage-v3`; `installed.json` identifies the exact nine reviewed files.

The 36 solid hanging rectangles are replaced with suspended two-channel industrial lights: flange clamps, paired yokes, fasteners, cooling fins, end plates, an open-bottom casing with recessed lenses and sealing rims, a driver enclosure, cable gland and connected conduit. No runtime point lights were added. Nine plain solid beam envelopes become fabricated flanged beams with subtle edge bevels and web stiffeners. A dedicated matte concrete surface replaces the coarse cloudy steel finish on the three ceiling undersides. Narrow joints have recessed beds and return faces; they are cut into the replacement underside rather than overlaid on the old face.

The installed legacy beams were single 18-by-34-inch solid cuboids. The maintained generator already described separate flange/web members. `collider_ceiling.old_parts(published=True)` matches the installed mesh for migration; its default matches generator geometry. Both produce the same new fabrication. `Tools/collider_ceiling.py` owns the construction and private materials; `collider_map.py` and `collider_materials.py` retain it on regeneration.

Only the structure's OBJ, MTL and material remaps, plus six private material/texture files, were installed. Original retained OBJ attributes and unaffected face lines remain in order. The existing ModelDoc physics suffix is byte-identical, and the saved scene was neither rewritten nor saved. No existing gameplay placement, other model, shared material, or light component was changed by this pass. Primary staged copies of all nine owned files were synchronized under hash guards; its scene was preserved.

The structure changes from 169,073 to 208,601 source triangles: 546 old triangles removed and 40,074 added. This is geometry accounting, not an FPS measurement. Retain `stage-v3/before/` for rollback through the native editor, reviewing any newer work first.

## Verification

- Native compilation succeeded for the structure model and all three new materials.
- All 68 native support, player-box clearance and Complete navmesh path checks passed; zero missing models/materials.
- Actual rounded OBJ export has zero winding errors or degenerate triangles; minimum added triangle area is 0.008660 square inches.
- The generator hook was exercised on the authored shell/wings and retains the same 136 collision boxes and four hulls.
- Matched native before/after views are `before/` and `after-v3/` in this pass's output. Captures render 3000x2000 and resolve to 1500x1000, use the existing editor session, warm textures and restore the camera, selected document and play/dirty state. The final report includes all private ceiling sources.

The existing GI and reflection bake were retained. There was no fresh lighting bake, live-match performance benchmark or multiplayer test in this local ceiling fix. Earlier fabrication receipts describe historical model hashes after this revision.

`stage.py` creates a private candidate from current published sources and refuses unmatched legacy faces. `import.cs.txt` installs only the whitelisted nine files through the editor, with exact before/after hashes, collision checks and rollback. `publish.cs.txt` requires the native checks and matching reviewed source hashes before recording acceptance.

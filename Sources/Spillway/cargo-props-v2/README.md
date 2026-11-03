# Spillway's yard pallet v2

Created and installed 2026-11-03, at the user's word ("Yes, install it") after same-camera before and after shots in s&box. Nothing is committed. Notes: `docs/notes/193-*`.

The old "pallet" in `Tools/spillway_map.py`'s `cargo_yard()` is seven flat grey slabs, 20 x 49 x 5 in each, floating 2 in off the floor beside
container 02 (plan e -285..-111, n -712..-663), with no collision. It was chosen from s&box shots of the yard's props (`candidates.py`):
the hose coil is passable, the steel cabinets are boxes but hidden under the A1 stairs, and the cases are plain but fine.

The new one is a used 48 x 40 in stringer pallet, 4.75 in tall: three 2x4 stringers with fork notches, seven top boards and three bottom
boards, nailed, one board chipped at a corner and one paler where it was mended (off-centre, so a pallet turned end for end differs).

- Triangles, LOD 0-2: 964 / 482 / 192 (LOD thresholds 30 and 80). One 2048 atlas at 25 px/in. All 13 pieces face outward (`check_outward.py`).
- Surface from a real scan: Poly Haven's CC0 `wood_planks` (`Assets/materials/forestbase/scans/`, licence in its `LICENSE.txt`). Each
  board face samples its own stretch of one of the scan's nine planks at about 36 px/in, so no two match; its height is integrated from
  the scan's normal map. End grain, nail heads with rust bled into the wood, and yard dirt low down are painted on top.
- Collision: one box, 48 x 40 x 4.75 in, surface `wood`. The old slabs had none. That's a choice to put to the user.
- Its length is +X and its width +Y, standing on the ground about its origin. A plan heading along e is an engine yaw of 90.

Files: `pallet.py` (Blender: build, bake, export), `paint_pallet.py` (maps), `candidates.py` / `candidates.cs.txt` (the yard's props as the
game draws them), `compare.py` / `compare.cs.txt` (old and new side by side in an isolated copy of Spillway in s&box; nothing saved).
`compare2.py` / `compare2.cs.txt` are the clearer, matched before and after the user asked for: the same four cameras over the real spot
(the map's slabs hidden for "after" by `Assets/models/compare_old/hidden.vmat` on the cargo model's `rv_desk` slot) and over open sunlit
floor (the old slabs there are `cut_old.py`'s copy, `Assets/models/compare_old/spillway_slabs.*`). Both of those are temporary: delete them
once the user has decided. Sheets: `output/asset-improvement-20261030/spillway-cargo/matched/sheet_sun.png` and `sheet_place.png`.
Work files and shots: `output/asset-improvement-20261030/spillway-cargo/`. Run order:

```
blender_idle.ps1 -Script pallet.py -Log build.log <work> <root> build bake
python paint_pallet.py <work> Assets/models/maps/spillway/pallet_v2
blender_idle.ps1 -Script pallet.py -Log export.log <work> <root> export
python Sources/Gameplay/capture-flag-v2/check_outward.py Assets/models/maps/spillway/pallet_v2/pallet_lod0.obj pallet
python compare.py pass2
```

(`blender_idle.ps1` is `Sources/Belltower/props/pew-v2/blender_idle.ps1`.)

**Installed** by `install_pallets.py` (dry run without `--apply`): the slabs' 84 faces (the only `rv_desk` ones) are cut from
`Assets/models/maps/spillway/spillway_cargo.obj`, and the scene has `Yard Pallet 1-4` under `Spillway` (copies of `Control Desk 1`'s object:
a ModelRenderer and a static ModelCollider): singles at e -258 and -139, a stack of two at e -198, n about -688, engine yaws 92, 269, 94.5
(the top one) and 276. `Tools/spillway_map.py` no longer draws the slabs and places the same four in `scene()`, though the map's script
isn't rerun (as for the desks). Retired copies: `output/asset-improvement-20261030/spillway-cargo/retired/`.

Checked in s&box on 2026-11-03 with `check_install.py`, in an isolated editor scene loaded from the installed scene file (no play
session): 4 pallets with colliders, no error models, the slabs gone from the recompiled cargo model, and 7 rays as expected (tops at 4.75
and 9.5 in on wood, the floor in the gap and past the last pallet, the row's ends at e -282 and -221). Not checked: a real match (walking
over them, bullets, bots' paths), as play wasn't started in the shared editor.

The temporary comparison files in `Assets/models/compare_old/` (`spillway_slabs.*`, `hidden.vmat`) were deleted after the install, so
`compare2.py` no longer runs as it is.

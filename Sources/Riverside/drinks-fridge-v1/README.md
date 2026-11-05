# Riverside porch drinks fridge — installed

Replaces the porch fridge's flat illuminated product picture with a stocked glass-door cabinet. Approved and installed on 2026-11-04. The public `riverside_store.vmdl` imports the private store mesh with the old fridge removed plus the approved fridge mesh. The initial installation left the saved scene unchanged; the later wall-placement fix moved its existing light.

The cabinet keeps the original 30 × 28 × 72 footprint, now at plan centre (96, 624), base z=20, facing south. Its rear is two inches from the storefront wall. It includes 32 separate drinks, four wire shelves, recessed liner, clear glass, gasket, hinges, metal pull handle, compressor grille and a raised DRINKS plaque. Drink labels use local geometry glyphs. The replacement has 34,152 triangles; the original box and picture card have 14.

The existing porch-fridge light is retained and follows the cabinet. The visible interior diffusers reuse the map's cool lamp material; no capture-only lights are added. The preview store mesh removes only those 14 original fridge triangles. The wall-placement fix translates only the fridge's mesh positions and its existing physics box; all other mesh records and physics stay as installed.

## Reproduce

Run from `C:\sbox-projects\hc1\forked-shooter-main` with the existing editor connected to this checkout:

```powershell
rtk python Sources/Riverside/drinks-fridge-v1/build.py
rtk python Sources/Riverside/drinks-fridge-v1/setup.py
rtk python Sources/Riverside/drinks-fridge-v1/review.py
rtk python Sources/Riverside/drinks-fridge-v1/verify.py
```

Build writes outside Assets under `output/riverside/drinks-fridge-v1/stage`. Review uses a guarded native editor script to import private assets and requests incremental compilation. Capture requires a stopped, saved editor scene, starts an offline Riverside play session, captures the original and candidate with the same camera and post effects, then stops its session and restores the prior editor scene. It aborts if another session takes over. Texture streaming is allowed to settle normally; no forced residency is used.

The approved comparison is `output/riverside/drinks-fridge-v1/fridge-comparison.png`. The installed public asset was checked in actual play mode without runtime replacement geometry; its capture is `runtime-installed/fridge-installed.png` and its receipt is `installed.json`. All nine private materials loaded. The original collision and porch-fridge light are preserved. `Tools/riverside_drinks_fridge.py` retains the approved geometry in the porch-only generator hook; interior fridges remain as authored. No full Riverside regeneration or performance benchmark is performed.

`prepare_install.py`, `install.cs.txt` and `verify_installed.py` record the original guarded installation and play audit. Their historical hashes predate the later placement fix.

## Wall placement fix (2026-11-04)

- Moved the porch cabinet 64 inches toward the store, from world centre (560, -96, 56) to (624, -96, 56). The rear is at x=638 and the wall begins at x=640.
- Translated only vertex positions in `drinks_fridge.obj`; faces, UVs, normals and materials are unchanged. Moved just its metal physics box in `riverside_store.vmdl`.
- Moved the existing `fridge 77` point light from (534, -96, 63.2) to (598, -96, 63.2), and saved through the native editor. Every other saved scene value is unchanged.
- Updated the porch-only generator hook's geometry, collider and light location, plus the private mesh builder. The full map generator was not run.
- Native compilation passed. Five native rays confirm the new cabinet front, its rear, the wall, the clear old footprint and the clear store doorway. The moved generator
  reproduces the installed vertex positions and collider. The position was visually checked in the editor; this relocation has not been checked in live gameplay.
- Current verification: `rtk python Sources/Riverside/drinks-fridge-v1/verify_wall_move.py`. Before/after editor captures, guarded move plan and receipts are in
  `output/riverside/fridge-wall-placement-20261104/`. `prepare_wall_move.py` stages the one-time move against explicit source hashes; it must not be rerun after installation.

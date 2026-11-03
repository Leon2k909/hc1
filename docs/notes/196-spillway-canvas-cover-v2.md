## Spillway's canvas cover v2 (`canvas_cover_v2`, B2 loading deck, 2026-11-03)

- Installed following the user's approval in Claude; Codex completed validation, comparison cleanup and notes. Nothing committed.
- `models/maps/spillway/canvas_cover_v2/canvas_cover.vmdl` replaces the mustard box on the B2 deck with simulated canvas over a generator,
  orange ratchet straps, stitched seams, grommets and a faded B2 GEN 2 stencil. One 2048 atlas; 24,059 / 10,103 / 3,331 triangles,
  LOD thresholds 30 / 90. Tint matches the live map material rather than the generator's older material definition.
- Exactly 11,520 old cloth faces and 48 strap faces were cut from `spillway_east.obj`; all other OBJ lines match the rollback copy.
  The saved scene differs from its rollback copy only by the added `B2 Canvas Cover` renderer at `-1705,-1550,128` under `Spillway`.
- No new collision. The east model retains the old 140 x 130 x 90 in solid box; the canvas skirt extends up to about 22 in beyond it
  and remains pass-through. `Tools/spillway_map.py` keeps that invisible box and places the new renderer on rebuild. Generator syntax
  checked, without regenerating the map.
- Native s&box validation: one valid cover in the saved scene and open editor, no cover collider or error models. Four rays match:
  box top z 218, north face n -1640, and deck z 128 beyond both sides. Four installed renders visually checked. All code compilers
  succeed with zero errors; existing warnings remain. No new console errors during validation. Not checked in a match.
- Ten temporary cover-specific comparison files and metadata, plus two compiled model caches, archived out of Assets;
  shared `models/compare_old/hidden.vmat` retained.
  Validation did not change the user's active scene or play state. Sources, rerun instructions, captures, receipts and rollback locations:
  `Sources/Spillway/canvas-cover-v2/README.md` and `output/asset-improvement-20261030/spillway-canvas/`.

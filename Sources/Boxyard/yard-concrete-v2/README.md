# Boxyard yard concrete v2 (2026-11-09)

**Status: approved by the user on 2026-11-09 and kept. The old concrete (`materials/boxyard/bx_concrete.vmat` and its
three textures) stays, at the user's request, for use on another map. `python install.py revert` still puts the old
floor back.**

The yard's floor is half of every frame on Boxyard. It was one procedural 4096 px picture stretched over 64 ft
(**5.3 px/in**): pale, soft and blurred at a player's feet. This replaces the floor's material with two layers built
from a real scan.

| Layer | What | Density |
|---|---|---|
| slab tile `yc_slab_{color,normal,rough}` 4096 px | one 16 ft slab. Poly Haven `concrete_floor_02` (CC0, 2 m square, already in the project at `Assets/materials/forestbase/scans/`) laid at its true scale and quilted from sixteen turned, shifted patches so the 2 m scan never shows as a grid; half desaturated and cooled toward a port's grey, values kept strong; sawn joint with sealant, dirt and spalled edges on the tile's border | **21.3 px/in** (4 x the old) |
| macro layer `yc_macro_detail` 4096 px | the whole yard, nine by nine slabs, multiplied over the slabs through `complex.shader`'s detail slot (Mod2X): each slab's own tone, weather staining, tyre rubber, oil, rust ghosts where containers once stood, dirt at the wall's foot and round what stands in the yard now (read from `boxyard_containers.obj` and `boxyard_props.obj`) | 2.4 px/in, locked to the world |

The slab joints sit where the old texture drew them (192 in), so the painted lines and container bays still line up.

## Pictures (real editor viewport, matched)

`output/boxyard/yard-concrete-v2/`: `before_*.png`, `after_*.png` and `compare_*.png` (side by side) for three views, plus
`after_top.png` (from above, to check the macro layer's placement). Each pair is the Boxyard tab's own viewport camera at
the same pose (engine units, FOV 80), the same crop of the editor window, the scene's own lighting and post settings.
The viewport's grid and gizmos were switched off for both sets (a display toggle, put back afterwards).

| View | Position | Pitch, yaw |
|---|---|---|
| A lane | -700, 0, 64 | 3, 0 |
| B open yard | 690, -430, 64 | 5, 145 |
| C at the feet | 560, -380, 64 | 30, 150 |

## Files

* New: `Assets/materials/boxyard/yard_concrete_v2/` (`bx_yard_concrete.vmat`, four textures), this folder (`build.py`,
  `install.py`, `verify_generator.py`).
* Changed: one line in `Assets/models/maps/boxyard/boxyard_yard.vmdl` (the `bx_concrete.vmat` remap), and
  `Tools/boxyard_map.py` (`YARD_CONCRETE`, set on the yard model in `build()`).
* Kept: `materials/boxyard/bx_concrete.vmat` and its textures, free for another map (a 768 in tile, 4096 px colour and
  normal, made by `Tools/boxyard_materials.py`). The ground outside the wall (`boxyard_backdrop`) still uses
  them, so both concretes are loaded on Boxyard: about 41 MB more compiled texture data
  (slab colour 8.7, normal and roughness 21.6, macro 10.7), which is about that much more video memory at full
  resolution. Halving the macro layer to 2048 px would save about 8 MB and soften only the oil spots.

```
python Sources/Boxyard/yard-concrete-v2/build.py           # both layers and the material (several minutes)
python Sources/Boxyard/yard-concrete-v2/build.py macro     # the macro layer only
python Sources/Boxyard/yard-concrete-v2/install.py         # floor uses the new material
python Sources/Boxyard/yard-concrete-v2/install.py revert  # floor back on the old material
```

An open editor recompiles the yard model and the material by itself after either command.

## The generator

* `Tools/boxyard_map.py` writes the new remap on a regeneration. `python verify_generator.py` builds the generator's
  yard model into a temporary folder and compares it with the installed one: obj, mtl and vmdl identical (2026-11-09).
  Setting `install.py revert` by hand is undone by the next regeneration unless the `YARD_CONCRETE` line in `build()`
  is removed too.
* Run `build.py macro` whenever containers or heavy props move, because the contact dirt is drawn from their footprints.
* The macro layer only fits this floor quad (UVs `u = 1.60318 + (840 - x) / 768`, `v = 2.45799 + (z + 872) / 768`).
  `build.py` keeps those numbers at its top; a changed floor card needs them updated.

## What was learned (for the next floor)

* The detail slot multiplies in linear space (`albedo *= 1.99 * texel`), so a ratio r in the texture draws as about
  r^0.45 on screen. The first macro layer was authored by eye and was invisible. `build.py` now stores `ratio ^ 2.2`.
  The most the layer can brighten is x1.99 linear (about x1.37 on screen).
* Detail UVs are taken from the mesh UV before `g_vTexCoordScale`: `uv_d = sc * uv - 0.5 * sc + off + 0.5`.
* The yard model lands in the world as (X, Y) = (OBJ z, OBJ x) and the importer flips v. Checked with a numbered
  calibration texture from above; slab joints fall exactly on the macro layer's ninths.

## Not verified

* Seen in the editor viewport only. Not seen in a running match, at 1920 x 1080, or with bots; FPS and video memory
  were not measured (the figures above are from file sizes).
* Collision, navigation and geometry are untouched (only a material remap changed), so none of that was retested.
* The generator was checked for the yard model only; a full regeneration of Boxyard was not run.

# Burn drum v2

Created 2026-10-30 and installed on Riverside the same day at the user's word ("yeah replace with new and do another"). Seen in s&box on 2026-10-31
in an editor capture with the map's real flames and light, but **not yet in a live match**. Nothing is committed.

## Why this one

The wall-buy board was the weakest thing players see in Zombies. This is next. Burning drums are in Riverside's reference picture and
stand along the routes players run all match, but `riverside_parts.drum` makes each one a 14-sided cylinder in a flat tint, with rust
bands, a flat ember card and six glowing quads floating on its side for air holes (164 triangles). The other Zombies props are taken
or not seen: the ammo case and cash bag are another session's, and power-up drops are off.

## What it is

A 55 gallon drum made into a burn barrel:

- A sheet-steel shell with real wall thickness, rolled chimes, two rolling hoops, and dents that move both walls together.
- The lid chiselled out, leaving a jagged ring, and six air holes cut right through, so you see the hot inside through them.
- A lumpy ember bed with coals, and four logs charred into alligator skin, with heat in their cracks.
- Paint that browns and blisters as it climbs, then burns off to a dark scale. Soot rises from each air hole and over the rim, rust runs
  from under the hoops, and mud splashes up from the ground.
- Invented lettering: "WASTE OIL", "55 GAL LOT 3381".

One mesh and four models, for what the map uses: `burn_drum_blue` (4 on the map), `burn_drum_red` (3), `burn_drum_rust` (5) and
`burn_drum_cold` (2, with ash instead of embers).

## Numbers

- Triangles: 3,666 / 1,648 / 944 (LOD 0-2), against 164 and no LODs. 14 on the map. LOD 2 stays that high because at 444 the air
  holes' tunnels smeared into dark streaks up the side.
- One 2048 atlas layout, about 24 px/in on the outside. Four colour maps, roughness, metalness and normal for each of the two shell
  states (painted, rust), one AO and one glow mask. The glow is `F_SELF_ILLUM` with the mask at brightness 4.5. The old embers are 8.
- Same size as the old drum, same axes, origin on the ground at its axis. Radius 11.68 against 11.65, and 11.72 on LOD 1 and 2, as
  decimating moves points. Height 34.5. The bed is at the old height, 75% up, under where `MapFire`'s flames sit.
- No physics in the vmdls: the old hull (14 sides, radius 11.25) stays the collision.

## How it's installed

- `riverside_parts.drum` now keeps only the hull and the `FIRES` entry and records a placement, and `riverside_map.py` writes a "Burn
  Drums" group of 14 `ModelRenderer`s, each turned by the golden angle so no two show the same dents.
- **`riverside_map.py` wasn't rerun, because that isn't safe now.** An unmodified run changed the ground, levee and pad as well as the
  dressing, and reported paints with no material (`rv_steel`, `rv_yellow`, `rv_zinc`), because the shared kit has moved on since the map
  was last generated. So `install_drums.py` asks the map's code where the drums are, cuts exactly their faces from the checked-in
  `riverside_pad`, `_store` and `_dressing` OBJs (2,272 triangles), and adds the group to the scene.
- The OBJs only lost lines and the scene only gained them. The hull OBJs and the fires are untouched.
- To roll back: `git restore` those three OBJs, the scene, `Tools/riverside_parts.py` and `Tools/riverside_map.py`.
- `old_drum.py` cuts the before from `riverside_pad.obj`, so it now needs that file from before the install. Its result is kept in the
  work folder.
- `riverside_map.py --preview` and the map art no longer show drums, since the models aren't in its zone meshes.

## Files

- `Assets/models/zombies/burn_drum_v2/`, `Assets/materials/zombies/burn_drum_v2/`: the models and maps.
- `drum.py` builds, bakes and exports, with `drum_pack.py`. `paint_drum.py` paints. `old_drum.py` cuts the old drum out of
  `riverside_pad.obj`, reading only. `render_drum.py` and `make_sheets.py` make the comparison. `verify_drum.py` checks the files.
- Work files and renders: `output/asset-improvement-20261030/burn-drum/`.

## Checked and not checked

Checked, from the files (`verify_drum.py`):

- `check_outward.py` on LOD 0: 16 solid pieces, 0 inside out.
- Radius, height and ground contact of every LOD against the old drum, within 0.1 in.
- Every texture the vmats name exists, every file the vmdls name exists, the vmdls have no physics, and the cold one has no glow.
- On Riverside: 14 drums placed, all with existing models, the old drum faces gone, 12 drum fires still there, and the hulls unchanged.

Checked by eye, in Blender renders with backfaces made transparent as the engine culls them: the stencil reads the right way round,
and LOD 1 and 2 hold up from across the park.

In s&box 26.10.27c, in an isolated editor scene built from `riverside.scene`'s own moon, sky, fog, lights, fires and post-processing
(`Sources/Zombies/cooler-v2/capture_engine.cs.txt`, exposure held at 3.5):

- It holds up beside `MapFire`'s real flames, and the air holes glow. That capture showed one fault Blender hadn't, fixed since: the fire's light reached the
  drum's bare floor, which read as a pale patch through the holes, so the floor now burns like the walls.
- Collision, by rays against the compiled map (`collision_check.cs.txt` in the same folder): the top at z 130.5 and the side 11 in out, both metal.

The sheets sent to the user are Blender (Cycles, ACES 1.3) renders. Their night sheet's light and exposure are my estimate of the map's look.

**Not checked:**

- **A live match**, so real auto-exposure and a player walking up to one are unseen. The capture holds exposure at 3.5 rather than letting it settle.
- The inside from above with the flames going: they cover the embers and logs from most views, and were only checked close up in Blender.
- Whether the LOD thresholds (0, 20, 60, copied from the town house doors) switch at sensible distances.
- The old renders use the vmat's tints as sRGB, as `riverside_materials.py` writes them. If the engine reads them another way, the old
  drum's real colour differs a little from the sheet.

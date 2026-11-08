# Reef Hall office chair v2 (standalone model, not placed in the map)

`models/maps/reefhall/office-chair-v2/office_chair.vmdl`, 13,664 triangles, origin on the floor under the gas lift,
facing +X. v1 (`office-chair-v1`) is kept unchanged. The user asked for the chair improved, not placed (2026-11-07).

What changed from v1 (its native capture: `output/reefhall/office-chair-v1/runtime-review/chair-after.png`):
- One curved spine from the tilt unit carries the back through a bolted plate (v1's two thin rods floated).
- S-curved back (lumbar forward, sides wrapping) with welt piping and a lumbar seam; crowned seat with a waterfall front.
- T-arms: forged bracket, tapered upright, soft pad with a height button.
- Tilt unit with tension knob and paddles, ribbed lift shroud, tapered polished alloy spokes, hooded twin casters.
- Materials reused from the approved Collider chair (`materials/collider/chair-realism-v2`: cloth, welt, polymer,
  alloy, rubber, steel) at their own tile sizes.

`python Sources/ReefHall/office-chair-v2/build.py` writes the model. `preview.py` makes offscreen Blender previews
(`output/reefhall/office-chair-v2/`), not game captures. Not yet compiled or seen in s&box: the editor was closed.

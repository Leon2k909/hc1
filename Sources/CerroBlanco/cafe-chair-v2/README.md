# Cerro Blanco's cafe chair v2

**Installed 2026-11-03** at the user's word ("looks good", to the install question), after a before and after in s&box: see `docs/notes/189`. Built after the user said of the courtyard parasols "ye good install it and do something else". Nothing is committed.

The old chair (`cerroblanco_parts.cafe_chair`, 20 in all: three at each of the cafe's four tables, two at each courtyard table, from `cerroblanco_map`) was a 16 x 16 teak slab on four square steel bars, with two more bars leaning back to 33 and a board across them. Its collision is one 14 x 14 x 18 box in the dressing model, which stays.

The new one stands in the same place, faces the same way and has its seat at the same height:
- A steel bistro chair with five teak slats screwed to a flat-bar apron. The rear slat fits between the posts.
- Front legs splayed a little. The rear legs sweep up into raked back posts carrying two curved teak back slats.
- Side stretchers, nylon glides and domed post caps.
- Anthracite powder coat, matching the parasols.

- About 6.4k / 2.5k / 1.6k triangles, with LOD thresholds 30 and 80. One material and one 2048 atlas at about 48 px/in.
- The teak is the forestbase `wood_planks` scan (CC0) at about 40 px/in, laid along each slat from inside one plank so the grain runs its length.
  - Each slat takes a run clear of the scan's butt joints and its tile seam (`JOINTS`).
  - The colour is shifted from the scan's oak brown to oiled teak.
- `chair.py` builds, bakes and exports. `paint_chair.py` paints. `make.ps1` runs them at idle priority (`-Preview` renders the bare build with `preview.py`).
- `chairs.py` lists the 20 places as the map puts them. `cut_compare.py` writes `Assets/models/maps/cerroblanco/cafe_chair_v2/compare/`: a copy of the dressing model without the old chairs (72 faces each, 1,440 in all), for the comparison only.
- `capture_engine.cs.txt` renders before and after in an isolated editor scene with the player camera's look. `sheet.py` makes `output/asset-improvement-20261030/cerroblanco-cafe-chair/chair-before-after-in-sbox.png`.

`install_chairs.py` did the install: it cut the old faces (72 a chair, 1,440 in all) from `quality-v1/cerroblanco_dressing_v2.obj` and added the scene's "Cafe Chairs" group, from `Tools/cerroblanco_chairs.py`. `cerroblanco_parts.cafe_chair` keeps the old collision box. `capture_installed.cs.txt` checks the scene as it stands. The `compare/` copy was for the comparison and is deleted.

To go back, restore `cerroblanco_dressing_v2.obj`, `cerroblanco.scene`, `cerroblanco_parts.py` and `cerroblanco_map.py` from git. Other sessions' Cerro Blanco changes were uncommitted in them on the day, so check the diff first.

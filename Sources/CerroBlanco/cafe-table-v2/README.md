# Cerro Blanco's cafe table v2

**Installed 2026-11-03** at the user's word ("good yeah install"), after a before and after in s&box: see `docs/notes/190`. Built after the user said of the cafe chairs "looks good do another". Nothing is committed.

The old table (`cerroblanco_parts.cafe_table`, eight in all: four in the cafe, four under the courtyard parasols, from `cerroblanco_map`) was a 20-sided white disc 1 in thick on a six-sided bar and a 12-sided disc. Its collision is one box in the dressing model, which stays.

The new one is a bistro table with its top's surface at 29.5, where the fit-out's cups stand:
- A 28 in top of white compact laminate, 1/2 in thick, with its black core showing at the eased edge.
- A four-armed steel spider screwed up under the top.
- A column and a cast base on levelling glides, in anthracite powder coat to match the parasols and chairs.

Two models come from one build and one atlas:
- `table.vmdl` is the whole table, for the cafe.
- `table_top.vmdl` is only the top and spider, for the courtyard. There the parasol's socket tube and base stand under it: the spider's hub sits on the parasol's flange at 28.4, and the parasol's grommet sits on the top.

- About 3.5k / 1.8k / 1.0k triangles for the whole table and 1.6k / 0.7k / 0.4k for the top, with LOD thresholds 30 and 80. One 2048 atlas at about 45 px/in.
- The top's paint has faint broken cup rings, plate scratches, a little grey where forearms rest, and a satin black core edge knocked pale in places. The base is kicked bare at its rim and the column scuffed low by shoes.
- The face and edge are told apart by height, not by the baked normal. The normal is smoothed across the arris and drew notches along the edge.
- `table.py` builds, bakes and exports (written by `assemble.py` from the chair's shared stages). `paint_table.py` paints. `make.ps1` runs them at idle priority.
- `cut_compare.py` writes `Assets/models/maps/cerroblanco/cafe_table_v2/compare/`, a copy of the dressing model without the old tables, for the comparison only. It cuts 122 faces at each cafe table and 88 at each courtyard one.
- `capture_engine.cs.txt` renders before and after in an isolated editor scene with the player camera's look. `sheet.py` makes `output/asset-improvement-20261030/cerroblanco-cafe-table/table-before-after-in-sbox.png`.

`install_tables.py` did the install: it cut the old faces (840 in all) from `quality-v1/cerroblanco_dressing_v2.obj` and added the scene's "Cafe Tables" group, from `Tools/cerroblanco_tables.py`, which gives a table under a parasol the top-only model. `cerroblanco_parts.cafe_table` keeps the old collision box. `capture_installed.cs.txt` checks the scene as it stands. The `compare/` copy is deleted.

To go back, restore `cerroblanco_dressing_v2.obj`, `cerroblanco.scene`, `cerroblanco_parts.py` and `cerroblanco_map.py` from git. Other sessions' Cerro Blanco changes were uncommitted in them on the day, so check the diff first.

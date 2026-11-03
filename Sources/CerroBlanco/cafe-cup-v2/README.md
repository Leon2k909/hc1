# Cerro Blanco's cafe cup and saucer v2

**Installed 2026-11-03** at the user's word ("ye install them"), after a before and after in s&box: see `docs/notes/191`. Built after the user said of the cafe tables "good yeah install and do another". Nothing is committed.

The old cup (`cerroblanco_fitout`, "Cups and saucers on the tables") stood two to a table on all eight cafe tables, 6 in from the middle at 70 and 230 degrees. Each was:
- a grey 12-sided `cbf_plastic` disc for a saucer, from 29.5 to 29.8;
- an open ten-sided cone for a cup, which vanished from above, because the engine draws only its outside.

They're in `cerroblanco_fitout_fine.obj` ("Fit-out Detail"), 84 faces each.

The new one is white porcelain with bare bisque foot rings:
- **Saucer:** a 5.6 in saucer with a well and a rolled rim.
- **Cup:** a cappuccino cup with a thick base, a rounded lip and a strap handle.
- **Two models from one build and one atlas:**
  - `cup.vmdl`: full, with a milk foam heart on crema. It goes at 70 degrees round each table.
  - `cup_empty.vmdl`: drunk, with a teaspoon on the saucer, a dried foam line inside and dregs. It goes at 230.
- **Stains:** a coffee ring and drips on the saucer, and a smear and a drip at the side it's drunk from.

- About 4.7k / 2.8k / 2.0k triangles each, with LOD thresholds 10 and 30. One 1024 atlas at about 77 px/in.
- **Ambient occlusion:** the bake's occlusion reaches 3 in, the whole cup, so the paint keeps only the near half of it. At full strength the cup's inside drew black.
- **No kiln specks:** at this size any made by noise read as grey flecks over the whole glaze.
- **The heart:** found from the heart curve's value over its slope, so its edge is the true line and not a lumpy blob.
- **Files:**
  - `cup.py` builds, bakes and exports. It's written by `assemble.py` from the table's shared stages, including the two-model export.
  - `paint_cup.py` paints, and `make.ps1` runs them at idle priority.
  - `cups.py` lists the 16 places as the fit-out puts them.
  - `cut_compare.py` writes `Assets/models/maps/cerroblanco/cafe_cup_v2/compare/`, a copy of the fit-out detail model without the old cups, for the comparison only.
  - `capture_engine.cs.txt` renders before and after in an isolated editor scene with the player camera's look, and `sheet.py` makes `output/asset-improvement-20261030/cerroblanco-cafe-cup/cup-before-after-in-sbox.png`.

`install_cups.py` did the install: it cut the old faces (84 a cup, 1,344 in all) from `cerroblanco_fitout_fine.obj` and added the scene's "Cafe Cups" group, from `Tools/cerroblanco_cups.py`, which places the cups from the recorded tables. The fit-out no longer draws them. `capture_installed.cs.txt` checks the scene as it stands. The `compare/` copy is deleted.

To go back, restore `cerroblanco_fitout_fine.obj`, `cerroblanco.scene`, `cerroblanco_fitout.py` and `cerroblanco_map.py` from git. Other sessions' Cerro Blanco changes were uncommitted in them on the day, so check the diff first.

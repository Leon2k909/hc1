# Cerro Blanco's courtyard parasol v2

**Installed 2026-11-03** at the user's word ("ye good install it"), after a before and after in s&box: see `docs/notes/188`. Built after the user asked for "an asset that needs improvement, do it and show me a before and after". Nothing is committed.

The old parasol (`cerroblanco_parts.parasol`, four over the courtyard's cafe tables in `cerroblanco_map.courtyard`) was four flat white triangles from rib tips at 84 in to a peak at 100, a six-sided bar for a pole and an 18 x 18 x 3 black box at its foot. It had no collision.

The new one covers the same 88 in square:
- An ecru acrylic canopy in eight gores. It sags a little between the ribs and pulls in along the hem.
- A piped hem, a valance down each side with a bound foot, and a wind vent on its own spindle and finial.
- Under the canopy, eight anthracite ribs pivot in a turned hub. Stretchers hold them up from a runner, which a cord pulls up the pole. The cord comes out of a grommet onto a cleat, with its tail coiled on the top horn.
- The pole drops through a steel grommet in the table into a socket tube. The tube stands in a 21 in cast base under the table and is clamped by a T-knob. The old table's centre post and base disc sit inside the tube and base.
- A tie strap hangs from one gore.
- There is no lettering except "25 KG" cast in the base.

- About 24.3k / 13.6k / 5.1k triangles, with LOD thresholds 40 and 110.
- One material and one 2048 x 4096 atlas: about 17 px/in on the canopy's underside, 10 on its top and 18 on the frame.
- The canopy's top and underside are each one sheet laid flat from above, so they pack as squares. The islands are nested by Blender's packer inside the whole atlas.
- `parasol.py` builds, bakes and exports. `paint_parasol.py` paints. `make.ps1` runs them at idle priority (`-Preview` builds and renders the bare mesh with `preview.py`).
- `cut_compare.py` writes `Assets/models/maps/cerroblanco/parasol_v2/compare/`, a copy of the dressing model without the four old parasols, for the comparison only.
- `capture_engine.cs.txt` renders before and after in an isolated editor scene with the player camera's look. `capture_before.cs.txt` was the first look at the old one. `sheet.py` makes `output/asset-improvement-20261030/cerroblanco-parasol/parasol-before-after-in-sbox.png`.
- `check_outward.py` flags ten pieces. They are the canopy, valance and vent sheets: open cloth, so a signed volume means nothing for them. In the engine every sheet faces the way it should.
- The canopy's top goes blue-grey in the courtyard's shade, as the old white one does. It's the skylight, not the paint.

`install_parasols.py` did the install: it cut the old faces (264, 66 a table, as `cut_compare.py` picks them) from `quality-v1/cerroblanco_dressing_v2.obj` and added the scene's "Parasols" group, from `Tools/cerroblanco_parasols.py`. `capture_installed.cs.txt` checks the scene as it stands. `cut_compare.py`'s `compare/` copy was for the comparison and is deleted. No collision was added: the old parasol had none.

To go back, restore `cerroblanco_dressing_v2.obj`, `cerroblanco.scene`, `cerroblanco_parts.py` and `cerroblanco_map.py` from git. Other sessions' Cerro Blanco changes were uncommitted in the scene and the map tool on the day, so check the diff first.

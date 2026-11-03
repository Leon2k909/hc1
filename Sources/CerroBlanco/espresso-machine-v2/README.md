# Cerro Blanco's cafe espresso machine v2

**Installed 2026-11-03** at the user's word ("Install it"), facing the barista, after a before and after in s&box: see `docs/notes/192`. Built after the user said of the cafe cups "ye install them and do something else". Nothing is committed.

The old machine (`cerroblanco_fitout.cafe`, on the cafe counter at plan ( 575, 615 ), the counter's top at 42) was:
- a steel box 26 x 18 x 17 with a dark lid;
- two chrome stubs with black sticks for group heads, on its south (customers') face;
- four open cones for cups on top.

It's 318 faces in `cerroblanco_fitout_fine.obj` ("Fit-out Detail"), drawn only, with no collision.

The new one is a two-group commercial machine about 28 x 21 x 21 in:
- Brushed stainless side panels with rounded tops, on chrome feet over a black base pan.
- Under the head, two chrome group heads with portafilters locked in: double spouts, black handles worn glossy at the grip.
- Steam wands on ball joints with cool-touch sleeves and levers above, and a hot water spout.
- Two pressure gauges with drawn dials: pump 0 to 16 bar at 9, boiler 0 to 2.5 with a red band, at 1.2. A keypad with green lights over each group.
- A drip tray with a slotted grate, grounds and limescale on it.
- A railed cup warmer with espresso and cappuccino cups upside down on it.
- The water and drain hoses into the counter at the back.
- No maker's names.

**Its working front faces north, toward the barista behind the counter, as real cafes set them; the customers see its stainless back.** The old box had its stubs toward the customers. A half turn would put the work area on that side instead.

- About 15.9k / 9.4k / 1.8k triangles, with LOD thresholds 20 and 60. One 2048 atlas at about 26 px/in on the stainless and about 83 on the gauge faces.
- Half the boxes' area is hidden (behind the side panels, under the warmer, under the body) and gets next to no texture.
- The gauge bezels are swept rings. The toolkit's lathe caps its ends, and a turned bezel put a chrome disc over each dial.
- The dials are matte: as a gloss they mirrored the windows and washed their print out.
- `machine.py` builds, bakes and exports. It's written by `assemble.py` from the chair's shared stages.
- `paint_machine.py` paints, and `make.ps1` runs them at idle priority.
- `cut_compare.py` writes `Assets/models/maps/cerroblanco/espresso_machine_v2/compare/`, a copy of the fit-out detail model without the old machine, for the comparison only.
- `capture_engine.cs.txt` renders before and after in an isolated editor scene with the player camera's look. `sheet.py` makes `output/asset-improvement-20261030/cerroblanco-espresso/machine-before-after-in-sbox.png`.

`install_machine.py` did the install: it cut the old machine's 318 faces from `cerroblanco_fitout_fine.obj` and added the scene's "Espresso Machine" object, from `Tools/cerroblanco_espresso.py`. The fit-out no longer draws the old one. `capture_installed.cs.txt` checks the scene as it stands; it warms up its first view, as a cold first frame came out green-cast with blank dials. The `compare/` copy is deleted.

To go back, restore `cerroblanco_fitout_fine.obj`, `cerroblanco.scene`, `cerroblanco_fitout.py` and `cerroblanco_map.py` from git. Other sessions' Cerro Blanco changes were uncommitted in them on the day, so check the diff first.

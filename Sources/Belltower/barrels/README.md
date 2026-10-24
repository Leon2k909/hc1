# Clock-building barrel pairs

The two casks beside each clock-building ground-floor doorway are stored beneath
the adjoining wide window. The doors and their approaches are clear. Both pairs
retain their original 26-inch diameter and 36-inch height; their existing wood
collision hulls move with them.

`placement-v2.json` records the measured old centres and the new centres in plan
inches. `Tools/belltower_map.py::barrel` resolves only those two west-side centres;
the normal map mirror provides the east pair. All other barrels retain their
existing authoring behaviour and random-number sequence.

`Tools/belltower_barrels_v2.py` builds separate tapered staves, recessed board
lids, small bungs, worn rim ends and beveled fitted iron hoops. It reuses existing
photographed wood and iron materials. The bounded live models import one small
private mesh per side at `models/maps/belltower/barrels-v2/`.

`installed-v2.json` records the installed files and native validation evidence:
both models compiled, ten physics rays passed, and all three camera captures
restored the editor state. Other geometry and collision bytes were preserved by
the scoped staging process. The source scene required no changes for this repair.

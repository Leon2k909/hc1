# Reef Hall equipment racks preview

The control room's north-wall bank contains 13 plain cabinets with six luminous
strips each. This preview replaces their render geometry with rolled cabinet
edges, recessed rack rails, six removable equipment chassis, open grille slots,
drive caddies, pull handles, fasteners and small status indicators. The existing
cool/warm indicator pattern and six vertical levels are retained.

The cabinets stay inside their original plan envelope `e1960..2300`, `n870..900`,
`z0..84`. Four small cantilever service lamps attach to the cabinet tops,
extending forward to `n841` and upward to `z110`. The private assembly has 81,872
triangles. Four unshadowed point lights under those actual fixtures illuminate
the previously unlit equipment fronts. They are part of the proposed installed
asset, enabled only for the after variant. It adds no collision.
The original public model, scene, lighting and generator
are unchanged; this is a proposal awaiting visual approval.

`build.py` matches all 286 old rack triangles by exact material and rounded saved
vertex positions. It creates a private control-room mesh without those faces,
retaining every vertex/normal/UV record and the complete original physics
section. No bounding-box deletion is used.

Commands from the canonical checkout:

```powershell
rtk python Sources/ReefHall/server-rack-v1/build.py
rtk python Sources/ReefHall/server-rack-v1/setup.py
rtk python Sources/ReefHall/server-rack-v1/review.py
rtk python Sources/ReefHall/server-rack-v1/verify.py
```

Native editor import and asset compilation precede an actual offline play-mode
check. Matched before/after views copy the player's post effects and use the same
camera and exposure, with 180 normal streaming frames per view and no
forced texture residency. The runner restores the editor's previous scene and
stopped state. If another user switches scenes during capture, it aborts and
leaves that new session untouched. Ambient map lighting is unchanged; the after
variant includes the rack-mounted service lamps. Their native-world positions
are `(844,-e,104.5)` for `e=2000,2085,2170,2255`, radius 180, shadows off,
linear RGB `(0.85,0.93,1)*4`. Installation must retain these four lights to match
the reviewed result.

Outputs: `output/reefhall/server-rack-v1/`, including comparison PNGs, the source
hash guard, manifest and `validation.json`. No frame-time benchmark is claimed.

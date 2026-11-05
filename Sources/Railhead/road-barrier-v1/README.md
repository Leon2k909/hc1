# Railhead roadworks barrier — installed 2026-11-04

The east goods yard's barrier at plan `(1905,-1556,0)` was six alternating colour
blocks on two square posts and rectangular yellow feet. This isolated proposal
rebuilds it with a continuous rounded board, diagonal red-and-white panels on
both faces, rounded weighted feet, dark grip recesses and rubber ground pads,
post sockets and thumb screws, steel supports, saddle clamps and rear stays.

The candidate has 5,608 triangles and five private materials. It keeps the
original 39.4-inch board length and height, and the original support positions.
The board sits 1.4 inches in front of the post centres, carried by wraparound
saddle clamps, so the posts do not obscure the striped panel.
It adds no lights or collision. After user approval, the public east dressing
model imports the trimmed base and approved barrier mesh alongside its existing
extinguisher import. The scene and other roadworks props are unchanged.

`Tools/railhead_road_barrier.py` reproduces the approved mesh exactly.
`Tools/railhead_map.py` uses it only for the selected east-yard placement; the
west barrier retains its original helper. `prepare_install.py` stages this
integration and refuses already-installed or changed source assets.

The actual public east dressing model imports `extinguisher-v2/east-base.obj`
plus the approved extinguisher geometry. The private preview removes only the
barrier's exact 120 legacy triangles from that current base, preserving all
vertex/UV/normal records, unrelated faces, remaps, other imports and the complete
physics section. It does not rebuild the shared map.

Original preview workflow (retained for provenance; not an installation command):

```powershell
rtk python Sources/Railhead/road-barrier-v1/build.py
rtk python Sources/Railhead/road-barrier-v1/setup.py
rtk python Sources/Railhead/road-barrier-v1/review.py
rtk python Sources/Railhead/road-barrier-v1/verify.py
```

Private assets import and compile through the native editor. The matched front
view is captured during actual offline Railhead play, with a player
present, the player's post effects, identical camera/exposure/map lighting and
180 normal streaming frames per view. Texture residency is not forced. The
runner restores the previous editor scene and stopped state and aborts if
another user changes scenes during capture. Restoration is checked against its
immediate receipt, allowing later scene changes by another editor user. An
exploratory rear view was obscured by the existing brick pallet and is not used
in the published comparison.

Sources and receipts are in `output/railhead/road-barrier-v1/`, including the
source hash guard, manifest, comparison PNGs and `validation.json`. No frame-time
benchmark or material retroreflection simulation is claimed.

Installation receipts and the final public-model play check are recorded in
`output/railhead/road-barrier-v1/installed.json`, with the final screenshot in
`runtime-installed/barrier-installed.png`. The original public ModelDoc and
generator snapshot are retained in `install-before/`. The original complete
physics section is preserved byte-for-byte. Only the public east ModelDoc and
the generator hook are changed among previously existing protected files.

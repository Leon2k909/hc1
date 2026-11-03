# Riverside's lawn chairs v2: installed

Created and reworked 2026-11-03. Installed the same day after the user asked to install the new chairs. All four original placements now draw the replacement: three green chairs and the red porch chair.

The old chair is `riverside_parts.lawn_chair`: two flat cards (seat and back) on thin rods. It has no collision. There are four of them, merged into the map's models:

- `riverside_dressing.obj`: the yard's green one at engine (1060, 420, 0), facing plan (0.7, 0.7).
- `riverside_terrace.obj`: a porch's pair, one green (`rs_lawn_chair`) and one red (`rs_drum_red`, the same paint as the red drums, so cut it by position).
- `riverside_levee.obj`: a green one up on a trailer's roof, someone's lookout.

The new one is a folding aluminium chair, built and painted by `lawn_chair.py` with numpy and PIL:

- A front U and a rear U of 1 in tube, splayed into an A side on, on floor bars with black plastic glides. The seat frame and back frame sit inside them. Off-white plastic armrests are rounded over the front legs and bevelled, with bolts, washers and rivets.
- Woven webbing: 14 straps on the seat and 14 on the back, each a real 0.025 in thick so its two sides never fight. They go over and under one another, sag where people sat, and each wraps round its tubes and tucks under. One of the back's straps has snapped and its ends hang.
- The webbing is woven yarn: coloured warp yarns make the stripes, the weft makes fine ribs, each yarn a touch different. It's sun-bleached unevenly with yellowed white, grime in the weave and the edges, frayed edges, a little mildew and mud. The aluminium is dull and oxidised, scratched along its length, and caked with dried mud on its lowest stretches; there are four tube pictures chosen by height. Nothing copies a maker's pattern.
- Two colours from one mesh: `lawn_chair_green.vmdl` (the old chairs' green, with a yellow line) and `lawn_chair_red.vmdl` (red, white and navy, for the porch's red one). They share every map but colour.
- Triangles, LOD 0-2: 27,696 / 8,040 / 1,508, switching at 24 and 70. One 2048 x 1024 atlas, straps at 28 px/in.
- Engine X is the way it faces, Y its left. The origin is on the ground under the seat's middle, where the old chair's was.

`compare_chair.py` renders old and new in the real map, in an isolated editor scene. The old chair can't be hidden there, so the new pair stands 50 in to the yard chair's left.

## Installation

`install_chairs.py <project root> <session exchange directory> --apply` cut 68 old triangles per chair (272 total) from the three existing zone OBJs. Every retained line is unchanged; collision files were untouched. Backups are in `output/asset-improvement-20261030/lawn-chair/before-install/`. The script also writes placement data and the editor scripts into the exchange directory. Run `install-chairs.cs` with native `run_csharp` to create/validate the objects in an isolated editor scene and save the SceneFile through `Editor.Asset.SaveToDisk`. This preserves the active scene and play session; it refuses installation if Riverside is open elsewhere.

`riverside_parts.lawn_chair` now records placements. `P.carry` transforms them out of the trailers' local frames, and `riverside_map.lawn_chair_objects` emits the `Lawn Chairs` scene group. Future generator runs retain the replacements. Do not regenerate the whole map for this installation; its shared kit has changed.

Verified all four installed chairs in isolated engine renders using `check-chairs.cs`, generated from `check-installed.cs.txt`. Screenshots are `installed-porch-green.png`, `installed-porch-red.png`, `installed-roof.png` and `installed-yard.png` in `output/asset-improvement-20261030/lawn-chair/`. All four models loaded without errors and have no colliders, matching the old chairs. `verify_install.py` checks that only the intended old face lines were removed and existing scene content is unchanged apart from the engine's component-version metadata and equivalent realtime probe mode added on save.

Not seen in a live match.

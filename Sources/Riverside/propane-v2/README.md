# Riverside's propane cylinders v2

Created 2026-11-03. **Installed 2026-11-03**, all six, at the user's word, by `install_propane.py`. See `docs/notes/194`.

The old ones were `riverside_parts.propane` (a 100 lb cylinder: a plain tube with a cone and a black cap) and the "propane pair" in `riverside_parts.rv` (two plain 12 x 18 in tubes on the camper's tongue). All were merged into the map's models:

- `riverside_pad.obj`: the row of three at engine (-560, 380 / 362 / 344, 96), and the camper's pair at (-130, -255 / -237, 114).
- `riverside_terrace.obj`: one on a trailer's porch at about (72, 535, 124).

The new ones are two models, built and painted by `propane.py` with numpy and PIL:

- `propane_100`: a 14.5 in steel shell with elliptical heads, a weld seam and a foot ring. It has a collar with two handholds round a brass valve with a red handwheel, a yellow relief-valve cap and a gauge screw. Triangles, LOD 0-2: 6,168 / 2,776 / 1,008, switching at 30 and 90. One 2048 atlas at 29 px/in.
- `propane_20`: the same build at grill-bottle size, 12.2 x 19.9 in. Triangles 5,528 / 2,424 / 1,008, switching at 24 and 70. One 1024 atlas.
- Worn off-white paint. Rust runs from under the collar and the seam, rust creeps up from the foot, and there's mud splash, chips, rub scuffs and a weathered film. There's a warning label with a class 2 diamond, and a red "PROPANE / 100 LB" stencil on the big one. The collar has stamped marks. Everything printed is made up. The mottle and the rust's colour come from `forestbase/scans/metal_plate_02`, with its plate seams filtered out.
- The origin is the middle of the foot. The valve's outlet points along +X, through a handhold.

`compare_propane.py <root> [old|new] [row|pair]` renders old and new in the real map, in an isolated editor scene. The old ones can't be hidden there, so the new row stands 80 in along from the old one. The new pair stands on the pad's ground, as the camper's tongue still has the old pair on it.

## The install

`install_propane.py` runs riverside_map's own trailers and pad code, without writing anything, to get the six placements. It cut the old `rs_propane` and `rs_steel` faces at each one from the live `riverside_pad.obj` and `riverside_terrace.obj`: 102 for a 100 lb spot, 28 for a 20 lb spot. The 100 lb ones' old collision hulls stay. It added a top-level "Propane Cylinders" group after "Teddy". `riverside_parts.propane` now only records a cylinder, and `P.carry` (called by `place_into`) brings those drawn in a trailer or the camper into the zone's frame, so a rerun of the map keeps them. Backups are in `output/asset-improvement-20261030/propane/before-install/`.

`check_installed.py` waits for the zones to recompile and renders the row and the pair as the scene stands (`installed_*.png`). The porch one wasn't looked at.

Not seen in a live match.

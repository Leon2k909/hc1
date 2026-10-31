# Railhead pallet truck v2

Created 2026-10-31. **Installed on the user's word the same day**, after seeing both side by side in s&box. See `docs/notes/173-pallet-truck-v2-models-props-railhead-pallet-truck-v2-sources-railhead-pallet-truck-v2.md`.

The hand pallet truck left in Railhead's goods yard, placed once on each side. The old one (`pallet_jack` in `Tools/railhead_furniture.py`) is two red boxes for forks, a tube for a pump and a thin red stick with a black bar on it. I picked it from
shots in s&box: it was the crudest thing left that I looked at on Railhead. This keeps its size and bold red and builds the real thing: pressed channel forks open underneath, with load rollers and pins in their tips, a welded frame with gussets, a pump with a chrome ram
and a clevis, two rubber steering wheels in a yoke, and a tiller with a looped handle, a ribbed grip, a release lever and its rod. Its paint is worn where pallets drag along the forks and on its real edges. A printed "MAX 2500 kg" label on each fork is its only lettering. No brands.

- Triangles: 6,788 / 3,786 / 2,038 / 902 (LOD 0-3). One material, one 2048 atlas, about 21 px/in, half full.
- `pallet_truck.py` builds, bakes and exports. `paint_truck.py` paints. `capture_config.py` shoots old and new side by side in s&box, with `Sources/CerroBlanco/boulder-v2/capture_engine.cs.txt`. `finish.ps1 -Build` runs the build at idle priority and stops at the first step that fails.
- The bake has an edge mask from the Cycles Bevel node: how far its normal turns from the true one. It finds real edges on any mesh, so the paint can wear them without knowing the shape.
- Work files and shots are in `output/asset-improvement-20261030/pallet-truck/`: `pass2/` is the comparison, and `draft1/` is the first pass, with the truck stood in some pallets by mistake.

## Checked

- `check_outward.py`: 0 of 57 solid pieces inside out on LOD 0. Bounds about the old ones: within 0.3 on its sides and short of the old height.
- Compiled by the editor with no errors reported, and seen in s&box beside the old truck in the goods yard, in a hidden copy of the map's real scene with its sun, sky, fog and post effects. Exposure was held at one value so both match.
- After the install, in the same hidden copy, each side's truck stands alone with no old one left inside it.

## Not checked

- Not seen in a match, or with the player camera's finish.
- LODs 1-3 haven't been seen in s&box. `switch_threshold`s (30, 90, 220) are estimates.

## How it was installed

`install_trucks.py` cut both old trucks, 302 triangles each, from `extinguisher-v2/east-base.obj` and `west-base.obj` (what the dress models build from) and from the generator's OBJs, and added the scene's "Pallet Trucks" group. `railhead_props.pallet_jack` now keeps only the collision box and records a placement, so a full map run makes the same group, which hasn't been tested. `check_config.py` makes the check's shots.

## Known weaknesses

- Its forks are dark in shade, though so are the old truck's.
- Up close, the scrapes on the forks are soft at this density.
- Its collision box, the old one's, stops at the pump, so bullets and players pass through the tiller.

## Sewage power cabinet v2 (`power_cabinet_v2`, Sewage's three cabinets, 2026-10-31)
- `models/maps/sewage/power_cabinet_v2/power_cabinet.vmdl` replaced the flat box with eight bars at the user's word ("Yes, install it") after an in-engine
  before and after. Sources, install steps and tools are in `Sources/Sewage/power_cabinet_v2/`.
- Three objects in `sewage.scene`, `Power cabinet 1-3`, at world (470, 958, 0), (600, -946, 0) and (830, 870, 352), facing the walkways.
- The old faces and lamps are cut from `sewage_details.obj`, and `Tools/sewage_map.py` no longer draws them. The bodies still collide through the old
  hulls in `sewage_details.vmdl`. The new model's only collision is a box round its conduits, so it has a `ModelCollider` too.
- Work lights 37-39, the cabinets' green lights, moved to the new status lamps (model-space 24, -24, 104.5). From the old spot, behind the doors'
  plane, they couldn't light the doors. Moving them is why the doors now read in the dark.
- Colour and normal are 4096 and the rest 2048. They're painted at 3072, but the engine can't filter a normal map that isn't a power of two.
- Checked in an isolated editor scene from the real scene file: no error models, rays stop at the doors and conduits where expected, and all three spots
  looked at, including the catwalk's stair head, where the third cabinet leaves about 46 in. Not seen in a live match.
- Still weak: the plain rubble boxes round the first two cabinets.
- 2026-11-04 instrument detail pass accepted: folded rain hood with drip lip and side cheeks, raised meter pointers, numbered A/V scales and a static voltage
  indication of about 440 V. Counts 21,982 / 11,022 / 5,324 / 1,882. One material, existing atlas sizes, ModelDoc/material resource and collision are retained.
  Current build inputs and native before/after captures: `output/cabinet-instruments-20261104/`. `verify_detail.py` checks exported LODs, closed-shell winding,
  bounds, UVs, texture sizes and the three installed placements. This pass has not been checked in live gameplay or benchmarked.
- Native full model/material compilation passed. Actual-scene isolation check found all three cabinets, zero error models and nine matching door/conduit/clearance rays.
  Two map-lighting captures and the validation receipt are in `output/cabinet-instruments-20261104/map-check/`. The user's active scene and play state were preserved.
- The improved model was retained after acceptance; superseded original build files and the before/comparison files were deleted. The user wants future model work to be
  substantial rebuilds of crude assets rather than small detail passes on already detailed models.

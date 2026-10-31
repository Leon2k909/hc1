# Jersey barrier v2

Created 2026-10-30, as a trial. **Rejected by the user the same day**, after seeing both side by side in s&box: its chipped patches look pixelated, and that's how they're painted, not an engine fault. Riverdale and Spillway still build the old barrier, and no map file changed. Its assets moved out of `Assets` to `output/asset-improvement-20261030/jersey-barrier/retired-jersey_barrier_v2/`, and these scripts remake them.

The concrete barrier those two maps use as cover, which players press right up against. The old one (`jersey` in `Tools/riverdale_parts.py`,
430 triangles) is a clean F-shaped loft in a concrete that tiles every 64 inches. This keeps its section exactly, because the map's collision
hull comes from it, and adds what a barrier left out in the rain has: rain streaks, moss at the foot, tyre scuffs, form seams, bug holes,
chipped arrises, a knocked corner with rebar, faded hazard stripes, rusty connecting loops in each end, and invented stencilling ("RHP 07",
"KEEP 3M CLEAR", for the plant). No brands.

- Triangles: 6,561 / 3,035 / 964 / 288 (LOD 0-3), against the old 430 with no LODs. One material, one 2048 atlas, about 17 px/in.
- That sharpness is about level with the old concrete's 16 px/in. The gain is that nothing repeats and the wear is worked out for the shape.
- `jersey.py` builds, bakes and exports. `paint_jersey.py` paints. `render_jersey.py` renders. `verify_jersey.py` checks. `read_old.py` makes the
  old barrier from the map's own code, for the "before". `finish.ps1 -Old -Build` runs it all at idle priority and stops at the first step that fails.
- Work files and sheets are in `output/asset-improvement-20261030/jersey-barrier/final/`.

## Checked

From the files, by `verify_jersey.py`: 0 of 11 solid pieces inside out on LOD 0, bounds within 0.1 of the old (0.15 for far LODs, which a collapse
moves slightly), nothing more than 0.2 outside the collision hull, normals, UVs in range, every texture and mesh named exists, and no map asks for it.
I looked at Blender renders of LODs 1-3 from one angle: no holes.

## Not checked

- **Never compiled or seen in s&box.** The sheets are Blender Cycles renders, which flatter any asset, in my approximation of the maps' overcast light.
- `switch_threshold`s (30, 90, 220) are estimates.

## To install it

It isn't one path to change. The old barrier is merged into the maps' generated meshes, so:

- `jersey` in `Tools/riverdale_parts.py` should keep its collision hull and stop drawing, and each barrier become a placed copy of this model.
- That means regenerating Riverdale's and Spillway's meshes and scenes, which needs the editor to compile them.
- Riverdale's barriers are the 118 this was built at. Spillway's four are 160 and 180 long: stretching this one 35-50% would smear it, so either those
  become two barriers end to end, which real ones would be, or get a longer build.

## Known weaknesses

- The chipped patches look a little alike, and paler than I'd like.
- The broken corner reads as heavy wear rather than a clean break.
- A small jag at the bottom of one scupper shows at some angles, from the boolean cut through the chipped surface.

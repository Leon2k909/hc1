# Railing post fittings v1

Created 2026-10-31, at the user's "pls fix" over a screenshot of a post on Riverdale's fuel pool rail.

## The fault

`riverdale_parts._post` put a six-sided sleeve near the top of each post, with no top. Back faces aren't drawn, so from above its open end read as a torn edge, with the room showing through it and the bare post standing inside. It stopped just under the rail, so nothing joined them.

## The fix

`riverdale_parts._rail_fitting` draws a cast T-fitting: an eight-sided capped socket on the post, and a closed collar 3.8 in long round the rail. Where the rail turns a corner it misses the post, so there's a capped socket and no collar. Each post is about 100 triangles, where the old fitting was 24.

`fix_fittings.py` swapped the fitting in the live OBJs, because rerunning a map's script rewrites far more than this. It finds each post from its old sleeve, takes the rail's direction from the long sides of the tube over it, removes those 24 triangles and adds the new ones.

| Model | Posts | Added triangles |
| --- | --- | --- |
| `riverdale_hall` | 229 | 17,046 |
| `riverdale_hall_detail` | 25 | 1,950 |
| `riverdale_hall_dress` | 16 | 1,248 |
| `riverdale_pool` | 8 | 368 |
| `riverdale_middle` | 60 | 4,296 |
| `riverdale_east` | 74 | 5,260 |
| `riverdale_west` | 74 | 5,260 |
| `spillway_control` | 82 | 6,396 |
| `spillway_cargo` | 26 | 1,748 |
| `spillway_east` | 110 | 7,740 |
| `spillway_west` | 109 | 7,942 |
| `spillway_ground` | 391 | 30,058 |
| `orion_fuel` | 114 | 8,484 |
| `orion_launch_control` | 115 | 8,778 |
| `orion_launch_deck` | 99 | 7,594 |
| `orion_overlook` | 34 | 2,524 |
| `orion_pad` | 162 | 9,564 |
| `orion_vista` | 24 | 1,104 |

That's 1,752 posts: 486 on Riverdale, 718 on Spillway and 548 on Orion, for about 35,000, 54,000 and 38,000 more triangles. Run the tool until it says "nothing to do". Sleeves a few inches apart group wrongly until a neighbour has gone, two can stand in one place where rails meet, and a pair about two inches apart needs its corners sorted out, so one pass isn't enough.

Originals are in `output/asset-improvement-20261030/rail-fittings/retired/`. `capture.py` shoots the pool's rail from a small hidden scene. The shots are in `output/asset-improvement-20261030/rail-fittings/`.

## Left alone

- `riverdale_backdrop` has 378 posts that players never get near. A rerun of its script would fix them.

## Not checked

Seen in s&box on Riverdale's pool rail, a right-angled corner and Spillway's rails, in hidden scenes with the map's own light. Orion and the last few posts on Riverdale and Spillway were patched at the user's word while s&box was closed, so they draw the old fittings until they next compile, and Orion hasn't been looked at in the engine. Its texture scales were measured from the old fittings (48 in, and 64 in for `oa_dark`). None of it has been seen in a live match. Stair rails were only seen from a distance in the dark. Frame rate hasn't been measured.

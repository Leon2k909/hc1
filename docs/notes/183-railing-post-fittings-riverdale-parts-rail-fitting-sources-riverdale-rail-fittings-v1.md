## Railing post fittings (`riverdale_parts._rail_fitting`, 2026-10-31)
- The kit's post had an open six-sided sleeve under the top rail. Back faces aren't drawn, so its top read as a torn edge with the room showing through (the user's screenshot of Riverdale's fuel pool rail). `_rail_fitting` draws a capped socket and a closed collar round the rail, and just the capped socket where the rail turns a corner.
- `Sources/Riverdale/rail-fittings-v1/fix_fittings.py` swapped them in Riverdale's, Spillway's and Orion's live OBJs, 1,752 posts in 18 models, without rerunning a map's script. Rollback: `output/asset-improvement-20261030/rail-fittings/retired/`.
- `riverdale_backdrop` still has 378 that players never get near.
- Riverdale and Spillway were seen in s&box in hidden scenes with the map's light. Orion was patched with s&box closed and hasn't been seen there. None of it has been seen in a live match.

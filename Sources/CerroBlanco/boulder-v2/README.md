# Cerro Blanco boulders v2

Created 2026-10-31. **Installed on the user's word the same day**: all three shapes are in use, so four of the six spots have new stones and two keep the old shape. See `docs/notes/172-garden-boulders-v2-models-props-cerroblanco-boulder-v2-sources-cerroblanco-boulder-v2.md`.

The six boulders on the lawns round bomb site B, which are cover there. The old one (`boulder` in `Tools/cerroblanco_parts.py`) is the convex hull of 18 random points, shaded flat, standing on a point, in a tiled rock
that shows as blotches. I picked it from shots of candidates in s&box: it was the crudest thing I looked at on Railhead or Cerro Blanco. These are two sculpted stones sitting down into the lawn, at the old stones' sizes, with broken
faces, bedding ledges and real cracks baked from a high sculpt. Grey granite with warm feldspar and dark mica, soft lichen on top, rain stains, dirt in the cracks, damp and moss at the foot. No lettering.

- Two shapes, `boulder_a` (72 x 54 x 30 tall) and `boulder_b` (62 x 60 x 34 tall), sharing one 4096 atlas at about 19 px/in. Placed at different turns and scales, they can stand in for all six.
- Triangles: a is 8,818 / 3,703 / 1,409 / 439 and b is 8,439 / 3,543 / 1,350 / 420 (LOD 0-3). What's under the lawn is left off.
- The atlas is only 40% full, so a better packer would sharpen it.
- `rock.py` sculpts, bakes and exports. `paint_rock.py` paints. `rock_noise.py` is gradient noise for both, since thresholded value noise reads as pixels. `capture_config.py` and `capture_engine.cs.txt` shoot old and new side by side in s&box.
  `finish.ps1 -Build -Size 4096` runs the build at idle priority and stops at the first step that fails.
- Work files and shots are in `output/asset-improvement-20261030/cerroblanco-boulder/`: `final/` is the comparison, and `draft1/` and `pass2/` are the earlier passes.

## Checked

- Compiled by the editor with no errors reported, and seen in s&box beside the old stones on their own lawn, in a hidden copy of the map's real scene with its sun, sky, fog and post effects. Exposure was held at one value so both match.
- Those shots show no holes or inside-out faces on LOD 0.
- After the install, in the same hidden copy: all six stand right with no old stone left inside a new one, a trace down each new stone hits its own collision, and a trace down each old one hits Dressing.

## Not checked

- Not seen in a match, or with the player camera's finish. Walking into a stone, bullets against it, and the navmesh and bots round the new shapes haven't been tried.
- LODs 1-3 haven't been seen in s&box. `switch_threshold`s (30, 90, 220) are estimates.
- `check_outward.py` can't judge these, since they're open underneath.
- 4096 textures for one prop weren't measured for memory. The colour map compiles to 6.4 MB.

## How it was installed

`install_boulders.py` cut four old stones from `quality-v1/cerroblanco_dressing_v2.obj` (what's drawn), `cerroblanco_dressing.obj` and their hulls from `cerroblanco_dressing_hulls_default.obj` (what's collided with), and added the scene's "Garden Boulders" group. Each stone matched the map's own code: 110 faces in all, and one hull each. `cerroblanco_map` does the same on a full run, which hasn't been tested. `check_install.cs.txt` is the check.

## Known weaknesses

- `boulder_b`'s top looks a little folded, where cracks and broken faces crowd together.
- Close up, at about 19 px/in, the grains are soft.
- `boulder_a` overhangs the lawn at one end.
- The collision is one convex hull, so it stands a little proud of the stone in its hollows.
- The two old stones keep their blotchy tiled rock, so they read as a different stone from the new four.

# Boxyard's steel drum v2

Created 2026-10-30. At the user's word ("yeah new is better replace pls") it replaced the five 205 l drums in Boxyard: three as cover
on bomb site B and two in the south-west corner. Nothing is committed.

The old drum was a 16-sided lathe with no rims, seams or dents. This one has rolled chimes, two rolling hoops, swaged beads, a dished
head with two bungs, a welded seam and real dents. Enamel over primer over steel, chipped on the rims and hoops, with rust running
down from the chips. Its lettering is made up ("LUBE OIL 46", "SOLVENT 12", "NET 205 L"). There are no bullet marks, since players
shoot these themselves.

- Triangles, LOD 0-2: 6,254 / 2,570 / 856, against about 400 per old drum with no LODs. 2048 maps at 33 px/in, with a colour map each
  for blue and red.
- `oil_drum.py` builds, bakes and exports. `paint_oil_drum.py` paints. `render_oil_drum.py` renders. `verify_oil_drum.py` checks.
  `finish.ps1` runs all of those. They use `Sources/Gameplay/capture-flag-v2/` as a toolkit. Rerunning the build can change the
  unwrap, so bake and paint after it: the export refuses to run otherwise.

## How it's installed
`Tools/boxyard_map.py` is the source of truth, so a re-run keeps it. Its `drum()` now writes only the hull it always wrote into the
merged props, with no faces, and `drum_object()` places each model in the scene with no collider. `boxyard_props`' hull files are byte
for byte as they were, so collision hasn't changed. The other models are unchanged too. The old `bx_drum_*` materials stay in the
repository, unused.

I didn't run the script over the real files. I ran it into a scratch folder and copied only `boxyard_props.obj/.mtl/.vmdl` and the
scene across, because a run would also rewrite the radar picture for no reason. The scene file's odd double-newline format is kept,
so its diff is only the five new objects. A real re-run later will rewrite it with normal line endings, and that's harmless.

To undo: `git checkout` those four files and `Tools/boxyard_map.py`.

## Checked, from the files
`verify_oil_drum.py` passes: 0 inside out, within 0.12 in of the old drum's size at LOD 0 and 1 (LOD 2 is 0.15 in wider, at a distance),
the merged props have no drums left, the hull files match the last commit, and all five drums are where their hulls are, on files that
exist, with no collider of their own. The map script's own checks still pass: 0 problems in 76 spots, none cut off, and Retakes clean.

## Not checked
- **Never compiled or seen in s&box.** The editor wasn't allowed. The images are Blender Cycles renders, which flatter any asset. Until
  the editor compiles them, `boxyard_props.vmdl_c` is stale and the five new models have no `_c`, so a game built before that
  shows the old drums. What an open editor does with this on its own hasn't been seen, so look at site B the first time it runs.
- The LOD switch distances (30, 80) are estimates.

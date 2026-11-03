# Riverdale pool rules plates — 2026-10-31

Three matching plates replace the small shared-atlas boards. The dedicated 1024 × 2048 print has consistent type sizes, six numbered rows, a plant header and an identification footer. A folded backing, narrow metal lip, spacers and four screw heads give each board physical depth.

The north board moves from plan east -200 to -228, leaving 24 inches between its nearest edge and the pilaster. Its bounds are east -241..-215, height 40..74. Both upper boards retain their centres and grow from 28 to 34 inches high. The printed faces sit 1.12 inches in front of the wall, clear of the 0.25-inch epoxy band.

Authoring source is `Tools/riverdale_pool_rules.py`, called by `Tools/riverdale_hall.py`. The new surface is registered with the hall's extra materials, so subsequent generator runs retain the design and placement.

## Installation

`build.py` generates only the old and new boards and compares the exact old faces with the published hall. It refuses unmatched geometry. The staged splice replaces 30 backing triangles and six print triangles; every other published face is preserved. New hardware adds 1,476 detail triangles and 30 fine triangles across all three boards.

Run the builder against the original published model state. It deliberately refuses to splice a second time after installation. The original files are retained in `output/riverdale/pool-rules-20261031/backup`; new sources, hashes and geometry counts are in `stage.json` and `stage/`.

`install.cs.txt` runs in the native editor exchange directory. It checks all source and destination hashes before writing, backs up existing files and installs the staged model sources and material. No scene file is edited. Force compilation is available in `compile.cs.txt`; a CLI timeout must be followed by inspection before any retry. In this installation the force-compile call exceeded its connection timeout, then native inspection confirmed all three assets compiled successfully, both models valid, and the fine model using the new material.

## Verification

- The north board was visually checked in the live Riverdale match.
- `capture.cs.txt` checks all three boards in an isolated copy of the saved Riverdale visuals, leaving the open scene and running match untouched. Final captures: `north-final.png`, `west-upper.png`, `east-upper.png` in the output folder.
- All assets report compiled with no asset failures. The project's C# compilers report zero errors.
- No temporary cameras, isolated scenes or CLI processes are retained by these scripts.

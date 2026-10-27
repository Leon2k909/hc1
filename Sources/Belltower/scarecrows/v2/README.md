# Belltower scarecrow v2

The work shirt now has shaped shoulders, sagging sleeves, rolled cuffs, a collar,
button placket, sewn repairs and a turned, uneven hem. Tapered straw bundles and
loose threads emerge from the cuffs and lower shirt. The sack head is asymmetric
with a gathered neck, seams, stitches and a knot. The smaller, crushed field hat
sits lower, has a curved brim, a dished top and a closed crown/brim junction.

`Tools/belltower_scarecrow.py` retains the existing public materials and delegates
to `belltower_scarecrow_v2.py`. The original builder is archived here as
`previous-generator.py`. Existing material paths and texture pixels are reused.

`Tools/belltower_stage_scarecrow_v2.py` exports the two dedicated render imports
under `pending-garden-v1`. Native `import.cs.txt` publishes only their OBJ/MTL
files and checks the current town's import paths and material bindings. It never
writes a ModelDoc, scene or collider. Other town work and an existing unsaved
editor document are preserved. Do not run the full map generator for this change.

`output/belltower/scarecrow-v2/import-request.json` selects the final stage;
the stage contains its source hashes and exact mesh backups. `installed.json`
records the final native compilation, restoration checks and actual map captures.
No gameplay performance claim is made.

# Belltower wheelbarrows — 27 October 2026

Both garden wheelbarrows now use a thin pressed-steel basin with curved heels,
shallow stamped floor channels, small handling dents and a continuous curled rim.
Bent tubular rails and standing loops replace the square beams. The shaped timber
grips reuse the existing photographed wood, with metal ferrules. The pneumatic
wheel has staggered tread, two closed stamped hub dishes, axle hardware and a valve.
Five private materials provide enamel, inner-bed scuffs/residue, frame coating,
rubber and exposed steel. No ImageGen image or generated concept is presented as
an engine capture.

`Tools/belltower_wheelbarrow.py` builds the geometry and writes its materials.
`belltower_gardens.wheelbarrow` delegates to it for future map generation. The
original gardens source is preserved in `previous-gardens.py`.

The accepted migration is `output/belltower/wheelbarrow-v2/stage-v7`. The one-time
`Tools/belltower_stage_wheelbarrow.py` removes exactly 2,360 old prop triangles
from each canonical town OBJ and its three referenced material chunks. All other
OBJ bytes and attribute indices are retained. Each town ModelDoc adds one private
wheelbarrow render import and six material aliases, with its complete physics
suffix preserved byte for byte. New geometry is 11,404 triangles per instance.
The two original wheelbarrow placements remain unchanged.

Do not rerun the whole map generator to apply this repair. The migration expects
the previous prop; it intentionally refuses an already migrated town mesh. Later
prop refinements should refresh the two private wheelbarrow OBJ resources and
materials, retaining the installed town imports and subsequent shared edits.

`import.cs.txt` publishes through the native editor connection, with staged-source,
target, backup and protected-file checks. Preview only publishes private resources
and separate trial town models. Both trials compiled and were inspected before
installation. The two scarecrow OBJ resources changed during preview; stage-v7
retains those current resources and produces the same wheelbarrow/publication
bytes as the inspected stage-v6 preview.

Both installed town models and all six material bindings are compiled and up to
date. Ten local collision traces match exactly before and after installation.
Native images in `output/belltower/quality/wheelbarrow-v2-installed/` cover west,
east, a higher view of the basin and a close view of the wheel. They contain no
temporary renderer override. Each capture records restoration of the scene camera,
tone settings, renderer state, object identities and active editor/play state.
No gameplay C# or saved scene was edited, and no scene save was performed. The
shared editor acquired unrelated unsaved changes during the work and saved the
scene after the final captures. That save is retained; the native receipts preserve
the scene hash used during this task's import and captures.

`verify.py`, `installed.json` and `output/belltower/wheelbarrow-v2/validation.json`
record the installed source and native evidence. No gameplay frame-time claim is made.

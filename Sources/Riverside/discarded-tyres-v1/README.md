# Riverside discarded tyres — 2026-11-04

Replaced twelve loose tyres (four on the pad, eight in the dressing junk piles) with hollow, rounded rubber
casings, bead lips, inner liners, three staggered rows of chamfered tread blocks and moulded sidewall lettering.
Geometry adapts the existing verified `Tools/lowtide_tyres.py` construction; private authored rubber maps and a
sidewall inscription replace its material. No downloaded assets or image generation. The existing camper tyres
retain their original geometry: the generator hook applies only to horizontal discarded tyres.

`layout.py` reproduces the four seeded junk-pile positions and the separate tyre beside the dog run. Every old
face was matched against the published asset before replacement. `prepare_install.py` stages exact Counter
splices into the two public OBJs, snapshots shared inputs and guards hashes against concurrent changes. The
native editor installation changes only those OBJ/MTL/ModelDoc resources and the two offline generator files.
The old528 faces are removed;91,680 replacement faces are added. All52,910 unrelated faces remain exact,
including the approved transformers and searchlight. All hull inputs, complete physics suffixes and scene are
unchanged. No gameplay or lighting changes. A whole-map rebuild is unnecessary and unsafe per the Riverside notes.

`before.png` and `after.png` in `output/riverside/discarded-tyres-v1/` are actual native engine captures with the
same camera, light and exposure. `context/tyre-installed.png` shows the installed pad tyre in Riverside's night
lighting. Temporary capture scenes are destroyed. `verification.json` records hashes, face retention, collision,
finite/nondegenerate data and generator syntax. Native compilation logs confirm public resources are current.
No frame-time benchmark was run. The unused old preview is archived outside Assets with a retirement receipt;
do not rerun the historical preview import after retirement. The rollback snapshots and comparison PNGs remain.

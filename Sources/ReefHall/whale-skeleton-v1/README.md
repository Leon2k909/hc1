# Reef Hall suspended whale skeleton — review, 2026-11-05

Substantial rebuild of the lobby's suspended skeleton at plan(-2300,0), basez475, nominal length640 inches.
Continuous curved/tapered ribs, shaped centra and paired neural arches/spinous/transverse processes, compact
head/neck connection, cranium and separate rostral/temporal bones, long bowed mandibles, thin fan-shaped scapulae,
paired forearm bones, separate finger chains and tapering tail/ventral chevrons. The old solid flipper/tail slabs
are removed. This is an authored museum-inspired game sculpture, not a scientific reconstruction or museum scan.

The original `rh_bone` material and all60 original steel suspension-cable faces are retained exactly. No new
materials, texture generation, external mesh assets or added lights. Photographic visual references were consulted
for the overall exhibit silhouette, including Hope in Hintze Hall (https://www.thincdesign.com/posts/read/a-new-hope).
No reference image is embedded in the game asset; all geometry is authored in `whale.py`.

**Preview only.** Public map and generator unchanged pending acceptance. `build.py` snapshots guarded inputs and
requires all4,520 original bone faces to match the actual public mesh by position, UV, material and normal. New
bone geometry:47,920 triangles. The other38,738 lobby faces remain exact, including all original cables, approved
planters and surrounding improvements. Full ModelDoc physics, all hull sources and saved scene are unchanged.
The sculpture adds no collision. On acceptance, narrow-splice only bone faces and hook `reefhall_map.whale` to the
new body while retaining its exact cable recipe. Do not regenerate the whole map.

`verify.py` checks guarded hashes, exact retained faces/cables, original material, physics suffix and finite,
nondegenerate triangles/unit normals. `capture.cs.txt` renders actual before/after geometry with the same camera,
framing, exposure, floor and lighting. `context.cs.txt` clones saved Reef Hall visual roots and substitutes only
the private lobby model to show its atrium placement. Temporary scenes are destroyed; no document/play controls.
Three preview models compile/load; evidence, snapshots and native receipts live in local `review/` on C:.
No full map rebuild, envmap bake, playtest or FPS benchmark.

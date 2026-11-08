# Lobby queue barrier — native review, 2026-11-06

Rebuilds both reception queue lanes (eight posts/six belts) on the main rotunda
player route. Flat disc feet and faceted shafts become spun weighted bases with
rubber skirts, socketed polished shafts, shaped retractor heads and connector
housings. The belts now enter the heads at z37, rather than meeting the shafts
below the old caps at z35.2. Connector blocks overlap both the webbing and head;
shafts overlap their base collars and cassette mounts. Positions, 6-inch base
radius, maximum 39-inch height and route spacing remain. Existing chrome, dark
head and belt materials are reused. No installed/pending queue-post replacement
was found in the source audit.

`model.py`/`build.py` stage a private fine-model variant. Exactly 952 original
triangles are replaced with 12,344 new triangles. All 89,504 unrelated faces and
their UVs/indices remain, including approved cafe grinder/case/pastry upgrades.
No physics, scene, lights, materials, navigation or public source changes.
Profile normals split at sharp cap transitions and smooth over shallow changes;
geometry checks pass for finite/unit normals, winding, nondegenerate faces and
the exact expected face multiset. Native compile passed; model IsError=false.

`output/cerroblanco/queue-posts-v1/before.png` and `after.png` are matching actual
viewport native-window captures, position (1010,-165,58), angles (14,-33,0), FOV80,
same native crop and original lighting/display settings. No Computer Use,
offscreen scene, temporary cameras or RenderToBitmap. The public Fit-out Detail
model was restored after review, and the scene remains clean. Original barrier
stays active pending approval. No LOD/frame-time test is claimed.

Candidate: `models/maps/cerroblanco/queue-posts-v1/fine.vmdl`. Render-only queue
asset retains map-space coordinates; it is not a local-origin standalone prop.

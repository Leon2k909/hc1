# Queue barrier — revised silver finish, 2026-11-06

User liked the new black retractor tops and spun base shapes, preferred the older
metal appearance but requested improvement, and asked to retain every created
asset. This is a separate variant; original barrier, first new barrier, source,
materials and every earlier model variant remain retained.

The original and first proposal used the same cbf_chrome material. Smoother
geometry changed their reflection appearance. This revision retains the new top,
base and connection geometry, with scoped queue_metal and queue_shaft materials.
Both are fully metallic neutral silver; bases use roughness .18, shafts use
procedural directional microvariation around roughness .15 and brighter .90 tint.
Cylindrical UVs orient the roughness grain vertically on the shafts. The generated
roughness bitmap has no external source image. Global chrome is unchanged.

Private mesh: 12,376 triangles. Exactly 952 old queue triangles are replaced in
the candidate; all 89,504 unrelated faces/indices/UVs are retained. No collision,
scene, lighting or public model changes. Geometry checks pass and native compile
succeeded. Native inspection confirms both new material paths load without errors.

Matching actual viewport native screenshot_game captures are before.png/after.png
under output/cerroblanco/queue-posts-metal-v2, at (1010,-165,58), angles(14,-33,0),
FOV80 and unchanged settings. No Computer Use, offscreen scene or temporary camera.
The public Fit-out Detail model was restored after review, leaving the original
barrier active pending finish approval. All variants remain available.

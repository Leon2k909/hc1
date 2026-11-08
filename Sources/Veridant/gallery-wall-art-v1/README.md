# Gallery artwork placement — applied review, 2026-11-06

Moved three existing framed paintings off window openings and onto solid piers.
South pair art_1/art_2 centers E=-497/-433, N=-543.8, Z=196; west art_5 center
E=-703.8, N=-370, Z=192. All retain their artwork, dimensions, UVs and frames.
The east-wall artwork remains in place. No new props or changed lighting.

Native editor import redirects only touched Buildings render sources to
models/maps/veridant/gallery-wall-art-v1/. Staging matched exactly 14 triangles
per painting, asserts no vertices shared with other geometry, and changes only
those vertex positions. Physics section unchanged. Prior source OBJ files and
output/veridant/gallery-frames-v1/before/parent.vmdl remain for restoration.
The map generator uses the same corrected positions.

Preparation and guarded native import scripts: output/veridant/gallery-frames-v1/.
The explicit full-compile CLI call timed out, but the editor completed its asset
reload and Buildings/Dressing loaded without error. Matching actual displayed
viewport captures before.png and after.png were verified after reload. The
comparison temporarily restored original render-source references to capture
before from a closer unobstructed editor view, then restored the corrected
references. Final live ModelDoc matches the staged corrected file. No offscreen
render, temporary scene/camera, or display/lighting changes.

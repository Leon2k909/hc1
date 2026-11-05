# Belltower wall lantern v2 — review candidate

Prepared after the approved replacement of all seven café tables, on
`codex/belltower-wall-lantern-v2-review`. Approved by the user and installed at all 24 matching wall-lantern positions (12 west, 12 east).

This is the doorway fixture from the original overlap screenshot: plan anchor `(-1850,475,126)`,
heading 180 degrees, reach 15 inches and lantern scale 0.8. `locate.py` reads its deterministic house
generator; `placement.json` preserves the exact accepted location for reproducible review builds.

The complete bracket and lantern are rebuilt: curved wrought support and hook, a beveled oval wall
plate and fixings, rounded tapered corner posts and retaining beads, recessed panes with hinges/latch,
an ogee hipped roof with stepped cornice and open vent cap, a round hanging ring and shaped finial,
and a turned ceramic lampholder with brass socket and warm globe. The existing iron, glass,
emissive bulb, reflector and bronze materials are reused. No textures, lights or collision are saved.

Three LODs: 5,680 / 3,744 / 1,788 triangles versus the original complete fixture's 960 triangles.
The original review builder checked finite, nondegenerate source faces and removed exactly those 960 old triangles
in a private west review variant. Every other source record is retained. All three VMDLs compiled.

Both comparison models use freshly compiled definitions, including an unchanged production
baseline, and discarded warm captures precede the final pair. The final camera, framing,
projection, tone parameters and temporary inspection light match. Effective GPU exposure was not
independently measured. All model/object/camera/tone/editor state and saved source hashes were
restored or preserved. A first prewarm aborted when editor selection changed, before any mutation.

Final evidence: `output/belltower/wall-lantern-v2/{before,after}-final.png` with camera/restore receipts.
`review.json` records checks; `audit.py` preserves and verifies the matched evidence.
The user approved replacement and explicitly requested retention of the original asset because its shape was useful.
All 24 matching fixtures are now separate saved scene objects. Exactly 23,040 baked triangles were replaced
in twelve source meshes; seven affected current/historic map VMDLs and the retained original compiled.
The saved scene, physics, existing object IDs and editor/play state passed native verification.
`installed.json` records the source and state checks. Saved after evidence is `after-installed.png`.

## Retained original � keep this asset

`models/maps/belltower/wall-lantern-original/wall_lantern_original.vmdl` is the complete original
960-triangle lantern and bracket, at the same scale/reach as the review. Its local origin is the wall anchor;
local plan +E faces away from the wall. Mesh, materials, compiled model and procedural source are retained.
The resource compiles and loads successfully. No existing asset files were deleted, including review evidence.
`build_original.py` can stage the original again; `belltower_map._legacy_wall_lantern` retains its authoring code.
`build.py` now stages only the accepted new resource. Custom nonstandard scale/reach calls retain legacy behavior.
Regeneration uses `Tools/belltower_wall_lanterns.py` with stable IDs and mirrored headings.

# Riverdale north-lane hydrant - revision 2 review candidate

Substantial close-range rebuild of the untouched west lane hydrant, plan(-380,2436), facing(0,-1), root engine2436,380,0, yaw0.
Retains the original three-outlet silhouette and30-inch overall height. Separate cast barrel/base/bonnet sections and gasket
seams, base/bonnet hex bolts, machined necks, stepped captive cap rims, pentagonal bosses, casting ribs and hanging linked chains.
The two side outlets and larger front outlet remain capped. No new collision, lights or gameplay components. Revision2 adds
two private512px PBR surfaces: mottled red painted cast iron and aged cap iron, with fine casting normals, restrained rim chips,
rust in paint loss and varied roughness. Shared Riverdale red/dark/zinc resources remain unchanged. Other hydrants remain authored.

Audited existing approved and pending resources, source filenames, CLAUDE notes and active model chats. No hydrant upgrade found.
Excluded Riverside office door (another chat owns it), spawn sign, Riverdale sand-bin revisions and Cerro Blanco bench work.

Resource models/props/riverdale/hydrant_v1/hydrant.vmdl. LODs18,430 /11,390 /2,050, thresholds20/45. geometry.py is the recipe;
build.py stages outside Assets and removes exactly465 fingerprint-matched original triangles only in a private yard copy.
prepare_review.py adapts the established native import/isolated-scene workflow. review.py import compiles three resources;
verify.py checks hashes, winding, degenerate triangles and no physics. review.py context renders fresh before/after scenes under
Riverdale's original Sun/Look/lights, holding exposure at its configured2.5 shadow ceiling. Streaming receives an extra settling
pause. compose.py arranges matched standing-height and close views without retouching images.

Work/receipts: output/riverdale/hydrant-v1/. Six native resources compile; all LODs have zero inverted/degenerate triangles.
Preview only. Public yard source/ModelDoc, scene and reused materials remain hash-protected. Await visual approval under
CLAUDE.md before integration. Later installation must remove only465 original triangles, preserve original collision/lights,
save one renderer and add a narrow generator hook. Never install the private whole-yard comparison resource.

Revision2 responds to the user's request for further improvement. The bonnet now has a curved profile with continuous casting
normals; profile normals remain sharp across machined steps. Pentagonal bosses have flat faces. Oval interlocking chains use
arc-length spacing, and attach through visible cap/body lugs. Raised curved FIRE lettering is unbranded. Custom link sweeps keep
the near LOD below20,000 triangles. surfaces.py generates deterministic cast-paint PBR maps; all image generation is procedural.

previous.vmdl preserves the previously reviewed candidate for the matching v1/v2 comparison. The original465-triangle legacy
cut-out remains separate for eventual integration checks. Final sheet:revision-2-comparison.png. No public map edits were made.

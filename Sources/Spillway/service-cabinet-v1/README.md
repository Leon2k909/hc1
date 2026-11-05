# Spillway service cabinet — 2026-11-04

The user approved this revision and requested installation on2026-11-04. Both public-map replacements
were rechecked against the reviewed hashes; the cargo model is compiled and up to date with no compile failure.

Rebuilt the two original36 x26 x79 inch steel boxes at plan(-325,345,0) and(-280,345,0) as formed
electrical service cabinets: recessed doors and seals, captured hinges, pull handles and key barrels,
rotary isolation switches, equipment plates, pilot lenses, real angled louvres, open fabricated bases,
bolted feet and cable glands. Private powder-coat, metal, rubber and label materials have quiet fine
surface variation and restrained chips. All geometry stays within the exact original box bounds.

The original12-triangle cabinet used in `before.png` is extracted from the actual saved map and translated
to the origin without changing its UVs, normals or material. `after.png` shows the real6,980-triangle mesh.
`capture.cs.txt` renders both using identical native camera, light, floor, exposure and resolution settings.
These are engine renders. The capture report records both resource paths and preservation of editor/play state.

`build.py` stages the current cargo mesh with exactly24 old cabinet triangles removed and13,960 new triangles
added. All25,956 other faces are preserved exactly. `import_preview.cs.txt` publishes private dependencies;
`compile.py` compiles the materials and standalone models. `install.cs.txt` then installs the guarded cargo
OBJ/MTL/ModelDoc and the narrow offline generator hook through the native editor. The public cargo model
was fully recompiled. `check_public.cs.txt` checks its ten private material paths. `verify.py` confirms all
installed file hashes, byte-identical physics suffix, unchanged collision sources and scene, other geometry,
generator syntax and original dimensions. `Tools/spillway_service_cabinet.py` is the retained generator;
`spillway_map.cargo_yard` draws it and keeps the original collision boxes.

Evidence, exact guarded install plan and rollback inputs: `output/spillway/service-cabinet-v1/`.
The context views under the stairs are very dark in the authored lighting. Placement inspection therefore
uses a disposable scene cutaway: `placement.cs.txt` hides only the Control render mesh and adds a temporary
work light, retaining the original collider. This inspection setup is never saved to the map. The main
matched before/after images use neither the cutaway nor this work light. Temporary scenes are destroyed,
and the user's open scene is preserved. The scene, lights, gameplay and collision were not edited.

No image-generation or external download was used. `paint.py` authors the label graphics and fine powder
coating procedurally. The mesh adds roughly14k triangles across the two installed units; no frame-time
benchmark was run. Run builders only against the recorded pre-install baseline, not over the installed mesh.

# Veridant upholstered walnut chair

This revision replaces all 12 published bistro chairs with shaped upholstered
seat/back cushions, sewn seams and piping, rounded walnut joinery, tapered
splayed legs, bowed back rails and protective feet. Dimensions remain about
16 inches wide, 17 inches deep and 33 inches tall. The seat is about 18 inches
above its existing floor.

`Tools/veridant_parts.chair()` continues through `Tools/veridant_chair.py`, which
now delegates to `Tools/veridant_chair_soft.py`. The map material configuration
preserves the three chair material overrides during future generation. The
existing cloth and walnut PBR textures are reused through separate chair
materials; other furniture materials are unchanged.

The parent `veridant_dress.vmdl` replaces just its two chair import paths and
adds the chair material remaps. The canonical map OBJ and all other mesh imports
remain unchanged by this task. All physics/document bytes from the physics
section onward are preserved. No scene, placement or camera edits are required.

The two deduplicated leaf imports contain 98,376 triangles total, or
8,184–8,206 per chair. Each import stays below 65,536 entries in all OBJ tables.
The final wood mapping uses physical perimeter distances, including straight
faces between rounded corners, so the grain has usable UVs across every side.

`output/veridant/chair-v4/stage-v2/` records the initial publication, including
the original model-document backup. `stage-v3/` records the wood UV,
finish and top-joint refinement. `stage-v4/` removes eight zero-area cloth
triangles that coincided at the OBJ writer's precision. The guarded native
importer edits only the chair's own meshes/materials for those passes, leaving
the shared VMDL untouched. Leaf-only publication validates the chair bindings
and target/source hashes while allowing concurrent edits to other props.
`import.cs.txt` validates every input hash before atomic source replacement,
then compiles the three materials and parent model in the native editor.

`capture.cs.txt` renders a separate visual scene and destroys it afterward.
Matched `before/` and reviewed `final/` views show front, rear and terrace
angles. The native receipts confirm the original editor scene, unsaved state
and play state were preserved. The final successful import receipt is
`output/veridant/chair-v4/installed.json`. The final import completed its source
copies before its connection timed out during compilation. No mutation was
retried. `native-resource-state/` subsequently confirmed all four resources
compiled and up to date; `native-complete-views/` confirmed a valid model and
preserved editor state. `record.py` combines those observations with the final
source hashes into the installed receipt.

Run the read-only geometry, source-hash, physics and UV verification with:

    rtk proxy python Tools/veridant_check_chair_soft.py

The recorded result is `output/veridant/chair-v4/validation.json`.

The garden well replacement is a standalone model at
`models/maps/belltower/well-v1/garden_well.vmdl`, with five private materials.
`Tools/belltower_well.py` owns the geometry and material definitions. No source
texture pixels or existing project assets were changed for this standalone asset.

The model has 60 individually bevelled limestone blocks, staggered wall courses,
projecting coping, recessed mortar, a damp inner course, and quiet dark water
five inches below the old water level. The construction previews in
`output/belltower/well-v1/preview/` were rendered in Blender. They are not native
game screenshots or proof of native shader compilation.

The live map still uses its original well. The main chat has a preservation
check open against the centre model, so this side conversation left the existing
centre OBJ/MTL/VMDL, map source and scene untouched. The editor disconnected
before the private preview import; eight new private resources were then copied
while the engine reported no running editor. Native compilation is unverified.

The exact map replacement is staged in `output/belltower/well-v1/stage/`.
It removes only 68 original well triangles and adds 4,944; every other original
mesh byte, the clocks and all VMDL physics are preserved. A separate source
integration patch preserves the original ring collision, timber frame and roof.
`verification.json` records the checks. The original staging manifest is retained;
`source-revalidation.json` documents a later shared furniture-source change and
proves that regenerating the well still produces identical OBJ bytes.

After the main chat releases its centre-model check, use the guarded native
`import-garden-well-v1.cs.txt` in an active, stopped, saved Belltower editor.
It checks all current target hashes before applying the well and source patch;
later main-thread source or centre-model changes cause it to refuse the import.
Do not force-compile the large centre model. Check asset state and take restored
native close/low views before accepting the saved-map appearance.

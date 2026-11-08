# Operations lounge painting — orientation fix and print upgrade, 2026-11-06

The original square painting faced into the west wall, presenting its plain dark
back to the lobby. Corrected its orientation to +E and installed a generated
still life, retaining its 44-inch size, center and frame style. Source
Tools/veridant_operations_art.py; ops generation hook matches one Operations
still life 1 scene object. Original retained at
models/props/shared/operations_art_original_v1/art_original.vmdl. New model
models/props/shared/operations_art_v1/art.vmdl.

Exactly 14 original render triangles replaced; unrelated records/physics retained.
Native compilation and model checks passed, scene saved. Built-in image_gen,
prompt operations-art-v1-prompt.txt; texture
Assets/materials/veridant/operations-art-v1/still-life.png. Matching displayed
viewport before.png/after.png and original snapshots under output/veridant/operations-art-v1/.
No temporary rendering or changed lighting/display settings.

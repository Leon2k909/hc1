# Generated wool rug texture — applied review, 2026-11-06

Replaced rejected flat stripe geometry with an imagegen wool herringbone albedo,
mapped once across the entire rug with its generated bound edge. Built-in
image_gen tool; prompt in gallery-rug-v2-prompt.txt. Final project image is
Assets/materials/veridant/gallery-rug-v2/rug-albedo.png. Roughness .98, metalness
zero, flat normal; no artificial high-frequency normal derived from shadows.

Source Tools/veridant_gallery_rug.py now emits only one full-texture quad with
0..1 UVs. Existing gallery rug model reference updated natively; material/model
compile checks passed, same footprint/layout/collision/lighting. Scene already
saved, no unsaved changes. Native model-load checks passed.

Preparation output/veridant/gallery-rug-v1/generated.py; new staging and actual
matching displayed before/after captures output/veridant/gallery-rug-v2/.
Generated image itself is an asset, not review evidence. Only the actual editor
captures are used for the comparison; no offscreen renders or altered settings.

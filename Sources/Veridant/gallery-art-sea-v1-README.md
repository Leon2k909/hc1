# Gallery seascape — applied review, 2026-11-06

Replaced the west-gallery blurry atlas print with a high-resolution generated
seascape. Same 37.5x50-inch image, frame, placement, lighting and collision.
Built-in image_gen; prompt gallery-art-sea-v1-prompt.txt. Final texture
Assets/materials/veridant/gallery-art-sea-v1/sea.png. Original retained at
models/props/shared/gallery_art_sea_original_v1/art_original.vmdl; new framed model
models/props/shared/gallery_art_sea_v1/art.vmdl.

Source Tools/veridant_gallery_art_sea.py; lounge generation hook matches one
Gallery sea painting 1 scene object. Replaced exactly 14 original render faces,
preserving unrelated records and physics. Native compilation/model checks passed;
scene saved. Staging, original source/parent snapshots and actual matching
displayed viewport before.png/after.png are under output/veridant/gallery-art-sea-v1/.
No offscreen rendering or altered lighting/display settings.

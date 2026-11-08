# Gallery olive-grove painting — applied review, 2026-11-06

Replaced the second blurry south-wall atlas print with a generated olive-grove
painting. Same 39x52-inch dimensions, frame, center and collision/lighting.
Built-in image_gen, prompt gallery-art-olive-v1-prompt.txt; final texture
Assets/materials/veridant/gallery-art-olive-v1/olive.png. Original framed print
retained at models/props/shared/gallery_art_olive_original_v1/art_original.vmdl.
New framed model models/props/shared/gallery_art_olive_v1/art.vmdl.

Source Tools/veridant_gallery_art_olive.py; lounge generation hook matches current
one Gallery olive painting 1 scene object. Exactly 14 original render triangles
removed; unrelated records and physics retained. Native compilation/model-load
checks passed, scene saved. Staging, original source/parent snapshots and matching
actual displayed viewport before.png/after.png are under
output/veridant/gallery-art-olive-v1/. No temporary renders or changed settings.

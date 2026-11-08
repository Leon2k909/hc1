# Gallery coastal painting — applied review, 2026-11-06

Replaced one blurry atlas print with a high-resolution generated coastal painting,
retaining its 39x52-inch image size, frame and placement. Built-in image_gen;
prompt gallery-art-v1-prompt.txt. Final image
Assets/materials/veridant/gallery-art-v1/coastal.png. Original framed print retained
at models/props/shared/gallery_art_original_v1/art_original.vmdl. New framed asset
models/props/shared/gallery_art_v1/art.vmdl. Same 14 triangles; original render
faces removed from Buildings source imports, physics and unrelated records retained.

Source Tools/veridant_gallery_art.py; lounge generation hook reproduces it. Current
scene uses one Gallery coastal painting 1 object. Native compilation/model checks
passed, saved without unsaved changes. An initially misplaced object in another
open scene was deleted by exact GUID before correct placement and validation.
Matching actual displayed viewport captures output/veridant/gallery-art-v1/
before.png and after.png. No offscreen rendering or changed lighting/display settings.

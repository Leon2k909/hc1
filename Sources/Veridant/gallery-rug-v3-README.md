# Rug texture density correction — applied, 2026-11-06

User reported pixelation in the full-rug generated image. Generated a seamless
wool fabric patch with built-in image_gen and mapped each repeat to 24 inches,
rather than stretching one image across 340 inches. Separate three-inch binding
uses the existing matte material. Actual image is 1254x1254, about 52 pixels per
inch before mipmapping; previous image was about 4.4 pixels per inch horizontally.

Final texture Assets/materials/veridant/gallery-rug-v3/rug-albedo.png; material
generated.vmat in the same folder. Prompt gallery-rug-v3-prompt.txt. Source
Tools/veridant_gallery_rug.py and tile-generated.py under output/veridant/gallery-rug-v1/.
Same scene object/model, footprint and layout. Native material/model compilation
and model-load checks passed; no unsaved scene changes. Actual matching displayed
viewport captures output/veridant/gallery-rug-v3/before.png and after.png. No
offscreen review renders or altered settings.

# Short 3D grass: one-bed review

The user rejected the 4K lawn material swap because the ground still looked flat. Restored the original lawn material on Ground, Dressing and garden relief; the map and relief generator changes for that swap were reverted. The scanned material and its source files remain available unused.

Installed one render-only field of actual blade geometry on the south garden bed at plan E~664..1175, N~-1344..-1223. Reuses the existing models/grass/grass_tuft blade geometry, UVs, texture and grass shader. Blade widths are narrowed to 25% before scaling, with randomized 2.65..3.82-inch heights and turns. No ground geometry, paving, relief, lighting or collision changes. Other lawns remain untouched for this review.

New reusable model: models/props/shared/veridant_short_garden_grass_v1/grass.vmdl. Scene object 4cce916e-5444-49ba-b215-b15e4358ae50, world (-1285,-920,0). Local coordinates are essential: the existing grass shader uses object-origin distance to control growth/fading. This preview contains 2976 tufts, 333312 triangles, one renderer, no collider. Its highest-detail blade field is retained for this near-player review; lower-detail source variants are saved but not active. Do not extend the dense field over the whole map without further density/distance tuning.

Build/import scripts: output/veridant/garden-grass-blades-v1/prepare.py and import.json. Original shared grass resources and all earlier material variants are retained. This one-bed trial is a saved editor scene addition; the full map generator has not been changed to scatter grass pending review.

Matching actual native editor viewport captures: world camera (-1250,-780,64), angles (16,110,0), FOV80. Before.png is the restored original ground (19.21.39); after.png shows the 3D-blade field (19.26.15). No temporary cameras, isolated scenes, offscreen renders or display/lighting changes. Images under output/veridant/garden-grass-blades-v1. Review pending.

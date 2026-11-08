# Reception ceiling light bezels — applied review, 2026-11-06

Four 64-segment recessed metal trims cover the old faceted fixture rims, preserving
the original emissive lenses and point-light settings. The 3,072-triangle model
uses existing vr_steel, has no collision, and is saved through the native editor
as one Reception downlight bezels object. The north_block generation hook emits
the same geometry into the buildings model when regenerating the map/scene.

Source: Tools/veridant_downlight_bezels.py. Import preparation, stage and actual
matching viewport before/after images: output/veridant/downlight-bezels-v1/.
No temporary camera, RenderToBitmap, lighting or post-processing changes.

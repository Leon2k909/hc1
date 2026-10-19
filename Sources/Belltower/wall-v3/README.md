# Belltower limestone and climbing ivy

The square-block material from wall-v2 is replaced with irregular limestone,
narrow lime joints and matching height shading. Its town-wall geometry cleanup
remains in place. This pass changes materials and textures only.

Built-in ImageGen produced the visual target, original color and height images,
and transparent ivy. Exact prompts and saved paths are in `generation.json`.
Selected source pixels are retained unchanged in `Sources/Belltower/generated`;
the engine copies live under `Assets/materials/belltower/generated`.

`Tools/belltower_wall_quilt.py` creates numerical material data. R/G select offset
UV samples along minimum-cost joins shared by the color and height. The unequal
offsets avoid half-tile duplication. B stores per-stone luminance computed from
211 height regions, allowing the shader to soften pigmentation while keeping
surface grain. The color and height images are not repainted. The source patch
spans six metres in the generated 160-inch mesh UVs.

`Sources/Belltower/shaders/belltower_masonry_v3.shader` traces shallow recessed
joints, derives correctly oriented normals from the same height field, and adds
continuous weathering. Relief fades from 600 to 1400 units. The ivy uses the
existing alpha-tested plant shader with the generated RGBA cutout. Definitions
live in `Tools/belltower_quality_materials.py`; the older material/front generators
delegate to it, preserving these definitions during rebuilds.

Regenerate material data with `rtk python Tools/belltower_wall_quilt.py`, then stage
`rtk python Tools/belltower_quality_materials.py --only rubble ivy_climb`. Copy
`Sources/Belltower/editor/import-wall-v3.cs.txt` to the native session exchange and
run it through `run_csharp`, then compile the two materials. The importer refuses
a live Belltower match and preserves other sessions.

Native captures and verification are in `output/belltower/quality/wall-v3`:
`wall-ivy-close.png`, `wall-front.png`, `grazing.png`, and `east-wall.png`.
Both materials compiled and loaded with their expected shader and full-size
textures. Scene, model and collision sources match the preceding geometry pass.
No runtime FPS improvement is claimed for this visual material pass.

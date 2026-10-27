# Fired terracotta pot finish

The pot material used the building render's coarse normal/roughness maps at a
256-inch mapping scale. Its small surface sampled a broad, lumpy plaster relief.
The replacement uses dedicated fired-clay colour, ceramic micro-grain and roughness
at a twelve-inch scale. Continuous world projection avoids the old per-face UV
transitions. Restrained mineral deposits affect the upper lip; the base has subtle
moisture darkening. Opacity remains solid.

The colour source was generated with the **built-in ImageGen tool**. The full
prompt and original source checksum are in `generation.json`; the unchanged
1254-square generated source is `clay-albedo-v1.png`. The production colour was
exported to 2048 square because the engine's mip compiler requires power-of-two
dimensions. Fine normal and roughness maps were generated independently from
seeded numeric ceramic micro-height, not the old plaster or the albedo shading.

Installed assets:

- `Assets/materials/buildings/clay_pot.vmat`
- `Assets/materials/belltower/terracotta-v1/clay-albedo-v1.png`
- `Assets/materials/belltower/terracotta-v1/clay-normal-v1.png`
- `Assets/materials/belltower/terracotta-v1/clay-roughness-v1.png`
- `Assets/shaders/belltower_terracotta.shader`

`Tools/belltower_terracotta.py` stages those assets. `building_textures.vmat`
delegates just the `clay_pot` definition to its `material()` function so material
regeneration retains the finish. The original shared clay colour, roof materials
and wall normal/roughness files are unchanged. No pot positions, geometry,
foliage, scene data or collision were changed by this task.

Final stage: `output/belltower/terracotta-v1/stage-v2`. The original material
backup is under `stage-v1/before`; stage-v1 also preserves the development export.
`import.cs.txt` validates hashes and publishes through the native editor. The
shader is compiled with `EditorUtility.CompileShader` (`compile-shader.cs.txt`),
then the material with native `asset_compile`.

Matched before/after native images are under `output/belltower/quality/` in
`terracotta-v1-before` and `terracotta-v1-installed-v2`. Both the shaded east pot
and sunlit west pot were reviewed. The remaining dark band under the projecting
lip is its cast shadow; the coarse plaster relief and UV transition are removed.
The original fourteen-sided silhouette remains; this task changes its finish.

The shared editor had unsaved work throughout. Its camera, selected document,
object set, play state, saved scene and dirty state were preserved. No scene save,
play stop, editor restart or full town-model compile was performed.

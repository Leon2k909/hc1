# AUG stock texture cleanup

Mode: built-in image_gen, precise-object-edit. The existing stock UV color and normal atlases were edited separately. Generated outputs are retained under `C:/Users/leon2/.codex/generated_images/01a0d475-c7ae-7d30-8336-dd8205e0d489/`.

Production paths:

- `D:/Documents/s&box projects/hc1/forked-shooter-main/Assets/Weapons/AUG/materials/aug_stock_tactical_clean_color.png`
- `D:/Documents/s&box projects/hc1/forked-shooter-main/Assets/Weapons/AUG/materials/aug_stock_tactical_clean_normal.png`

Outputs were resampled to the original 1024 x 1024 texture size with FFmpeg for matching engine mip generation. The material uses these sibling files; the builder preserves their references.

## Color prompt

Use case: precise-object-edit. Edit target: the attached square game UV base-color texture atlas. Remove ONLY the two embossed FSS letter logos: one horizontal near pixel (100,192), another rotated vertical near (600,755), coordinates refer to 1024x1024 preview. Fill each logo with seamlessly matching blank tan olive polymer and its subtle wear. Preserve exact original image dimensions, pixel registration, UV island layout, colors, all screws/metal/rubber/wear and every other detail. This is a production albedo map, not a render of the gun: output only this identical flat texture atlas with those two FSS marks erased. No new letters, logos, symbols, text, decorative additions, shadows or relighting.

Generated file: `exec-14912652-bf84-46d8-8b1f-8d2c37693546.png`

## Normal prompt

Use case: precise-object-edit. Edit target: attached tangent-space normal map for a game UV texture atlas. Remove ONLY the embossed FSS lettering in two positions: horizontal logo around (100,192), vertical logo around (600,755), coordinates from 1024x1024 preview. Smooth these two areas to seamlessly match the local blue-purple tangent-space normal of the surrounding flat plastic. Preserve exact dimensions, alignment, every UV island, every hard edge, screw, rubber groove, and all normal map channel colors everywhere else. Do NOT turn this into a color texture or a render. Output the identical blue-purple normal map with only the two raised letter logos removed. No text or additions.

Generated file: `exec-477475cc-dd39-4096-a4e9-d737b2838a9f.png`

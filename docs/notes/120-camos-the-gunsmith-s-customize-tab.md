## Camos (the gunsmith's Customize tab)
- Duplicates: on 2026-09-29 the user saw the same camo twice in Standard (`120c0e08` and `120c0e08-e7cd-...`, next to
  each other since the list is by name). 24 parts that were exact copies of another (same category, same image bytes,
  same material) went to `Backups/duplicate_camos/`, keeping the friendly-named twin: the GUID-named sapphire, emerald,
  gold2 and alien sets, `7e6b133c_animated` (= gold_animated), `120c0e08`, `custom_png` (= mycamo), and the "Seamless Test"
  `04834e09-...fea_seamless`. Animated versions with a different material (e.g. `magma_fast` / `magma_slow`) aren't copies.
- A compiled file with no source still loads: `1a_seamless.gnsmth_c` ("1a (Seamless Test)", a plain camo on `1.png`,
  whose `.gnsmth` was deleted in June) showed as a second "1" in Standard. It and its `1a_seamless.vmat_c` are in
  `Backups/duplicate_camos/` too. To find more: a `.gnsmth_c` in Assets with no `.gnsmth` beside it (the
  `*.generated.vtex_c` in `camos/` have no source by design).
- Mastery: the user wants different mastery camos, to pick later, so the tab reads "No mastery camos" meanwhile. Diamond
  and Mastery (`diamond.gnsmth`, `mastery.gnsmth`) stay as Standard camos (Camoflague, levels 30 and 100); their
  MasteryCamo versions are in `Backups/mastery_camos/`.
- Solid colours are paint, like Cerakote: `ApplyAttachments` gives a Camoflague part with no texture or material a flat
  texture of its `CamoTint` (`FlatTexture`), so it takes the texture path (the colour replaces the gun's, over its
  normal and AO, with the satin finish). As a tint it multiplied the gun's dark colour, which barely showed, and turned
  the FAMAS's lighter magazine lime.
- The custom colour (the Solid tab's "Enable custom colour") is paint too, in the finish picked (`ApplyCustomFinish`:
  flat metalness and roughness from `FinishMetalness` / `FinishRoughness`). Below full opacity `CustomPaintTexture`
  blends it over the material's own colour map, read back once with `GetPixels` at its first mip no more than 512
  across; if that can't be read it's flat paint.
- The camo tiles are `@key`ed by part: without it, switching tabs reused the tiles, and a tile kept the
  `background-image` its new style left out, so the Solid tab showed the Standard tab's first pictures.


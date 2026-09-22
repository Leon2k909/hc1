# Material artwork

Created with the built-in `image_gen` tool, then copied into project assets. Blender generated the geometry-dependent normal, roughness, metalness and AO maps. No photograph of a finished attachment is pasted onto the model. The reviewed color atlases preserve the UV layout of `m4a1_parts_pbr.blend`.

## Final assets and generation specifications

### Anodized metal input tile

- Project: `Assets/attachments/m4a1/textures/recon_anodized_color.png`
- Generated output: `C:/Users/leon2/.codex/generated_images/01a0c8e5-1126-76f2-982b-234ea9b91e9a/exec-4ec40c2d-474c-4928-bd24-c9fa38be0f55.png`
- Prompt specification: seamless square 2048 PBR base-color texture; uniform charcoal around #333538; fine bead-blasted anodized metal with subtle grain and hairlines. Flat material only, with no baked lighting, highlights, shadows, gradients, panels, bolts, holes, text or weapon. This tile supplies the Blender bake input, including the M4 suppressor finishes.

### Recon handguard color atlas

- Project: `Assets/attachments/m4a1/heavy_barrel/heavy_barrel_color_authored.png`
- Generated output: `C:/Users/leon2/.codex/generated_images/01a0c8e5-1126-76f2-982b-234ea9b91e9a/exec-732375f0-1f0c-4d2d-9161-b431f6a558a5.png`
- References: `heavy_barrel_color.png` bake and the user's M4 receiver screenshot `codex-clipboard-744bc7d8-b485-44b1-a09b-efe27c6692c1.png`.
- Prompt specification: precise edit of the 2048 UV atlas; preserve every island silhouette, position, dimensions, holes and gaps. Match the original receiver's worn black metal. Paint gray islands satin black hard-anodized metal around #303235, with restrained grain, tonal variation and thin broken rubbed silver edges, especially rails and slot rims. Sparse machining marks and hairline abrasions. Maintain black padding and near-black interiors. No added geometry, text, labels, lighting or reflections. Return only the atlas.

### Recon stock color atlas

- Project: `Assets/attachments/m4a1/precision_stock/precision_stock_color_authored.png`
- Generated output: `C:/Users/leon2/.codex/generated_images/01a0c8e5-1126-76f2-982b-234ea9b91e9a/exec-34bf89d5-1018-46e0-8ec7-1ddbc9352b4e.png`
- References: `precision_stock_color.png` bake and the same M4 screenshot.
- Prompt specification: preserve the exact 2048 UV layout. Large window faces and rectangular islands are black glass-filled polymer, with fine molded grain, handling polish, subtle scuffs, nicks and graphite edge wear. Small mechanical islands are dark metal; rubber remains near black. A maintained, used modern military gun, dark charcoal around #2b2d30. No fabric, carbon fiber, light-gray finish, rust or heavy damage. No added decals, geometry or lighting. Return only the atlas.

The final stock material uses a 0.65 color tint and 0.85 roughness scale, judged beside the original receiver in actual gunsmith lighting. Authored texture dimensions and final model/map dependency checks are in `qa/asset-validation.json`. Generated color atlases must be redone when the UV layout changes; `apply_authored_finishes.py` only reconnects an already reviewed matching atlas.

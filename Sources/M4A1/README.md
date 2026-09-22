# M4A1 Recon attachment art

Additional M4 optics—Reflex Sight, Patrol Red Dot and Scout 3x—are documented in [optics.md](optics.md), including rebuild steps and native validation.

**Recon Barrel Kit** replaces the first-person handguard with a vented rail, exposed slim barrel, clamp, fasteners and rounded edges. **Recon Stock** replaces the entire factory stock with an open frame, cheek rest, adjustment lever, sling sockets and rubber buttplate. **Compact Suppressor** and **Rifle Suppressor** are independent Muzzle selections. All four unlock at level 0. The legacy `heavy_barrel` and `precision_stock` resource paths remain stable for saved loadouts.

The finishes use unique UVs and model-specific color, normal, roughness, metalness and ambient-occlusion maps. The handguard has restrained worn anodized metal; the stock has darker molded polymer, separate rubber and metal response. Suppressors reuse the established HC1 cosmetic geometry with new M4-specific UVs and PBR materials. Their shared source assets are not overwritten. The color artwork was created with the built-in image generator; see [material-art.md](material-art.md).

## Mounting and restoration

The stock follows the animated `stock` bone. First-person factory stock/handguard material slots are hidden while replacements are equipped. The world stock uses a copy of the original receiver mesh with the stock removed, retaining the original UVs/material. Only its original base bodygroup is suppressed; other weapon bodygroups remain intact. Unequipping restores the original body synchronously. The world rail has a separate inner-cover variant to conceal the world model's baked handguard.

The barrel and muzzle use the animated muzzle socket, with explicit offsets for the static world model. Render options match the weapon. Independent Muzzle parts activate the existing suppressed sound/flash/radar behavior. Removing the barrel kit leaves the suppressor equipped. Active bodygroup requirements are reapplied after another part is removed.

RMR housing camo respects Apply Camo to Optics; glass and reticle remain separate. Camo applies to the new meshes. The gunsmith camera includes attachment bounds when framing the weapon beside the armory panel.

## Rebuilding

Run from the repository root. Blender 5.1 is used for mesh export and baking.

```powershell
rtk proxy 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --threads 4 --python Sources/M4A1/build_parts.py
rtk proxy 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --threads 4 --python Sources/M4A1/bake_finishes.py
rtk proxy 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --threads 4 --python Sources/M4A1/export_variants.py
rtk proxy 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --threads 4 --python Sources/M4A1/bake_finishes.py -- --suppressors
rtk python Sources/M4A1/apply_authored_finishes.py
rtk python Sources/M4A1/install_parts.py
rtk python Sources/M4A1/validate_assets.py
```

If mesh/UV layout changes, regenerate the authored color atlases before applying them. The unmodified Blender color bakes remain alongside the reviewed atlases. Non-color maps are 2048 square, except AO at 1024; authored color output dimensions are recorded in `qa/asset-validation.json`. The `.blend` files retain the source geometry and baked UVs. `world_base` is extracted from the mounted original model using the native stock inspection fixture.

## Validation

`qa/asset-validation.json` records actual triangle counts, finite geometry, UV/index validity, normal lengths, non-degenerate authored triangles, image sizes and local dependency checks. The original receiver material is an engine-mounted package dependency, checked in native renders.

Native fixtures are kept in `qa/`, outside normal Editor compilation. Temporarily copy the relevant `.cs` files into `Editor/` to rerun:

- `M4FrontEndQa.cs`: `m4_front_qa false rifle_suppressor true` (arguments: world model, muzzle choice or `none`, custom stock). Checks disabled-root initialization, serialized prefab references, valid models, world variant, independent selections, original-part restoration and suppression state/sound configuration. Saves `front-*.png`. Isolated tests restore loadout cookies.
- `M4A1NativeQa.cs`: `razed_m4_preview false true texture` (world model, optics camo, texture/animated/solid). Checks camo branches, RMR housing versus lens, equip/remove/re-equip, saved choices and render layers. `razed_m4_refresh` recompiles attachment references.
- `M4A1UiQa.cs`: `razed_m4_ui disk` validates freshly deserialized resources. `reload` and `capture` inspect the running gunsmith. This UI fixture changes the current weapon, so use a test class. `live-front-end.png` captures the actual UI at 1920x928.
- `M4StockInspect.cs`: native model inspection and reproducible stockless world-base extraction.

Remove the temporary Editor copies after QA. `qa/engine-validation.log` contains native assertions. Build with `rtk dotnet build Editor/razed.editor.csproj --no-restore -v q -m:2`. Suppression checks validate state and sound configuration; they do not substitute for a live firing/audio test. Older camo screenshots are behavioral evidence from earlier art revisions; use `live-front-end.png` and the latest `front-*-stock.png` for current appearance.

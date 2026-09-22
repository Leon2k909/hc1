# MW2022 attachments fitted to the existing HC1 M4

Downloaded anonymously from Steam Workshop on 22 September 2026. No Steam account login was needed. The HC1 M4 receiver, animation rig, reload animations and weapon identity are retained.

## Files

- `Assets/attachments/mw2022`: Source-unit OBJ meshes, native ModelDoc files, translated materials and decoded PNG textures.
- `Assets/gunsmith/m4a1/mw2022`: 83 selectable physical attachment options, using 82 distinct models. The two flip-hybrid variants share geometry.
- `Sources/MW2022/models`: editable Blender sources with the original attachment skeletons, weights, bodygroup variants, UVs and linked texture nodes; JSON metadata records the source bones and mounting points.
- `inventory.json`: all 97 entries in the addon's M4 customization menu, including defaults, perks and camo entries that have no model. Includes dependency archives, SHA-256 hashes and original paths.
- `conversion.json`, `materials.json`, `installed.json`: machine-readable conversion and integration inventories.
- `qa`: engine validation output and rendered fit checks.

| Physical category | Options |
| --- | ---: |
| Barrels / handguards | 8 |
| Stocks | 9 |
| Rear grips | 6 |
| Magazines | 4 |
| Muzzle devices | 17 |
| Optics | 27 |
| Foregrips / bipod | 8 |
| Laser modules | 3 |
| Underbarrel launcher | 1 |

The laser has an independent Gunsmith slot. The launcher occupies the underbarrel slot, preventing it from intersecting an equipped foregrip. All new options are M4-specific and have `(MW22)` in their names.

## Provenance and originals

1. [Modern Warfare 2022 SWEPs - M4](https://steamcommunity.com/sharedfiles/filedetails/?id=2962304029), workshop ID `2962304029`.
2. [Modern Warfare 2022 SWEPs - Shared Content](https://steamcommunity.com/sharedfiles/filedetails/?id=3529121373), workshop ID `3529121373`.
3. [Modern Wokefare Base](https://steamcommunity.com/sharedfiles/filedetails/?id=2459720887), workshop ID `2459720887`.

Original `gmpublisher.gma` archives remain under `D:/tmp/hc1-mw22-tools/steamcmd/steamapps/workshop/content/4000/<ID>/`. Complete extracted addons, including original MDL/VVD/VTX, VMT/VTF, Lua and audio, remain under `D:/tmp/hc1-mw22-tools/extracted/<ID>/`. The Workshop pages retain the original creators' credits. These conversions do not establish a new redistribution licence for the artwork.

Valve's GMAD performed extraction. [SourceIO](https://github.com/REDxEYE/SourceIO) imported the Source models and decoded textures; Blender 5.1 saved the editable files. Crowbar/VTFEdit were not needed. No addon Lua was executed.

## Integration details and limits

`GunsmithMw22Attachment` maps each source origin onto the current M4's bind pose. The magazine follows its existing animated magazine bone. Barrel metadata supplies the mounting positions for muzzle devices, grips and laser modules. `GunsmithMw22Factory` separates the original rigid factory sections, preserving their UVs and their individual moving bones; this avoids leaving a factory barrel or grip inside its replacement.

Discharge flashes, smoke and tracer origins follow the fitted barrel or muzzle device through `WeaponModel.DischargeMuzzle`. The original muzzle object remains the reference for existing socket-mounted accessories. Existing muzzle attachments can follow a MW22 barrel as well.

Magazine capacities use the existing ammunition system (15/30/45/60 rounds) and do not grant ammunition on equip. Suppressors use the game's existing suppression flag. Optical magnification uses the existing FOV mechanism. Source stencil and render-target lens surfaces are replaced with a clear s&box lens and reticle.

This is an asset and mounting port, not a port of Garry's Mod's weapon framework. Laser beams/accuracy bonuses, grenade launching, thermal imaging, switchable hybrid/variable modes, deployed-bipod mechanics and the original Lua perks are not implemented. Those limitations are also stated on the relevant Gunsmith options. The physical bipod is imported in its authored rest pose. The source addon's Black camo and perk scripts remain in the extracted original pack.

VTF colour and normal maps are retained. Source Phong exponent textures are approximated as roughness; these are not recovered MWII metalness/roughness maps. One source decal VMT contains an unresolved `${NORMALNAME}` placeholder and uses a flat normal. Attachment-specific Source animations remain in the original MDLs; the editable attachment files retain rest skeletons and weights.

## Rebuild

The scripts assume this repository layout and default to the local tool cache at `D:/tmp/hc1-mw22-tools`. Blender imports use the SourceIO checkout there, without globally installing a Blender addon.

```powershell
rtk proxy D:/tmp/hc1-mw22-tools/steamcmd/steamcmd.exe +login anonymous +workshop_download_item 4000 2962304029 validate +workshop_download_item 4000 3529121373 validate +workshop_download_item 4000 2459720887 validate +quit
# Extract each downloaded GMA with GMAD before rebuilding the inventory.
rtk python Sources/MW2022/inventory.py
rtk proxy 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' -b --python Sources/MW2022/convert_models.py
rtk python Sources/MW2022/convert_materials.py
rtk python Sources/MW2022/install_parts.py
rtk python Sources/MW2022/prepare_optics.py
rtk proxy 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' -b --python Sources/MW2022/link_blender_materials.py
```

`import_current_m4.py` and `build_factory_sections.py` recover and split only the current rifle's factory sections. They use the installed M4's local compiled cache, not the MW2022 rifle mesh. All view-model vertices in those sections are rigidly weighted to one bone, so splitting them preserves their original animation transforms.

With the project open in s&box, `hc1_mw22_compile`, `hc1_mw22_repair`, `hc1_mw22_audit` and `hc1_mw22_preview` provide native compilation, asset validation and isolated render fixtures. They do not change saved loadouts or the user's scene.

## Validation completed

- `dotnet build Editor/razed.editor.csproj --no-restore -v q -m:2`: passed, zero errors; existing project warnings remain.
- Native audit: all 83 Gunsmith resources, 86 models (82 attachment models plus four factory sections) and their material references loaded.
- `hc1_mw22_roundtrip`: all 83 options equipped and removed on both view/world models, restoring the original bodygroups and materials. All four magazines followed a displaced reload bone. Short/long barrel changes moved the muzzle device and discharge origin correctly.
- `hc1_mw22_optic_check`: all 27 optic options aligned with the aim ray in the original ADS animgraph. The fixture allows 0.04 Source units for the retained idle motion; observed vertical error stayed below 0.025 units.
- Native short-barrel world and long-barrel view renders were inspected, along with isolated reflex, holo and scoped ADS renders. Fixtures destroy their temporary scenes and do not change user loadout cookies.

See `qa/audit.txt`, `qa/roundtrip.txt`, `qa/optic-alignment.json`, `qa/world-short-final.png` and `qa/view-long-final.png`.

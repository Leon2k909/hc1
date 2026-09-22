# Rear grips and magazines

M4A1 and SCAR-H each have two new Gunsmith categories, with four authored parts per rifle:

| Slot | Option | Behavior |
| --- | --- | --- |
| Rear Grip | Rubberized Grip | Contoured rubber overmold; cosmetic |
| Rear Grip | Taped Grip | Raised olive cloth wrap; cosmetic |
| Magazine | 20 Round Compact | 20-round base capacity, reload duration ×0.90 |
| Magazine | 40 Round Extended | 40-round base capacity, reload duration ×1.15 |

Standard restores the original part and weapon capacity/reload duration. All new parts are unlocked immediately. Existing magazine and reload tuning multiply these base values; chamber behavior is preserved. Equipping a larger magazine does not refill ammunition. Spawn/refill uses the selected capacity. Ammunition remains a separate slot, so either magazine works with Standard Rounds or Tracer Rounds. Selections use the existing per-class, per-weapon save and share-code system.

## Art and mounting

`rear_mag_parts.blend` contains the eight source collections. Exported game art is in `Assets/attachments/rear_mag`; weapon-specific resources and prefabs are under `Assets/gunsmith/{m4a1,scarh}/rear_mag`. Meshes include bevels, contoured grips, raised cloth strips, curved magazine shells, reinforcement flutes, witness recesses, feed lips and baseplates. There are twelve exported models, including four differently scaled SCAR world variants.

The 1254×1254 color atlas was generated with the ImageGen tool on 2026-09-22 for this task. Art direction: a flat four-quadrant material atlas with black molded polymer, textured rubber, olive woven cloth and dark metal; no labels or baked directional lighting. The original generated image was `exec-1fbf5a94-ee29-4143-9eb2-f2d38b229bb7.png`. The project copy is `Assets/attachments/rear_mag/textures/rear_mag_atlas_color.png`. UVs use the corresponding quadrants. Five material definitions set roughness, metalness and tint; they use the engine's flat default normal map.

`GunsmithBoneAttachment` mounts art in the weapon model's bind space, then follows its animated grip or magazine bone. The original magazine bodygroup is hidden while a replacement is equipped and restored on removal. The SCAR model definitions split the original weighted `mag` mesh into a bodygroup without changing its bone weights. Their default bodygroup mask is 81 (body + original magazine + iron sights).

Recompiling the SCAR exposed two legacy SMD imports unsupported by the current importer. `convert_legacy_meshes.py` preserves those sight/suppressor meshes as local OBJ files and retains their existing materials and transforms. Native model bounds were compared with the originals and match.

## Rebuild

From the repository root, run these commands in order:

```powershell
rtk proxy "C:/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --threads 3 --python Sources/RearMagazine/build_parts.py
rtk proxy python Sources/RearMagazine/install_parts.py
rtk proxy python Sources/RearMagazine/convert_legacy_meshes.py
rtk proxy python Sources/RearMagazine/validate_assets.py
rtk proxy dotnet build Editor/hc1.editor.csproj --no-restore --nologo -v quiet
```

In the editor console, `hc1_rear_mag_refresh` recompiles the native assets. `hc1_rear_mag_test` checks loadout behavior; `hc1_rear_mag_preview m4a1 false true example` renders an isolated example (`weapon`, `world`, `extended`, `suffix`). `hc1_rear_mag_ui_test example` exercises the open Gunsmith interface and restores the original selections. The UI check expects M4A1 or SCAR-H to be selected.

## Validation

- Game build passes (`qa/game-build.log`). The editor build passed while running the native tests below; the last full editor build subsequently encountered an unrelated in-progress `SceneModel.FinishBoneUpdate` call in `Editor/M4OpticQa.cs` (`qa/build.log`).
- Static validation checks twelve meshes for finite data, valid triangle indices, nonzero triangle areas, unit normals, UV bounds and material/model references; it checks all eight part resources and the texture dimensions.
- Native isolated renders verify both rifles in view/world form, valid materials, factory-magazine hiding, Standard restoration and following a moved magazine bone.
- Loadout validation checks weapon/class isolation, share codes, capacity/tuning, chamber clamps, no free ammo, reload multipliers, Standard reset, tracer independence and ignoring local cookies for non-owned weapons.
- Live Gunsmith clicks verify both grips, both magazines and Standard against saved selections and preview objects; screenshots cover the eight-slot layout.

This validates the HC1 equipment path used by these two rifles. A two-client multiplayer session and a full recorded reload animation were not run. Grip options are cosmetic; their UI does not claim handling-stat changes.

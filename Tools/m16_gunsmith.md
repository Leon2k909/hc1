# M16A4 Gunsmith parts

The source M16 customization list is in the extracted MW22 pack's `lua/weapons/mg_iw9_mike16/customization.lua`. The M16 now exposes nine Gunsmith categories: muzzle, barrel, optic, underbarrel, magazine, rear grip, stock, laser and ammunition.

## Added choices

- 8 stocks: Open-Frame Carbine, Bare Buffer Tube, Minimalist Carbine, Standard Carbine, Adjustable Marksman, Heavy Carbine, Folding Wire and Telescoping PDW.
- 4 barrels: 11.5-inch Heavy Carbine, 14-inch Heavy Carbine, 11.5-inch Quad-Rail and 14.5-inch Free-Float.
- 5 rear grips: Stippled, Skeleton, Palm Support, Ribbed and Straight.
- 15-, 45- and 60-round magazines, each with its source normal/empty reload clips and sound events.

Standard restores the factory fixed stock, 20-inch barrel, grip and 30-round magazine. Magazines are native skinned bodygroups retaining both reload magazine bones. The factory barrel, handguard, front sight, stock and grip have separate bodygroups so replacements remove their original geometry. Both model prefabs use default bodygroup mask `9087989`.

Stocks and barrels reference the existing shared MW22 model prefabs through M16-only resources. Rear grips use M16-specific prefab copies at the original source scale. Other weapons retain their attachment resources and eligibility. Muzzle devices, lasers and foregrips follow the selected barrel's mounts; the muzzle effect follows its flash position.

The source pack also lists a grenade launcher, but the game currently lacks its firing/reload mechanics. Its decorative model is not added as a working attachment.

## Regeneration

Run `rtk proxy python Tools/m16_gunsmith.py` from the project root, then run `hc1_m16_compile` in the s&box editor. The generator uses the existing extracted/decompiled source cache configured in `m16_assets.py` and `kastov_weapons.py`. `--skip-meshes` updates resources, slots, model definitions and animation graph without rebuilding DMX meshes.

The generator hashes other weapons' Gunsmith resources before and after writing. The completed generation added 20 parts and left all 898 existing non-M16 attachment resource/prefab files unchanged.

## Validation

- `hc1_m16_parts_check true` / `false`: all 20 parts equip and reset on the world/view models; model/material validity; factory bodygroups; all four barrel combinations with muzzle/laser/foregrip; muzzle effect positions. Outputs reports and preview PNGs under `output/m16-gunsmith`.
- `hc1_m16_ammo_check`: nine available categories, magazine capacities, matching reload/sound selection, no ammunition granted on equip, and restoration of the standard 30-round capacity. Restores saved selections afterward.
- `hc1_mw22_roundtrip`: existing M4 attachment regression checks.

All checks passed in the editor. The editor C# project builds with no errors; existing warnings remain. Visual previews include `world-standard.png`, the eight stock variants and `view-combined.png` / `world-combined.png`.

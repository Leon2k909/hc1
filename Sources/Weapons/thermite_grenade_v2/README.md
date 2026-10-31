# Thermite grenade v2: the AN-M14 skins

Created 2026-10-30. The user saw the grey and red versions and said to have both as skins, so `EquipmentSkins` lists them after
Standard (the cloud model) and K-52 (`incendiary_grenade_v2`, another session's). Standard stays the default. No prefab changes.

- **AN-M14:** light red with black lettering, the modern scheme.
- **AN-M14 Early:** grey with a purple band and lettering, the scheme before 1987. It shares the red one's meshes and every map but colour.

Sources disagree on when the scheme changed: GlobalSecurity quotes FM 23-30 (1988) for grey and purple, and the Internet Movie Firearms
Database gives 1987 for the change. The shape is modelled from general knowledge, not from drawings, and its sealing tape is a guess.
The lettering uses the real designation, with a made-up lot number.

- Triangles, LOD 0-2: 13,322 / 6,612 / 1,442, against 3,498 / 1,536 / 720.
- One material with 2048 maps (colour, roughness, metalness, normal, AO), about 138 px/in.
- Same origin and axes as the old model, and the same body groups in the same order, so the prefabs' mask of 11 should still show all three.
- LOD distances 0, 4 and 8, as the smoke grenade's, which look like the old model's own.

## Checked, from the files
`verify_thermite.py` passes: 0 inside out on all three LOD 0 meshes, every group within 0.05 in of the old group's bounds, body groups
in order, all files present, and the early skin differs from the main model in its colour map alone. The game code compiles with `hc1check`.

## Seen in s&box, in a real match (2026-10-31)
Both models compile and load with no errors. `match_skins.cs.txt` stands all four skins in a row on a crate, and `match_in_hand.cs.txt` picks each skin as the gear
picker does, draws the grenade, then puts the player's saved pick back. In the hand, the fingers sit fine on all of them.

That found a real bug, now fixed: every skin drew the stock texture on its own mesh in first person. See `docs/notes/161`, and `skin_order_check.cs.txt`, which shows
the old and new order without play mode. Shots are in `output/asset-improvement-20261030/thermite-grenade/engine/`.

## Not checked
The gear picker's layout and pictures, thrown, dropped, holstered on the body, another player seeing it, and the burnt-out canister's black tint.

## Files
`read_old.py` and `old_maps.py` decode the old model for a fair "before". `thermite.py` builds, bakes and exports, `paint_thermite.py` paints
(`THERMITE_SCHEME=early` writes only the early colour map), `verify_thermite.py` checks. `finish.ps1` runs them and renders the sheets, then
`skins.ps1` adds the early skin and renders the picker's pictures, which `picker_pictures.py` shrinks. Exports go to
`output/asset-improvement-20261030/thermite-grenade/export/`, and the installed copy is `Assets/Weapons/Throwable/Molotov_Cocktail/thermite_grenade_v2/`:
copy it across after a re-export. Rerunning the build can change the unwrap, so bake and paint after it.

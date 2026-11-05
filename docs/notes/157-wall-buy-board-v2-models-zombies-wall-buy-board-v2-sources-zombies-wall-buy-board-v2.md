## Wall-buy board v2 (`models/zombies/wall_buy_board_v2`, `Sources/Zombies/wall-buy-board-v2/`, 2026-10-30)
- Zombies' wall-buy stations, replacing a tinted, stretched dev box at the user's word after a before/after. It's an armoury rack
  standing on the floor: a steel frame and feet, five bolted planks where the old board was, a padded rail behind the gun, a padlock
  on a cable and a sign-out sheet. All lettering is invented.
- It keeps the old board's origin, axes, width and top, and fills the station's BoxCollider, which isn't changed. The gun's code isn't
  changed either.
- `CreateStation` falls back to the old box if the model doesn't load, as `CreateBenchModel` does.
- Timber/lettering refresh (2026-11-04): shorter grain, pores, saw marks and roughness/normal detail reduce the smeared
  plank bands. Cleaner sprayed letters remove the doubled-line appearance. Meshes, LODs, UVs and atlas size are unchanged.
  Native full model/material compilation and offline asset checks passed; matched native captures are in
  `output/wall-rack-detail-20261104/`. Live station viewing, LOD distances and a pistol on the rail remain to be checked.
- Approved and installed at the same model/material paths. The gallery's OLD rack and superseded build/comparison
  files were removed; current inputs and approved native shots remain in the detail-pass folder.
- `Code/hc1.csproj` names an old s&box path (`SteamLibrary/...`), so a plain `dotnet build` fails on it, whatever the code. Regenerate
  it, or pass the real paths through `-p:CustomAfterMicrosoftCommonTargets`.

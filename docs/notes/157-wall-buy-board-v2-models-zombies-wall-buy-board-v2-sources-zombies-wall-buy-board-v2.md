## Wall-buy board v2 (`models/zombies/wall_buy_board_v2`, `Sources/Zombies/wall-buy-board-v2/`, 2026-10-30)
- Zombies' wall-buy stations, replacing a tinted, stretched dev box at the user's word after a before/after. It's an armoury rack
  standing on the floor: a steel frame and feet, five bolted planks where the old board was, a padded rail behind the gun, a padlock
  on a cable and a sign-out sheet. All lettering is invented.
- It keeps the old board's origin, axes, width and top, and fills the station's BoxCollider, which isn't changed. The gun's code isn't
  changed either.
- `CreateStation` falls back to the old box if the model doesn't load, as `CreateBenchModel` does.
- Built offline, and the game's code compiles with the swap, but it's **not yet been compiled as an asset or seen in s&box**: check
  for the fallback's warning, the LOD distances and a pistol on the rail. See the folder's README.
- `Code/hc1.csproj` names an old s&box path (`SteamLibrary/...`), so a plain `dotnet build` fails on it, whatever the code. Regenerate
  it, or pass the real paths through `-p:CustomAfterMicrosoftCommonTargets`.

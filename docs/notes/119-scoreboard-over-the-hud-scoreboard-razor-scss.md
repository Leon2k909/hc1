## Scoreboard over the HUD (`Scoreboard.razor.scss`)
- The scoreboard's root panel survives Razor's early return while closed. Since 2026-10-18 it defaults to
  `display: none`, and its full-screen background and backdrop blur apply only under `Scoreboard.visible`.
  Keep those effects off the base selector: otherwise joining a game blurs and darkens the class picker and world.
- The user saw the medals (double kill and the rest) drawn over the scoreboard. Held open, it's now over the rest of the
  HUD, at z-index 2000: over MainHUD's `.center-layer` (the medals, 1700) and `CrosshairHud` (the crosshair and hit
  markers, 1500). It was 100.
- A higher z-index draws over a sibling that comes later in the markup: the medals are before the scoreboard in
  MainHUD.razor, and they drew over it.
- The Return to the AO countdown (`PlayAreaOverlay`) and the drone prompt (`DeployedPawnOverlay`), both 99999, still
  show over it.
- Not yet seen in a match.
- Its look (2026-10-27, the user: "scoreboard needs to look better"). It was slate blue-grey, unlike the rest of the game.
  Now it's in the menus' look:
  - a charcoal sheet with the menus' orange line along its top, Chakra Petch for words and the HUD's Dinish for every
    number (the clock, team scores, positions, stats);
  - each team's heading a band of its colour from a 4px edge, fading off to the right (`Scoreboard.TeamBand`);
  - your row marked in orange, as the HUD marks what's yours; dead players' names and stats dimmed;
  - each team's leader (first in its roster with a score) gets the HUD's crown (`ScoreboardRow.IsLeader`);
  - the voice channel picker is the menus' segmented choice, the picked one in orange; the player details popup matches.
  - Headings are capitals through the translation tables (`Tr( "PLAYERS" )`, `Tr( column.ToUpperInvariant() )`: an
    ALL-CAPS key shows its translation in capitals, with Turkish's İ), not CSS `text-transform`.
  - Checked in a browser mockup of the real SCSS (`output/scoreboard-redesign/20261027/mockup.py`, sass and headless
    Chrome, before and after) and parsed in the engine with no warnings. Not yet seen in a match.


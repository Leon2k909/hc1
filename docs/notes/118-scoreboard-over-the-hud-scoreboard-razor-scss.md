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


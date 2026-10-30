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
- Its look (2026-10-27, the user: "scoreboard needs to look better") is the HUD's: Dinish capitals and numerals, the HUD's
  ink and orange, no outer box.
  - Each team's heading is a banner of its colour fading right (`GetTeamBannerStyle`), with its score at 54 px.
  - Rows are 48 px on dark ink with hairlines; your own row has the orange bar and wash; the dead are greyed.
  - Ping's signal bars are green, amber from 80 ms (`ping-fair`), red from 150 ms (`ping-poor`).
  - The voice channel picker is flat with an orange underline on the chosen one.
  - Each team's leader (first in its roster with a score) gets the HUD's crown (`ScoreboardRow.IsLeader`).
  - Headings are capitals through the translation tables (`Tr( "PLAYERS" )`: an ALL-CAPS key shows its translation in
    capitals, with Turkish's I), not only CSS.
  - Two restyles were made in parallel that day. The other, in the menus' look (a charcoal sheet and Chakra Petch), was
    never committed; the user merged this one later, so it won when the two met on 2026-10-30. Its stylesheet is in commit
    efd629b7 if it's ever wanted. Mocked up in a browser from the real SCSS; not yet compiled or seen in a match.

# Private match validation

Verified in the running s&box editor on 26 September 2026.

- Actual setup controls selected 1v1 Gunfight and constrained capacity to two, then TDM with four player slots.
- Bot fill and Friends / Invite Only controls updated the selected settings.
- Changing settings stayed in the menu; no match launched until the Start button was clicked.
- Clicking Start Private Match loaded TDM on Flatgrass without terminating the editor.
- Runtime checks confirmed a connected local client, a hosted lobby named Razed Private Match, four player slots, retained settings and no bots with bot fill off.
- The loaded map did not contain the legacy PregameLobbyManager.
- Returning to the menu cleared private settings.
- Live visual inspection confirmed PROFILE, the private setup screen and Battle Royale's teal accents.

Screenshots: playwright/private-match-start-verified.png, playwright/private-match-setup-live.png, playwright/battle-royale-teal-live.png.

Game and editor builds passed before live testing. The final rebuild at 18:08 was blocked by 14 RankedPage references to APIs removed from Rank.cs in a separate edit at 18:06:53 (including GetSR, WinSr and SrPerTier). Those files were not changed for this task.

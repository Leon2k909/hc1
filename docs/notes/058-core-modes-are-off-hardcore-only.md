## Core modes are off (hardcore only)
- Ordinary multiplayer modes are hardcore for now; Tactical Defuse uses its own standard-health preset. The user
  wants Core back later, so the Core/Hardcore toggles, the
  "HC" labels and the `SetHardcore( IsHardcore )`-style calls are commented out with "Put back with Core" notes
  (MatchLauncher, PregameLobbyMenu/Manager, CreateLobbyPage, RankedPage, RoundStateDisplay, `GameMode.DisplayTitle`,
  `GameMode.ActiveHardcore` defaults to true). The menus show plain mode names, no "Hardcore". The Core/Hardcore
  toggle for public matches was on the removed Multiplayer page, so it needs a new home when Core comes back.
- Zombies still sets `SetHardcore( false )`, so hardcore's hit rules and one-shot bots don't apply to it. It has its
  own faster regen (`UpdateHealthRegen`).


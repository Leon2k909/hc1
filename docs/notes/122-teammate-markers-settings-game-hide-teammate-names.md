## Teammate markers (Settings → Game → Hide Teammate Names)
- The user asked for a setting that leaves only the circle over teammates' heads, on by default
  (`GameSettings.HideTeammateNames`, stored inverted as `showTeammateNames`, like Corner Slicing).
- With it on, `PlayerMarkerPanel` and `LightweightBotMarkerPanel` draw a teammate's dot only: no health, name or weapon
  icons. A teammate carrying the bomb keeps the bomb icon. Enemy markers are unchanged.
- The setting is in both panels' BuildHash, so switching it redraws them at once. Not yet checked in-game.


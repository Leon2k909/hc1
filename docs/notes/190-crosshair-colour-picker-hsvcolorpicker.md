## Crosshair and hit marker colour picker (`HsvColorPicker`, `HsvStrip`, 2026-11-03)
- The user wanted any colour for the crosshair and the hit marker, not only the 8 swatches. Settings → Crosshair now has
  `HsvColorPicker` (`Code/UI/MenuSystem/Shared/Settings/`) in three places: the HC1 style (`GameSettings.CrosshairColor`,
  which had the settings' hue field), the Custom style (`CrosshairConfig.Color`) and the Hit Marker tab
  (`CrosshairConfig.HitColor`). The rest of the game (the gunsmith, the emblem editor, a settings search) keeps
  `ColorPicker`.
- It has the 8 swatches as quick picks, a colour chip, a hex box (`#` prefix, six hex digits; it applies only once six are
  typed, and goes back to the colour when it loses focus with anything else in it), and hue, saturation and brightness
  bars (`HsvStrip`). `CrosshairPreview` beside it shows the result as it changes.
- It reads the colour through `Get` every frame, so Reset Defaults or a copied crosshair shows straight away, and writes
  through `Set( hex, done )`. The page saves only on `done`: a drag let go, a swatch, a D-pad step, a hex typed in. The HUD
  (`CrosshairHud`, `HitmarkerPainter`, `Crosshair.cs`) reads the settings as it draws, so a change shows in a match at
  once.
- Three bars rather than a saturation/brightness square, so the D-pad reaches every channel: each bar is a `pad-target`
  and an `IPadAdjustable` (left and right step it, about 50 presses end to end, faster when held; the hue bar's step is
  1°). The virtual cursor drags them like a mouse.
- A grey keeps the hue it came from, and black keeps its saturation too (the picker holds H, S and V apart from the hex).
- Nothing is rebuilt during a drag: the bars, the chip and the hex box are styled from code, and only what changed is set.
  The picker rebuilds only when the selected swatch changes. The page no longer hashes the colours. The preview and the
  HUD still rebuild on a colour change, as they did for a swatch.
- `HsvStrip.WantsDrag` is true: otherwise s&box hands a press to the nearest scrolling panel up the tree (the settings'
  column), which drag-scrolls with the mouse while the thumb moves.
- After a hotload the bars came back blank: the rebuild made new bars, and the picker thought it had already styled them.
  `OnAfterTreeRender` now sets `_shown = false`.
- New words "Hue", "Saturation" and "Brightness" are in `SettingsText` and all nine Languages files.
- Checked in s&box on 2026-11-03 (main menu, Hit Marker tab): D-pad steps on the hue and saturation bars, a typed hex and
  a swatch each set and saved the colour, and the preview showed it. The Crosshair tab's two pickers compiled and use the
  same panel, but weren't seen; mouse drags and a real controller weren't tried.

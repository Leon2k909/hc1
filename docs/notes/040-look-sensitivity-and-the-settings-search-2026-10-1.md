## Look sensitivity and the settings search (2026-10-14)
- Settings → Controls has a SENSITIVITY section (the user asked for controller and mouse sensitivity): Mouse, Mouse
  ADS, Controller Horizontal, Controller Vertical and Controller ADS Sensitivity (`GameSettings`, multipliers, default
  1; each getter reads 0 as 1 for old settings files and hotloaded objects). They multiply s&box's own mouse
  sensitivity and stick look speed, which only s&box's menu can change.
  - `LookSensitivitySystem` (Stage.StartUpdate, the active scene only) scales `Input.AnalogLook` once a frame before
    anything reads it. s&box adds the mouse and the right stick into it, so a frame the mouse moved (`Input.MouseDelta`)
    counts as the mouse's, any other as the stick's. ADS is the local pawn's `aiming` equipment tag. It's a new
    GameObjectSystem, so after a hotload it starts only once play restarts.
  - Aim Assist was in the Controls group but never drawn (InputSettings draws that group by hand); it's there now.
  - Every slider in SettingEntry now shows its value beside it (`SliderText`, decimals from its step).
- The settings page has a search box over its categories (`SettingsSearch`): every word must be in a setting's name or
  category, in the player's language or English, case and accents ignored (`LanguageMenu.Fold`). Results are grouped
  by category, and matching keybinds come after them through `InputSettings` with its `Query` set (a keybind's key
  name counts too: "space" finds Jump). Picking a category clears the search. Aim and Sprint Input have
  `[Choices( "Hold", "Toggle" )]` so they show as a switch in the results.
- Compiled with dotnet and hotloaded into the user's match with no errors, with every text in all ten tables. Not yet
  seen: the sliders' effect, the search, or A jumping.


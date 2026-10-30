## Video settings: resolution and quality are s&box's
- Window mode, resolution, VSync, frame rate limits and graphics quality (textures, shadows, AA, AO, bloom, motion
  blur, upscaling) are s&box's own settings, shared by every game. Only its menu can read or change them
  (`MenuUtility.RenderSettings` is in Sandbox.Menu.dll, which the game doesn't reference), so they can't go on our
  settings page. Settings → Video ends with `SboxSettingsLinks`, whose rows open s&box's settings over the game at its
  Display or Graphics tab (`Game.Overlay.ShowSettingsModal( "display" | "graphics" )`).
- That modal opens in the editor too, a frame after the call (checked 2026-09-26). A second call while it's open
  closes it, so only one handler in a click's bubble path may call it.


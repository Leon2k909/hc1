## Crosshair settings preview (`CrosshairPreview`, 2026-10-27)
- The user asked to see crosshair and hit marker changes while editing them. Settings → Crosshair now has a live
  preview box beside the settings (`Code/UI/MenuSystem/Shared/Settings/CrosshairPreview.razor`), which stays in view
  while the list scrolls and drops under it on a narrow screen.
- It draws every style from the settings as they stand: HC1's own crosshair (the game settings Crosshair.cs reads),
  Classic, Modern and Custom (CrosshairHud's looks), and each hit marker style with HitmarkerPainter's geometry. 1x is
  match size (the HUD and the menu share the 1080p UI scale); 2x and 4x zoom in. Backdrops: dark, grey, light and an
  outdoor sky/ground, to judge contrast.
- Preview Hit (and Loop) play HitmarkerPainter's animation inside the box only; it no longer sets the global
  `CrosshairManager.HitFlash`. The Hit Marker tab holds the marker up when it isn't playing; picking a hit style or a
  duration plays it. The animation changes only the layer's style each frame, never the markup.
- With the HC1 style picked, its Show Dot, Dynamic, Length, Width, Distance and Colour rows show on the page. They had
  only been reachable through the settings search. They save with the page's Save, like the other game settings.

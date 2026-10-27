## No per-frame rebuilds in the HUD (2026-10-17)
- A Razor panel rebuilds when its `BuildHash` changes. Don't hash `Time.Now`, and don't call `StateHasChanged` from
  `Tick`: either one rebuilds the panel every frame. Hash what the panel shows, rounded as it shows it. Set anything that
  moves every frame (sway, radar positions, a draining bar) in `Tick` on an `@ref`'d panel's `Style`.
- What the engine does (sbox-public's `Panel.TickInternal`): BuildHash, then the render, then the children's Tick, then
  `OnAfterTreeRender`, then this panel's Tick, all before layout. A razor `style` attribute only sets the properties it
  lists. So a style set from code survives a rebuild. A rebuild that makes new panels (a hotload) needs the "last set"
  caches reset in `OnAfterTreeRender`.
- The minimap only rebuilds when what's on the radar changes. Each icon and label is a `MinimapIconMarker` /
  `MinimapLabelMarker` (`UI/HUD/Minimap/MinimapMarkers.cs`) that places itself every frame. The transform it builds is
  the one the CSS parser made from the old style string.
- `GunsmithPanel.IsAnyOpen` and `PauseMenuPanel.IsAnyOpen` read sets kept in OnEnabled/OnDisabled, so they don't search
  the scene several times a frame for the cursor code. The cursor's 3-4 call sites a frame are left as they were.
- Rain (`RainView`): the drops, splashes and rings exist only while rain falls, and go after 2 s dry. Only the active
  share of drops is made (`_dropCover`). `RainLook.Apply` and the puddle decals only write values that changed.
  `Weather` checks `HasSky` once a second while there's no view.
- New fields reach a running match through a hotload as defaults: null lists, 0 instead of NaN. Make such lists lazily
  (`??=`).
- Compiled with dotnet, 0 errors. None of it has been seen in a match: the radar, the scope, the death cam, voices,
  ammo, the kill feed, and rain starting and stopping (a Showers match).


## HUD markers under the gun (`ViewModelMask`)
- The user saw the bomb sites' A and B markers drawn over their gun while aiming, and wants the gun on top. The
  markers are UI, which draws after the whole scene, so every `MarkerSystem` marker (bomb sites, teammates, pings) is
  masked out where the first-person gun covers the view instead.
- Every frame, `ViewModelMask` draws the viewer's viewmodel again, with its own materials, into a half-size depth
  target: the gun, its parts and the arms (`Client.Viewer.PlayerPawn.CurrentEquipment.ViewModel`). It's a CommandList
  on the main camera at `Stage.AfterTransparent`. `shaders/hc1_viewmodel_mask.shader` turns that depth into a mask
  texture (white open, black gun), and `MarkerSystem` sets it as its own `mask-image` (Luminance, 100%).
- Only surfaces that write depth cover the markers. Reticles and lens glass (`m4_optic_lens.shader`) don't, so markers
  show through a red dot's or holo's window, the iron sights' aperture and see-through magazines. A magnified optic's
  picture (3dscope) writes depth, so it hides them.
- It only runs while there are markers (`ActiveMarkers.Count > 0`), because it draws the viewmodel a second time.
- Don't draw the markers before the gun instead: the viewmodel is the overlay layer, drawn between AfterSkybox and
  AfterTransparent, and all UI (EarlyUI too) comes later. Markers drawn earlier would go through tonemapping, bloom and
  TAA.
- Checked offscreen on 2026-09-28: a ScreenPanel's grid of test squares was hidden behind an overlay-layer box and a mini
  red dot's housing, and showed through the red dot's window, edge to edge. An offscreen scene draws no UI unless its
  internal `Scene.PreRender` runs before `RenderToBitmap`.
- In the user's Ridgeback match, the mask found the AUG and the arms, and the frame drew as normal. It hasn't been seen
  in-game over a gun with markers on screen.


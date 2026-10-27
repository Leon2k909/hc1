## Hitmarker (`HitmarkerPainter`, Settings → Crosshair's hit marker)
- The user (2026-10-20): the kill hitmarker "isnt fully centered". It was a UI panel in `CrosshairHud`, while the HC1
  crosshair is drawn with the camera's HUD painter at `Screen.Size * 0.5`. UI layout snaps to whole pixels, so on an odd
  width (the editor's game view was 1905 px, centre 952.5) the two could sit a pixel apart.
- Now `CrosshairInputSystem` (Stage.FinishUpdate) calls `HitmarkerPainter.Draw` on the main camera's HUD painter every
  frame, at the crosshair's own centre and scale (`Screen.Height / 1080`), with the old CSS animation (in from 0.6x over
  30%, out to 1.2x, ease-out). Same style, colour, alpha, size, thickness, outline and duration settings.
  - The X and the diamond are `DrawLine`s, as the crosshair's arms are. `DrawRect` (and `DrawCircle`) snap their rect
    to whole pixels, so the ring and the dot are sized to a whole number of pixels whose corner already lands on one
    (`Aligned`).
  - The diamond is a turned square now: the panel's animation replaced its `rotate(45deg)`, so it had shown as a square.
  - Hidden as the panel was: HUD off, a team's win banner, the recon drone's feed. It also draws in the firing range
    and the main menu (the settings' Preview Hit), which have a camera but no `Crosshair` component.
- Checked offscreen in the editor (`HitmarkerPainter.Paint` into a throwaway scene's camera, beside crosshair-style
  lines): every style's centroid within 0.001 px of the cross's centre, round a whole pixel and between pixels. Not yet
  seen in a match.


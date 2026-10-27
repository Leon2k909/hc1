## Emblem editor (`EmblemEditor`, PROFILE → Emblem Editor)
- The canvas is `EmblemCanvas` (2026-10-05, the user: the transform sliders "shouldnt be the only thing"):
  - Press a layer to select it and drag it about.
  - Drag a corner of the selected layer's outline to scale it, from its centre.
  - The sliders follow, and a drag stays inside their ranges (position -50 to 150, scale 0.1 to 10).
- How a press is read:
  - It's tested against the top layer first, in the layer's rotated box (`EmblemViewer`'s sizes: an emoji's box is
    28 px times its scale, an icon 32 px).
  - Small layers can be picked up within 12 px of their centre.
  - A corner counts only when the press is nearer it than the centre, so the middle of a small layer still moves it.
- The canvas's children take no pointer events, so it stays the pressed panel and `HasActive` holds through the drag
  (`TheaterTimeline`'s pattern).
- The EMOJI tab scrolls as one list (`.ee-emoji-list`). Each category used to be its own shrinking, scrolling grid:
  the panel squeezed each to about a row, and the second row spilled under the next category's heading (the user's
  screenshot, 2026-10-05).
- Not compiled or checked in-game.


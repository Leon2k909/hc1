## Flip-to-side magnifiers (`GunsmithFlipMagnifier`, `Tools/flip_magnifiers.py`)
- The user aimed a magnifier and wanted T to move the magnifier away and use the front sight on its own (2026-10-12),
  as a real flip-to-side mount does. The 2x Magnifier and Mini Dot, the 2x Magnifier and Holo, and the 3x Flip
  Magnifier with the Holo or the Digital Sight (the M4's, and the MP5's 2x copies) now have an alternate sight
  (`GunsmithPart.HasAlternateSight`, the other session's T framework in `Equipment.Optics.cs`): 1x through the front
  sight, its dot drawn by `ScopeOverlay`'s reflex dot.
- `Tools/flip_magnifiers.py` splits each model in two: `<stem>_mount` (the front sight, its mount and the magnifier's
  base) on the prefab's root, and `<stem>_magnifier` (the tube, its glass and reticle) on a "Magnifier" child with a
  `GunsmithFlipMagnifier`. It patches the prefabs and the parts' alternate-sight values (from the front glass), and
  `--check` lists what's stale. Its docstring has the split rules and hinges.
- While `Equipment.IsUsingAlternateSight` holds, the child swings 90 degrees about its hinge along the bore in 0.3 s
  (the 2x ones to the gun's right, the 3x to its left), and back. It follows the mount's renderer (enabled, tint,
  layers). In the gunsmith, Theater and on the floor it stays in.
- `optic_eyepieces.py` now finds the rear glass on any renderer in the prefab; its values didn't change.
- Made with the editor closed: the new vmdls, prefabs and parts need compiling (`recompile_asset` the six .gnsmth).
  Not checked in a render or in-game: the hinges' sides and the swing, whether a cut left a hole in the 2x Mini Dot's
  base, the dot through each front sight, and that a flipped tube stays clear of the window.


## Magnified optics: eye relief and the lens picture (`OpticZoom`, `Tools/optic_eyepieces.py`)
- The user aimed the FAMAS F1's 2x Magnifier and Holo and asked if a scope really looks like that (2026-09-29). The
  eyepiece's housing filled most of the screen, with a small magnified circle inside a ring of plain glass.
  - Every M4 optic had `OpticAimOffset` x -4, red dots and scopes alike. So a magnified optic's eyepiece sat wherever
    that put its model: that magnifier's glass 2.1" from the eye, the 6x scopes' 1.2-1.6" (their eyepieces filled the
    screen), and the 3x Flip Magnifier's (x -2.5) 5.3".
  - The picture was a fixed 0.3 of the screen's height (`OpticLensDiameter`), anchored 4 in front of the eye.
- `Tools/optic_eyepieces.py` writes each magnified MWII optic's `OpticEyepiece` and `OpticEyepieceDiameter`: its rear
  glass (the model's `lens` bodygroup disc, in its `_reticle` material). It also sets `OpticAimOffset` x so the eye
  sits a real eye relief behind that glass. y and z, which line the sight up, stay. The reliefs are the longest of each
  kind's common real optics (sources in the script):
  - magnifiers 2.8" (Aimpoint's 3XMag-1);
  - fixed 3x scopes 2.6" (Vortex's Spitfire 3x);
  - digital scopes 2.56" (Pulsar's Thermion 2 60 mm);
  - 6x scopes 4" (Vortex's Razor HD 1-6x24).
  `--check` reports part files it would change. Rerun it after editing an optic's model or a relief.
- `OpticZoom` anchors the lens where the line of sight crosses that glass, and sizes the picture to the glass's diameter
  over its distance, so the picture fills the eyepiece wherever it is on screen (sway, recoil, a rail's shift).
  Optics without eyepiece data (the MP5's, the Scout 3x) keep `OpticLensDiameter` at 4.
- When the picture shows (2026-10-05, the user: aiming the 6x Precision Scope on the Uzi, "its delayed to move to the
  magnified view"):
  - It used to wait for the camera's zoom, which eases in exponentially (`CameraController`, `LerpTo` at 5/s). It came
    in from 75% to 95% of the zoom: ~0.28 to ~0.6 s after pressing aim, though the scope was at the eye after ~0.3 s
    (`ViewModel.AimTime` 0.25 s, then the aim offset's ease at 10/s).
  - Now it goes by where the scope is (`OpticZoom.LensVisibility`, the overlay's opacity). It needs the optic pointing
    along the view (full within 2 degrees, gone at 8) and the line of sight on the eyepiece's glass: full within
    `FullOnAxis` (0.35) of its radius, gone off its edge. Optics without eyepiece data go by `ViewModel.AimProgress`
    (75-95%).
  - The lens stays active while the sights come down (`ScopeBlend` is `ViewModel.AimProgress`), so the picture leaves
    with the scope instead of vanishing while it's still at the eye.
  - The optic's place in front of the eye is learned once the aim has settled for `SettleTime` (0.15 s,
    `ViewModel.IsAimSettled`), not after the zoom's 98% (~0.8 s). Until then the optic's own axis stands in for it.
  - Compiled nowhere yet (made without a compiler), and not seen in-game.
- The M4 holds an optic's origin 8.718 in front of the eye before its `OpticAimOffset` (`M4_OPTIC_DEPTH`: the 762's slot
  at its ADS pose plus its correction). The ported guns' `OpticAimCorrection`s copy that, so each relief holds on them:
  the 762, M16A4, P90 and Uzi all put a 2x's glass at the same depth. A rail's `RailOpticAimCorrection` moves the eye
  with it (the FAMAS's low rail 0.6 further back).
- Checked in software renders of the optics' OBJs from the eye (before and after), not in-game. A new `GunsmithPart`
  field only loads into a part file compiled after the code has it: `recompile_asset` the part files after the hotload.


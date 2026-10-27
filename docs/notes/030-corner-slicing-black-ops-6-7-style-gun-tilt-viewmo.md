## Corner slicing (Black Ops 6/7-style gun tilt, `ViewModel.CornerSlicing.cs`)
- Settings → Game → Corner Slicing (`GameSettings.CornerSlicing`, on by default). It's stored inverted (`plainCorners`)
  because a hotload leaves a new field at false instead of running its initialiser. The user wants Black Ops 7's: ADS
  with a wall's edge beside the sights cants the gun, sights towards the opening and its body over the wall. It must
  stay visual only, with no advantage: the view, the body, the hitboxes and the shots don't change.
- `ViewModel.Setup` rolls the whole viewmodel about the camera's forward axis (`CornerRoll`, up to 15 degrees, eased),
  which keeps the sights centred. `FindCornerLean` casts a fan of 9 level rays (±32 degrees, 400 units) from the eye:
  - An edge is a neighbouring pair where the near ray hit a wall within 110 units and the far ray went on past where
    that wall would be (`IsWallEdge`). One flat wall seen at a glancing angle doesn't count.
  - The wall's closeness and the edge's angle from the sights set the strength. Edges on both sides (a doorway) cancel.
  - Not with a flat scope ("scoped"), in third person, or looking steeply up or down.
- Checked in-game (2026-09-26, AK-105 irons on Flatgrass): a brick wall close on the left canted the gun 14.6 degrees,
  sights leaning right and the body over the wall, with the front post still in the rear notch at the screen's centre.
  A leftward cant and a magnified optic weren't checked in-game.
- `OpticZoom` measures the optic against the canted view and turns the lens camera back, so a magnified optic's picture
  stays level while the gun cants.
- The setting used to cut menu panels' corners (`Slicing.scss`, `CornerSlicing.Class`, Settings → Interface). The user
  said that was never meant to happen, so it was removed on 2026-09-26.
- `dev_corner [radius] [side]` puts you at the strongest corner nearby and logs the cant (side 1: sights lean right,
  -1 left). Aim with `dev_force_aim 1`. It samples 80 random navmesh points, so run it again if the cant it logs is
  weak: after the teleport the capsule can end up a little off the point it judged.


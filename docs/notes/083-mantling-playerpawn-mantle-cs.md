## Mantling (`PlayerPawn.Mantle.cs`)
- The user (2026-10-01): "currently i just sort of hop over larger objects". Jump while moving forward at a ledge 28-84
  over the floor you're on (mid-thigh to ~2.1 m) and you climb onto it, in place of the jump. Lower than 28 is a step or a
  jump. Holding Jump in the air catches a ledge within 84 of the current feet, capped at 112 above the floor
  (`MaxJumpMantleHeight`), unless you're falling faster than 250 u/s. The actual jump must bring the hands into reach;
  the former floor + 94 ceiling rejected Lowtide's 102-inch containers even at the jump's apex.
- `PlanMantle` finds the ledge: a body box traced `MantleReach` (20) ahead finds a wall facing you within ~53 degrees,
  then a thin probe climbs its face in 6-unit steps for solid with free space above it (so a rail or an overhang works),
  and a trace down finds the top, which must be level enough to stand on (normal z 0.7).
  - A top no deeper than 24 (`VaultMaxDepth`: walls, fences, sandbags, rails) with a floor within 160 below on the other
    side (`VaultMaxDrop`, ~4 m) is vaulted over. A deeper top, or a parapet over a long drop, is climbed onto, and the
    crouched body has to fit there. A jumping grab above the standing reach always climbs onto the top and requires
    that room; it cannot become a fast vault over a high wall.
  - The body goes over tucked: 36 high for a vault (the eye 28 down), so a vault goes through a window-sized gap, and
    48 for a climb (the eye 16 down, `MantleEyeOffset`, synced).
  - Before it starts, the whole path (up, then over, overlapping) is traced with the tucked box at 16 points. If that's
    blocked it tries straight up and then over, and if that's blocked too there's no mantle.
- The owner then moves the pawn along the path (`UpdateMantle`, smoothstepped), with the controller's velocity set to
  match. Anything that moves it more than 8 units off the path (a teleport, a death) ends it.
  - Timing: the rise takes 0.12 + 0.004h + 0.0001h^2 s for h units: 0.33 s for the lowest ledge, 0.46 s waist high,
    0.69 s chest high, 1.2 s for 84. A vault goes over at your speed, 150-310 u/s, and you carry on at that speed; a climb
    at 150, leaving at half that. A waist-high vault takes about 0.55 s, an 84 climb about 1.35 s.
    High jumping grabs use the full floor-to-ledge height for the rise's effort, bring the legs over only after the
    rise, and move over at 90. The native 102-inch container check completes its pull-up in about two seconds.
- Never climbed: people (`player`, the bots' `movement` and zombies' `enemy` boxes), doors (`MapMover.DoorTag`), glass,
  player clips (a window's), and the Ridgeback's trees and hedges (clutter bodies, by the shape's `clutter` tag).
- While mantling: no shooting or aiming (the `no_shooting` / `no_aiming` tags, and an aim already held is cancelled),
  no sprinting and no inspect. The gun swings down and to the right (`ViewModel.MantlePosition` / `MantleAngles`), the
  camera dips 6 degrees and rolls 3 in first person (`CameraController.ApplyMantleTilt`), and the crosshair's lines go,
  all eased by `MantleBlend` on every machine. Other players see the airborne pose with the body tucked (the duck from
  the eye offset): there's no climbing clip.
- Sounds (`PlayMantleSound`, broadcast): a hand on the ledge at the start (the surface's footstep at 0.6), the feet on
  the top at the end of a climb, and a vault's landing is always heard, even off a drop too short for a fall's sound.
- Native validation (2026-10-20) is in `output/mantle-reach/`: 13 collision cases and a production movement simulation
  reproduce the old failure and complete a jump onto a 102-inch container after the fix. Standing grabs, insufficient
  jumps, 114-inch high cubes, taller walls, blocked roofs, distant cover and player clips are rejected. Low cover and
  vault timings match the baseline. All 27 stair approaches still avoid mantling; both real low-ledge controls climb.
  These isolated physics checks match Lowtide's closed-container collision dimensions and preserve the editor's
  scene/play state; a first-person Lowtide playthrough is not recorded. Hold forward and Jump to try a jumping grab,
  or look at a low ledge and run `dev_mantle` for a standing check.


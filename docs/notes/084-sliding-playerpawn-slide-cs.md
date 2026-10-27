## Sliding (`PlayerPawn.Slide.cs`)
- The user asked for sliding (2026-10-13), after the Cold War speeds (see Movement speeds). Press Duck while sprinting
  on the ground: you drop onto a hip and slide on. A tap is enough; letting go of Duck doesn't end it.
- Retuned the same day to feel like Modern Warfare III (2023)'s (the user: "not fast enough", "fast to initiate,
  longer", "doesnt feel fluid yet"):
  - The drop: the eyes go down at 24/s (`SlideDropRate`; a stance change's 10), most of the way in ~0.1 s, and the gun
    eases in at 16/s (`SlideBlend`, out at 7/s).
  - The push: the sprint's speed plus 115 (`SlideBoost`), at least 340 (`SlideStartFloor`) and at most 430
    (`SlideMaxSpeed`). It needs 180 u/s over the ground (`SlideMinStartSpeed`).
  - Friction (`SlideFriction`, a crouch's is 4) starts at 0.12, holds for 0.35 s, then eases up to 1.6 over 0.7 s, so
    the slide keeps its speed early and bleeds it late. It ends under 180 (`SlideEndSpeed`, about where a sprint
    picks up) or at 1.5 s (`SlideMaxTime`). Almost no steering (`SlideAcceleration` 1.5).
  - Simulated (50 Hz, flat ground): a rifle's ~285 sprint slides off at 400, is at ~370 half a second in, and goes
    1.14 s and ~375 units (9.5 m). From 200: 340, 1.04 s, ~300 units. With no gun penalty (~304): 419, 1.16 s, ~395
    units. The first version went 345 u/s, 0.86 s and 195 units.
  - Shortened a little the same day (the user: "little bit less distance"): it went 1.32 s and ~430 units (11 m),
    with friction held 0.4 s, then up to 1.4 over 0.8 s.
  - Duck pressed again 0.15 s or more into it (`SlideCancelDelay`) cancels it: you stand straight up (the press doesn't
    crouch until Duck is let go, `_slideCancelHeld`) and, holding Run, sprint on.
  - Duck tapped or held during a moving jump slides as you land (`_slideOnLanding`, updated 2026-10-18 after the user
    reported timing-dependent failures). Running momentum (at least 180 u/s) accepts the request even after Run is
    released or crouching ends the sprint flag. Jump and Duck on the same tick queue a landing slide, including out
    of an active slide; Jump takes priority over Duck cancelling that slide. More airborne Duck presses keep the
    request. It has no airborne timeout; the old 0.25 s `SlideLandingBuffer` was already removed on 2026-10-15.
    `TrySlideOnLanding` runs immediately after controller movement, so ground contact starts the slide before the next
    tick's crouch friction. Landing during the 0.4 s cooldown keeps the request until it clears, provided enough
    momentum remains. Toggle sprint intent survives the airborne crouch. Prone, climbing, death, movement restrictions
    and slow walking clear the request; landing too slowly only crouches.
  - A toggled sprint the slide stopped picks up again within 0.5 s of it ending (`ResumeSprintAfterSlide`, in
    `GetWantsToSprint`); Run pressed during the slide takes that back.
  - Another can start 0.4 s after one ends (`SlideCooldown`; it was 0.8).
- Slopes: on the ground it gets half of gravity's pull along the slope (`ApplySlideSlope`, `SlideSlopeHelp`), so
  downhill carries it further and uphill stops it sooner.
- What ends it:
  - Jump: a jump that keeps the speed. Prone: down flat. Duck again: the cancel above.
  - Leaving the ground, slowing under 180, or the time running out.
  - Death, a knockdown, mantling, the drone's tablet, planting, being downed.
  It comes up crouched while Duck is held, else standing.
- While sliding:
  - The eye is at -24 (`SlideEyeOffset`; a crouch's -16), and `IsCrouching` holds for movement. Footsteps are silent
    and the movement capsule stays crouched.
  - The gun dips a little back, in and down (`ViewModel.SlidePosition`), less as it's aimed, eased by `SlideBlend`,
    with no walk bob. No inspect.
  - Nothing tilts: the user had the gun's 14-degree cant and the camera's 5-degree roll taken out (2026-10-13, "remove
    the tilt").
  - It ends the sprint, so the gun can fire 0.25 s after the slide starts (the sprint-out time), or at once aimed.
- A crouch now stops a sprint (`!IsCrouching` in `CanSprint`). Before, crouch and sprint could be held together.
- Third-person slide (`ThirdPersonSlidePose`, 2026-10-13): a procedural pose applied after animation by
  `PlayerSlideAnimationSystem`, using `SlideBlend` on owners and proxies. Hips lower onto the right side, the right
  leg extends forwards and the left tucks outwards. Two-bone IK preserves thigh/shin lengths and keeps ankles above
  the floor during the transition; weapon and look animations stay active. Bone GameObjects carry the gun and
  holstered equipment with the pose, and clothing is merged again. Only the main body receives it; prone, knockdown,
  climbing and ragdolls take precedence. The main body's locomotion inputs fade out during a slide, so it no longer
  plays a crouch run. Supports the human's ankle_L/R and the legacy soldier's l_foot/r_foot skeletons.
- A scrape sound is still missing. The drop plays the floor's landing sound at 0.7 (`PlaySlideSound`, broadcast).
- `dev_slide` sets your speed to a rifle's sprint where you're looking and slides, logging the speed or why not.
- Compiled with dotnet; `Tools/SlideChecks` checks the production pose's limb lengths, transition continuity and
  floor clearance across yaw, scale and stance, including unreachable IK targets. Not yet checked in-game: the
  editor stalled while this was added.
- Jump/landing regression checks (2026-10-18): `Tools/SlideChecks/JumpLandingChecks.cs.txt` runs the production
  `BuildInput`, acceleration and movement against collision in an isolated native-engine scene, restoring input,
  time and sprint settings. All 189 jump/slide simulations and 7,287 assertions passed at 30/50/120 Hz, covering
  takeoff/apex/landing timing, taps/holds/repeated presses, released Run, hold/toggle sprint, jump fatigue,
  slide-jump-slide chains, cooldown retention, movement guards and grounded slide cancellation. Native compilation
  passed with zero errors. Report: `output/jump-slide-validation/checks.json`. Match feel still needs the user's check.


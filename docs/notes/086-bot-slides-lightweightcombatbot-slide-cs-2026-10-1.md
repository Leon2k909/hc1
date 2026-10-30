## Bot slides (`LightweightCombatBot.Slide.cs`, 2026-10-14)
- Bots occasionally slide after at least 0.3 s above 225 u/s, on a clear, straight route with at least 300 units ahead.
  Floor and body sweeps exclude stairs, drops, walls and other soldiers. Rushers and flankers do it more often;
  anchors and marksmen rarely do. Each decision is spaced 1.2-2.4 s apart, with an 8-16 s cooldown after a slide.
- The push is the player's +115 (340-430 u/s), with the same 0.12-to-1.6 speed decay and 1.5 s maximum. Navigation
  keeps handling position and avoidance. Slides stop early for a blockage or missing floor, then restore the previous
  route, speed and acceleration. Combat freeze and death cancel them. A slide ends sprinting, retaining the 0.25 s
  sprint-out before firing; the body faces its travel direction while the eyes/gun can track a target.
- Host-synced `IsSliding` drives `SlideBlend` on every machine. Eyes and collision height lower to 40. Locomotion fades
  out and `ThirdPersonSlidePose` runs before the weapon mount and support arm; bot LOD avoids creating bone objects.
  Native live matches on Lowtide and CerroBlanco showed natural slides around 350 units long and the gun still in hand.
  Ten native state checks covered entry, recovery, cooldown, collider/eye height, navigation restoration and combat
  freeze. The existing 45,816 slide geometry checks pass. No multiplayer client was attached for this validation.
- The user: "bots look weird when they slide" (2026-10-16). Aiming while sliding, `FinishWeaponPose` shouldered the
  gun at the logical eye (`EyePosition`, `SlideEye` 40 up), but the slide pose puts the hips 13 up and leans the body
  back, so the visible head is several units lower and the gun would hang over and ahead of the face. It now sights at
  the posed right eye (`PosedEye`, the `eye_R` bone after the pose) and blends the shouldered hand in by `SlideBlend`,
  so the gun comes up with the drop instead of snapping. Prone keeps `EyePosition` and full weight. Compiled with dotnet
  only (the editor was closed); not yet rendered or seen in a match, so whether this was what looked weird is unconfirmed.


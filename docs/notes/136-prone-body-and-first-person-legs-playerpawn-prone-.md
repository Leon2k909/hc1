## Prone body and first-person legs (`PlayerPawn.Prone.cs`, `ThirdPersonPronePose`, 2026-10-16)
- The user: "when i prone i should be able to see my legs like cod", with a picture of Black Ops 6's supine prone
  (lying on the back, aiming over the legs). Players had no lying pose: prone was the crouch clip with the eyes at -40,
  and the first-person body was hidden.
- The body lies along `ProneYaw` (feet to head, `[Sync]`, owner-set). The view turns freely within `ProneFreeArc` (45)
  of it; past that the body pivots after it at `ProneTurnRate` (90/s); a look further round than `RollOverAngle` (110,
  a quick look behind) rolls it onto its back (`IsSupine`, `[Sync]`), looking along the body at the feet. Turning back
  past 70 rolls it face down again. `ProneBlend` follows the eyes' stance rate and `SupineBlend` takes `RollTime` (0.4 s),
  on every machine.
- The camera stays at the lying head: `PlaceHeadForProne` moves the `Head` object (rest 9,0,60) along `ProneYaw`
  instead of the view, so a roll leaves the head where it was. `ProneEyeTarget` is where the eyes end up.
- `ThirdPersonPronePose` (applied in `PlayerSlideAnimationSystem`, to the body and the first-person body): pelvis and
  legs tipped 87 degrees along the heading and spun about their length for the back; the chest propped up (bisected)
  until, with the eyes at the camera, the pelvis is 5.5 over the floor; head and arms keep their animated aim, shifted
  to the lying neck and shoulders; the legs laid out straight by two-bone IK, knees to the floor face down and up on the
  back, face-down toes turned back. `ShoulderGun` then brings the third-person gun up to the eye with the bots' hand IK
  (pistols held out, none while reloading). Locomotion and duck fade out by `ProneBlend`, so crawling has no leg motion.
- The first-person legs show once `ProneBlend` reaches `FirstPersonLegsBlend` (0.9). On the back they lie ahead of the
  camera at the bottom of the view.
- The movement box is still the standing 32x32 square, so the lying legs can go into walls: behind you face down, ahead
  of you on your back.
- Checked offscreen on 2026-10-16 (an isolated scene in the editor): face down lies under the camera, the eyes within
  1.2 of it, and looking back along the body the legs fill the bottom of the view. The on-the-back render isn't valid:
  a turned root there kept its old animation frame, so render it with the root unturned and `proneYaw` 180. The leg IK
  and `ShoulderGun` came after: compiled with dotnet only (the editor closed), not yet rendered or seen in a match, nor
  on a second machine. In such a render, give the test body `CreateBoneObjects` or the gun won't follow the hand.


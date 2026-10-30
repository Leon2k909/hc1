## Third-person sprint carry (`ThirdPersonSprintPose`, 2026-10-14)
- The shared `ThirdPersonSprintPose` runs after animation for bots (`FinishWeaponPose`) and players
  (`PlayerSprintAnimationSystem`). The original fixed weapon-origin pose was rejected visually: stocks floated across
  the shoulder, grips were too low, and inherited elbows made the arms awkward. The replacement anchors each gun's
  actual buttstock pad at the upper right chest (`6, rightShoulder.y + 1.5, 1` in the animated chest frame).
  `BotWeaponPose.ButtstockContact` uses the active stock meshes, excluding hidden gunsmith stocks; combined meshes
  use the rear model bound and a pad centre 1.5 units below the bore.
- The carry retains the animated torso lean and bob but follows only 25% of shoulder yaw, avoiding a sideways swing
  every other step. Its base angles are `20,50,-10`; it rotates farther about the pad only when a grip exceeds an arm's
  reach, refining the angle to avoid five-degree jumps. Both arms use downward anatomical elbow poles and retain
  their original lengths. Carry yaw stays within 75 degrees of the chest even while looking sideways. The rendered
  skeleton's root supplies the facing so the carry and bone transforms use the same frame. Intermediate poses fit
  both grips within reach and move the stock around the torso; `Fit` uses the pad contact and shoulder-relative front
  plane for this carry, with side clearance for long stocks. The right-hand socket's height is
  calibrated against the gun's bore and index knuckle; the native M4 and imported rifles have different model origins.
- The carry blends in over 0.18 s and out over 0.22 s, with eased arm targets. Players use synced `IsSprinting`, excluding
  aiming; bots use their smoothed, replicated ground speed over 190, since `NavMeshAgent.Velocity` is zero on clients.
  Reloads, crouch, prone, slides and other player stance poses have priority. Pistols, melee and the drone tablet are excluded.
- The gripping hand carries the gun, the support hand follows its actual grip, and arm bone objects and clothing follow
  the final pose. Players retain their authored `HoldGameObject` offset. The gun's temporary grip correction is reset
  before each frame and restored on cancellation, stance/reload changes, weapon changes, and the final fade frame.
- Replacement checked in native 26.10.13 fixtures: 3,744 poses across all 24 bot guns (full running cycles, fade in/out,
  and looking 45 degrees to each side), and 12 player activation/state checks including migrated sockets and mount
  restoration. Hand/mount errors and arm-length changes stay below 0.0001 units; the stock-pad gap stays below
  0.001 units. Both project compilers succeed. M4/AUG stride and transition renders, a nine-weapon gallery including
  the Vepr-12, and the replacement reports are in `output/third-person-sprint/revision/`; older outputs in
  the parent folder describe the rejected pose and are not evidence for the replacement.


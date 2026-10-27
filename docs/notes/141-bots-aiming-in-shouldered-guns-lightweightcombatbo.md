## Bots aiming in (shouldered guns, `LightweightCombatBot`)
- The citizen graph's rifle pose only carries a gun at the hip (and lowers it after 1.1 s stood still), and it has no
  aiming clip, so bots never looked like they aimed (the user's report, 2026-09-29).
- In a fight the host sets `IsAimingIn` (synced): from seeing an enemy until 2 s after losing sight of them, and not
  while reloading. Every machine then shoulders the gun in `UpdateAnimation`. It doesn't while the reload clip plays
  or when the bot moves faster than 190 u/s: at a sprint (see "Sprinting and awareness" above; its walk is under 190).
  - The right hand's IK (`ik.hand_right.*`, `ShoulderedHandIk`) holds the gun level along the aim, with the right
    eye (`eye_R_forward`) on its sight line.
  - `EyeOnGun` takes that line from the model's bounds: half a unit under the top of the gun, clamped to 1.5-5 over
    the bore. It sits `ButtToEye` (8) in front of the butt.
  - `aim_body` goes to weight 1, and `aim_head` drops 20 degrees (`ShoulderedHeadDrop`), so the head comes down
    onto the stock while the eyes stay on the target.
  - The left hand follows the gun through its usual IK.
  - A cheek weld: after animation the head cants 20 degrees, right ear down (`ShoulderedHeadCant`, `BotHeadCant`,
    from `FinishWeaponPose`).
    - Upright, with the right eye on the gun's centreline, the face went through the stock and the receiver. The user
      saw a bot's nose and cheek in its FAMAS's carry handle (2026-10-12).
    - It turns the head's bones about the line of sight through the right eye, so the eye stays on the sights and the
      IK is unchanged. The jaw swings off the stock, and the neck turns to meet the head. The helmet and the other
      garments merged onto the body follow it (`MergeBones`).
    - It scales with the head drop, so it comes and goes with the shoulder. It's skipped where nobody would see it
      (`BotSystem.ShouldShowEffect`: within 800 of the viewer, or big enough on screen).
- `hc1_bot_grip_preview [gun] [dress] [headDrop] [buttToEye] [side] [pitch] [yaw] [speed] [crouch] [reloadTime] [cant]`
  renders the bot's body holding each gun in its pool into `output/bot-grip/<gun>.png`: carried and shouldered, from
  its left, front and right, then two rows of close-ups round the shouldered head.
  - It logs how far each hand misses its IK target, where the butt sits against the right shoulder, and the face's
    vertices inside the gun (`face inside=`). That count takes in concave spaces round the gun, such as under a carry
    handle, so judge by the close-ups.
  - headDrop, buttToEye, side and cant try other shouldered poses.
  - On 2026-10-12 the dressed renders posed the clothes with the body.
- Tuned 2026-09-29 with those renders:
  - A longer `ButtToEye` (9, head upright) poked the stock out behind the head.
  - A shorter one (5-7), or the gun set right of the eye, put the Kastovs' and the RPK's handguards out of the left
    hand's reach.
  - Now every gun's butt sits at the shoulder. The hands miss by 0.03-0.05, except the AK-105 (0.59) and the RPK
    (0.78), whose hands still sit on the handguard.
  - Not yet seen in a match.
- The cant checked in the whole pool's renders on 2026-10-12, against the same renders with `cant` 0:
  - The face's vertices inside the gun went down on every gun: the AUG from 5199 to 1386, the MP5 5468 to 1950, the
    M4A1 3958 to 1026, the FAL 5992 to 3130, the L85A2 3990 to 662, the RPK 5233 to 2607, the HK416 2130 to 297.
  - On the FAMAS the face sits behind and left of the carry handle's rear post. The headset's mic boom crosses the
    post, and its ear cup rests on the stock. Some guns' receivers still touch the chin a little (the FAL's).
  - The left hand missed by 0.00 on every gun, and the right hand by the same with the cant on and off.
  - The right hand's IK misses by more than the tuning above found, on the AK-pattern guns most: the AK-105 4.45, the
    AK-74M 4.54, the RPK 4.66, the FAL 3.71, the Vityaz 3.22, the 74u 3.04, the Bizon 2.97, the Kastov 762 2.63.
    `BotWeaponPose` then fits the gun to the hand (its mount error is 0). That came from a change after 2026-09-29,
    not the cant. Whether it shows in a match hasn't been looked at.
  - Not yet seen in a match.


## Third-person left hand (world models' `LeftHandIK`, players and bots)
- `rigged_human.vanmgrph` had no IK, so the world models' `LeftHandIK` points did nothing. The left hand followed the
  rifle clip and missed short handguards (the user saw bots' hands off the Kastov-74u). The graph now ends in a
  two-bone IK on the left arm (`ik.hand_left.enabled/position/rotation`, faded over 0.3 s). Its chain, `left_arm_IK`,
  comes into the three player vmdls from `models/player/prefabs_v2/prefab_ikdata.vmdl_prefab`. The chain's default
  target bone has to exist (`l_hand`).
- The IK matches the target's rotation. `LeftHandIK` is where the wrist (the `l_hand` bone) goes and how the hand
  turns, in world-model space: position alone left the hand hanging under the handguard. Players get it through
  `Equipment.UpdateIkHands` (the body's AnimationHelpers), and bots through `LightweightCombatBot.UpdateLeftHandIk`.
  Players turn it off for the whole reload, so the reload clip can take the hand to the magazine. Bots turn it off only
  while that clip plays (1.67 s, `ReloadClipSeconds`): their reloads run 1.7-8 s, and for the rest of one the hand hung
  off the gun (the user saw bots' front hands off their guns, 2026-09-29).
- Every long gun but the AUG (below) uses the same rotation (`-0.6308,0.3714,-0.448,0.5133`): the rifle clip's
  cupped hand, turned 20 degrees so the fingers wrap the handguard's right side. The wrist sits:
  - 3.5 left of the handguard's right side;
  - 1.19 under its bottom;
  - about 3.9 behind where the index finger should reach.
- The Kastov family's points come from `kastov_prefabs.py` (`world_left_hand`, `WORLD_LEFT_HAND_ROTATION`).
- The Steyr AUG's left hand holds its vertical foregrip, not a handguard, so it has its own rotation
  (`Prefabs.world_left_hand_rotation`, `0.0176,-0.1819,-0.0435,0.9822`) at `0.25,1.56,0.01`. Both come from fitting
  the player's hand (the wrist, four knuckles and the thumb's base, in the rifle clip) onto the first-person hand on
  the grip, then 1 further back, so the clip's curled fingers wrap the grip's front. With the shared rotation (at
  `1.2,2.6,1.6`) the hand held the barrel. Checked 2026-09-28 in offscreen renders of both teams' models: the IK
  reaches the point exactly, the fingers round the grip's front and the thumb round its back. Not checked in a match.
- Checked 2026-09-27 in offscreen renders of both teams' models holding all eleven long guns (the Spaghelli in its
  Shotgun hold type), but not in a match. The Vepr-12 came later: its point (`6.9,2.8,1.84`, at the handguard's front,
  by the rules above) hasn't been rendered. It holds the Rifle hold type. Nor has the M16A4's (`5.7,2.19,2.68`, the
  middle of the handguard, where the first-person hand holds it), the P90's (`-2.5,2.84,-1.55`, under the frame's
  front, where the first-person hand holds it), the MP7A1's (`-0.9,2.29,2.47`, under the receiver's front, where
  the first-person hand holds it), the Uzi's (`-0.13,2.59,1.8`, under the lower receiver's front, where the
  first-person hand holds it), the MCX's (`4.2,2.735,2.49`, under the handguard where the first-person hand holds
  it, by the rules above), the L85A2's (`-0.62,1.76,1.33`, where the first-person hand holds the handguard), the
  HK416's (`4.97,2.47,2.57`, where the first-person hand holds the handguard, by the rules above), the AK-12's
  (`6.9,2.55,2.23`, the same, by the rules above), which the AK-15 shares, the AK-74M's (`6.9,2.7,2.27`, the
  same), the MCX-SPEAR's (`4.2,2.574,2.702`, where the first-person hand holds the handguard, by the rules
  above), the M16A2's (`5.7,2.23,2.21`, on its round handguard, the same) or the RPK-16's (`6.9,2.5,2.03`, the same). The FAL's (`6.4,2.37,2.16`, where the first-person hand holds the handguard) was
  rendered on both teams' models on 2026-09-28: the IK reaches it exactly, with the thumb along the handguard's left
  side and the fingers round its right.
- Pistols, knives and grenades have no `LeftHandIK`, so the IK stays off for them.
- A fitted foregrip doesn't move the hand, so the hand and the grip overlap.


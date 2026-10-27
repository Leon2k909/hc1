## Zombie animations (NMRIH mocap and a made walk, on the citizen skeleton)
- A zombie is an invisible driver with the zombie mesh bone-merged onto it (`SpawnZombie`). The driver is
  `models/zombie/zombie_driver.vmdl`: the citizen's body, physics, hitboxes and constraints (its prefabs) plus No More
  Room in Hell's zombie clips, with no animgraph. `ZombieAI.UpdateSequence` plays them as crossfaded sequences from the
  `ZombieClips` table. If the driver won't load, zombies fall back to the citizen and its human animgraph.
- `Tools/zombie_anims.py` writes the clips, the vmdl and `Code/NPCs/Zombies/ZombieClips.cs`. Its docstring covers the
  sources (GMod addons 3255961963 / 3255991053 decompiled with Crowbar, the citizen skeleton from a Source2Viewer dump)
  and the retarget. The zombie mesh is skinned mostly to twist/helper bones, so the clips bake those too.
- Clips: idle, `walk_a` (70 u/s, made by `Tools/zombie_walk.py`, below), run (188.7 u/s) and six attacks. NMRIH's
  shambles (walk1-10) aren't used: they're 10-33 u/s, and hold the arms out, lurch, flail, limp or shuffle.
- The walk was the classic zombie's a_WalkN until 2026-10-01: a crouched waddle with the hips 1-5" low, the feet 19"
  apart and the arms up with clawed hands. Its 17" steps covered only 31.8 u/s against the Walkers' 70 (the user: "their
  animation is too fast"), and lengthening them by IK (`Clip.stride` 1.5, 47.8 u/s) sank the hips 3" more. The user
  then saw zombies in a deep, wide squat with raised arms and claws: "it feels like we're exaggerating what a zombie
  would look like". Next it was walk7, NMRIH's one upright shamble, with its legs replaced by IK'd heel-to-toe steps
  twice as long (65.4 u/s). The user: "nah they walk a bit weird". Its knees snapped from bent to straight in a frame
  at heel strike, and the source's uneven timing showed through.
- So the walk is made, not ported (`Tools/zombie_walk.py`, 2026-10-01; `zombie_anims.py` writes it as `walk_a`). Its
  docstring has the reasoning, and `Walk` every figure:
  - One stride of 26 frames on the citizen's own upright posture: 70 u/s at ~138 steps a minute, 0.77 m steps, a
    person's brisk walk. A Walker plays it at 1x.
  - The upper body: the pelvis turns, lists and tilts, the chest turns against it and leans 4 degrees, and the head
    holds its gaze. The arms hang just clear of the sides and swing 15 degrees each way opposite the legs, the elbows
    bent 18 degrees and more as the arm comes forward, with relaxed hands.
  - The legs follow a person's gait curves at a brisk pace (Winter's and Perry's knee, thigh and heel-rise angles:
    `STANCE_KNEE`, `HEEL_RISE`, `SWING_KNEE`, `SWING_THIGH`). Each foot lands heel first with the toes 15 degrees up,
    rolls flat, lifts its heel about the ball and leaves over the toes' tips, pitched ~70 degrees. The feet are 6"
    apart with the toes turned out 7 degrees. A planted foot slides back at exactly 70 u/s.
  - The hips go as high as the stance legs let them: a linear programme over the loop (`lp_heights`) keeps each stance
    knee bent at least 5 degrees and near its curve's bend, the hips' height accelerating within bounds and its jerk
    penalised. They bob 2" (5 cm).
  - Late in the stance the trailing heel rises further than its curve as the knee needs (`Leg.pitch_limits`), a
    push-off, so that leg doesn't hold the hips down.
  - The swing leaves the stance at its rates and follows the knee's and thigh's curves. The knee is straightest just
    before heel strike and the thigh swings back into it (swing-leg retraction), so the foot comes down slowing.
  - The knees: 5 degrees at heel strike, up to 17 as the weight comes on, ~5 by mid-stance and 58 at most in the
    swing. The swinging foot clears the floor by 0.2" at its lowest. `python Tools/zombie_walk.py` prints it frame by
    frame.
  - ZombieAI no longer plays each zombie's walk at its own rate (0.93-1.07x), which made the feet slide. Each still
    starts at its own point in the cycle.
  - Checked in Blender renders of the zombie mesh skinned on it (side and front, and heel strike close up), against
    the walk7 version. Not yet seen in the engine: the editor recompiles `zombie_driver.vmdl` from the new DMX by
    itself (register it if it misses it, see the Kastov pipeline notes).
- The ported clips were toned down to a person's (2026-10-01):
  - `Clip.arms` keeps that share of the source's arm pose and lets the rest hang like the idle's, keeping the swing
    about it (`relax`, times `Clip.swing`). `Clip.hands` keeps that share of the source's wrists and fingers, and the
    rest is a relaxed hand (`RELAXED_*`: the wrist bent a little towards the palm, the fingers lightly curled).
  - `Clip.lean` keeps that share of the trunk's forward lean from the citizen's upright rest (the pelvis to the neck,
    seen from the side), and `straighten` bends spine_0-2 equally to take the rest out.
  - Per clip: the run keeps 0.6 of its arms and swing (it flung them to shoulder height), 0.5 of its hands and 0.55 of its lean (21-34
    degrees, now 11-18; a runner at its 4.8 m/s leans ~10-15). The idle keeps 0.25 of its hands. The attacks keep their
    swings, with the hands half way to relaxed.
  - Checked in Blender renders of the zombie mesh skinned on the new clips (side and front, every clip, and the hands
    close up).
- Hands and fingers are posed from where the source's knuckles and finger joints are (`HANDS`, `FINGERS`, `TIPS`),
  not from rotation changes. The NMRIH-made clips (idle, run, attacks A and C) use NMRIH's own skeleton, whose
  hand bone is rolled ~90 degrees from the classic zombie's reference pose, which twisted the palms sideways and the
  wrists by up to 140 degrees. Attacks B, D, E and F are on the classic skeleton (claws curled ~75 degrees per joint).
- Elbows are hinges. The ValveBiped (a Max Biped) rolls its forearm with the hand, which wrung the citizen's elbows, so
  the forearms keep no roll of their own (`HINGES`) and the hand's turn goes to the forearm twist bones. In game the
  citizen's constraints recompute those from the hand (twist0 none of it, twist1 ~67%). The upper arms' roll matches
  the elbows' bend axes (`ROLLS`). The run bends its forearms up to 60 degrees off that hinge, so each frame the upper
  arm also rolls to bring its forearm into the bend plane (`ELBOWS`, faded in over `ELBOW_LOOSE`).
- The forearms turn the hands only as far as a person's can (the user: "the zombies hands are like backwards",
  "twisted"). `forearm_turn` measures the turn from the elbow's hinge (0 = palm fully towards the biceps, 180 = fully
  away; the citizen rests at ~102). Each clip keeps it in `Clip.turn` (5-170), and a hand past it turns back through
  the range at `FOREARM_TURN_RATE` at most. The old walk (a_WalkN) and attacks B, D, E and F hold their claws palm up
  (0-40) with the wrists bent ~60 degrees, which on a person's hands read as bent back towards the zombie, so they use `CLAW_TURN`
  (100-170): palm down, the bent wrists droop. Attack E's right hand spins a whole turn, and the forearm used to roll
  at the elbow to follow it (`WRIST_TWIST`, now gone).
- That turn didn't fix it (the user, 2026-10-01: "i keep asking for this to be fixed but it never gets changed").
  The hand was turned about its own length, which kept each claw pointing where the source pointed it, so a palm-down
  claw's 60-degree wrist bend became a sideways bend at the wrist, up to 60 degrees where a person's goes 20-30. The
  classic attacks also held clenched fists bent back at the belly.
  - Now the forearm turns the whole hand, bend and all.
  - `limit_wrist` keeps the wrist to a relaxed hand's range: 45 degrees flexion, 35 extension, 20 towards the little
    finger and 12 towards the thumb (`WRIST_*`, soft limits).
  - Each finger joint curls at most `FINGER_BEND` (45 degrees) past the citizen's relaxed pose: a loose claw, never a
    tight fist.
  - The worst wrist went from ~60 degrees sideways to ~22, and the fingers' total curl from 177-187 degrees to at
    most 138.
- The "checked in-game 2026-09-26" captures (a driver and body posed out of sight with `Sequence.Time`, playback rate
  0) showed whole bodies, too small to judge the hands. On 2026-10-01 the hands were checked in Blender close-ups of the
  zombie mesh skinned on the clips. The editor recompiled `zombie_driver.vmdl_c` by itself, and its clips matched the
  script to 0.01 degrees (Source2Viewer-CLI's glTF export with `--gltf_mesh_list nomesh`, after stripping the
  vmdl_c's GUID block, which it can't read). Not yet seen in a match.
- The run pumped its left fist up in front of the face. That's the arm swing, not the wrist; its swing is now 0.6 of
  the source's.
- The run's side-to-side sway is cut down (`Clip.sway`, 0.6; the user said the old a_WalkN's full sway "looks like
  they're having a dance"). `damp_sway` scales the hips' and spine's roll and yaw, and the hips' sideways shift, about
  their loop average. The arms turn with the chest. A clip can also narrow its feet (`Clip.stance`, through
  `plant_leg`).
- The attacks start part-way in, so the swing's furthest reach (`ZombieClip.Hit`) lands at `AttackWindup`.
  `SwingCount` is synced, so every client picks the same attack.
- Headshots go by the driver's head bone height (bullets stop on the capsule), not the renderer bounds.


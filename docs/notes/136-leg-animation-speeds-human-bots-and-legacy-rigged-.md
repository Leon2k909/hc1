## Leg animation speeds (human bots and legacy `rigged_human.vanmgrph`)
- Current human bots use `animgraphs/human_bot.vanmgrph` (2026-10-13, the user: bots' legs look like the animation plays
  too fast). It copies the installed 26.10.13 human graph, retaining its engine subgraphs. Only the minimums of the four
  `_human_{walk,run,crouch,sprint}_rate_per_inch` parameters differ: zero instead of their fixed calibration defaults.
  The engine graph fixes both minimum and maximum to the default, so writing a lower rate there silently clamps it back.
- `LightweightCombatBot.UpdateHumanGaitRates` caches those defaults per graph, then limits each rate times actual
  ground speed with `GaitRateLimit`: 1.1 walking, easing up to 1.25 at a sprint (2026-10-14). Slow movement keeps the authored proportional rate and restores it after slowing
  down. True move/wish velocities still select direction and gait. Renderer playback stays 1, preserving weapon and
  look timing. Install the bot graph before setting movement inputs: changing a renderer's graph clears its parameters.
- Checked in the native engine: 23 checks across 0-600 u/s, plus actual animated foot samples and rendered standing,
  strafing, sprinting and crouching poses (`output/bots/gait`). At 180 u/s, a strafe's left-foot cycles fell from 25 to 15
  over ten seconds (about 40% slower); slow walking and crouching retained their cadence. Live Railhead bots use the new
  graph and cap. Code and graph compile cleanly. When refreshing this copy after an engine update, preserve the four
  open parameter ranges and recheck the lower-body cycles.
- Faster strides (2026-10-14, the user: bots don't run properly at the new speed): `BotStridePose` runs after animation,
  before the weapon is fitted. Above 90 u/s it eases the stride up to 1.5 at 270; only the travel direction is stretched.
  A small hip drop and two-bone IK preserve thigh/shin lengths. Targets are clamped in the floor plane first, so the
  boots retain their animated height even when a longer step is out of reach. Clothing is merged again; the gun follows
  the resulting hand. Slow movement, crouching, prone and slides retain their own poses. Pose work is culled below
  16 screen pixels outside 1200 units. Movement sampling now responds at 20/s and discards teleport velocity.
  Native live samples showed about 40% more planted-foot travel; the live slide's weapon mount error was below 0.001 units.
  `output/bots/movement` contains the preview, native measurements and slide checks; limb lengths and ankle heights
  were checked across the animated cycle. This reduces foot drift within the rig's available reach; it is not foot locking.
- The legacy graph below is still used by other models; its bot cadence cap also follows `GaitRateLimit`.
- The lower-body Blend2Ds ("Stood Lower Body", "Crouched Lower Body"; X = move_y, right, Y = move_x, forward) put each
  clip at the velocity its planted feet carry the body: walks ~33 u/s, jogs 93 sideways, 103 ahead, 91 back and
  81,90 / -65,86 / 62,-71 / -67,-62 diagonally, the sprint 178, the crouch walks 31-39. They used to sit at 60/150/200
  (crouch 50/75), 1.4-2.5x faster than they step, so the feet slid: a bot strafing at 126 u/s stepped like one at ~70
  (the user: bots "glide along the floor when strafing").
- Past the outer ring (the jogs, and the sprint ahead) the blend holds the ring's clips, and the float param
  `move_rate` plays them faster. It's a CSpeedScaleAnimNode ("Move Rate") between the grounded state and the
  stood/crouched state machine, so only the legs speed up; default 1. Bots set it in `LightweightCombatBot.UpdateAnimation`
  to the square root of speed over `RingReach`, capped at 1.1 walking / 1.25 sprinting, with move_x/move_y clamped to the ring.
  `BotStridePose` then lengthens the steps within the rig's reach. The old full speed-up (the strafe's jog at 1.36x, the hunting
  sprint at 1.29x: 220-260 steps a minute) kept the feet planted but looked like the bots ran faster than they moved
  (the user's report): a runner goes faster mostly by lengthening the stride, which the clips can't.
  `StoodClipRing` / `CrouchedClipRing` copy the graph's ring: change them together.
- `BotStridePose` supplies bounded stride warping outside the graph. `CFootLockAnimNode` could pin
  planted feet, but the player models define no feet or leg IK chains (only `left_arm_IK`).
- Players don't set `move_rate` yet, so a player past the ring (a rifle's ~181 walk sideways, the ~285-304 sprint, a
  ~110 crouch, since the faster gaits of 2026-10-13) slides, more than before. Inside the ring their legs match better than they did.
- Bots animate from their smoothed movement (`UpdateMoveVelocity`), not `Agent.Velocity`, which is zero on clients: in
  multiplayer every bot glided on idle legs there.
- Between the walks and the jogs the blend still under-steps ~15%: its cycles are synced, and a walk cycle (1.33 s) is
  nearly twice a jog's (0.73 s).
- Measured from the FBXs in `Assets/models/animations/temp_import/unarmed` (headless Blender, 1 m = 39.37 u, which
  matches the model's `ScaleAndMirror` 0.3937 on centimetres): the planted toe against the pelvis, three ways that agreed
  within ~10%, and against the model root (the clips are in place), within 2% of the pelvis figures. walk_E shuffles, so
  only the stroke between its extremes finds its ~33. s&box imports each FBX's take (AnimationStack LocalStart..LocalStop),
  not Blender's action range, which can run on with frozen frames (walk_W: 101 frames for a 41-frame take).
- The legacy graph's original foot-speed calibration has not yet been checked in-game.


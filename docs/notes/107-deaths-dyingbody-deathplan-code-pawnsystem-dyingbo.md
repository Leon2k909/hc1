## Deaths (`DyingBody`, `DeathPlan`, `Code/PawnSystem/DyingBody.cs`)
- The user asked for "more variance in the way people die", some "slowly" dropping, with "hyper realism". Every death
  used to be a limp ragdoll at once, shoved by 5-20 times the damage (players) or 50 times the force (bots) on every
  part.
- `DeathPlan.Choose` picks how the body goes down from the killing hit and how the victim stood:
  - Limp at once (`Drop`): head, neck and spine hits (the brain, brain stem or upper spine), blasts, falls, and anyone
    prone, knocked down or in the air. Also 30% of chest hits, 10% of belly hits and 40% of hits with no hit location.
  - `Buckle` (0.55-0.9 s): the knees give and the body folds forward (60%) or to a side. Most chest hits, half of
    melee and arm hits.
  - `Stagger` (0.8-1.2 s): someone moving faster than 120 u/s carries on the way they were going, then goes down. A
    buckle on the move turns into one 40% of the time.
  - `Slump` (1.6-2.6 s): sinks to the knees, head dropping, then slumps over. Most belly hits, some chest, arm and leg
    hits; burns and the gas zone always (2.2-3.2 s).
  - `SitBack` (1.1-1.6 s): the hips go back and they sit, then fall backwards. A quarter of belly hits, standing still.
  - `LegGives` (0.8-1.3 s): the shot leg folds at once and they go down on that side. 65% of leg hits.
  - Crouched: no stagger or sitting back, and 30% quicker.
- It's the same on every machine: the dice are a hash of the victim's id and where the hit landed (a Guid's hash is
  its bits; never a string's). For players the host picks the plan and sends it with `CreateRagdoll`'s RPC; for bots
  every machine picks it from the kill it was sent, with its own smoothed `_moveVelocity`.
- `DyingBody` does it all at the velocity level, so it doesn't depend on the physics' torque units:
  - The body keeps the victim's velocity. The bullet jolts only the part it hit (1.2x the damage, 30-120 u/s along the
    shot); a blast throws every part (3x the damage, 120-450 u/s, a little upward). A bullet doesn't knock anyone over.
  - Weight: `GravityScale` is eased back in from 1 less the share the legs still hold, so the body sinks.
  - Muscle tone: each joint's bend speed relative to its parent is damped, harder while there's tone. The arms go first
    (the gun falls), then the legs, then the back and neck. Regions come from the bodies' bone names: the player
    models' thighs are `l_hip` / `r_hip`, the citizen's `leg_upper_*`.
  - Balance: the chest is held over the hips (a 1.5 Hz critically damped spring), easing out 16 units toward the way
    it'll go over, so the body sinks upright and then topples that way instead of tipping stiff like a plank.
  - While the body's still light its feet grip the floor (its sliding is damped); a stagger's hardly, so it runs on.
  - At the end, gravity is put back and the component removes itself.
- Every machine builds its own ragdoll, on a body that no other machine owns. `ModelPhysics.CreatePhysics` returns at
  once on a proxy (read from Sandbox.Engine.dll's IL on 2026-09-30).
  - Before the fix, a body under someone else's pawn or bot got no physics bodies. It stood in its bind pose (a T-pose)
    until it was removed. The user saw it with a second instance on 2026-09-30.
  - The Theater replays showed it on both machines: every host bot's corpse on the client, and every other player's
    corpse on each machine. Only a machine's own bodies fell.
- So the body leaves its parent first, then goes limp:
  - `PlayerPawn.CreateRagdoll` unparents it before `SetRagdoll`.
  - `LightweightCombatBot`'s `OnKill` unparents the renderer's object. It takes the dead, ragdoll and corpse tags it
    had from the bot, and goes when the bot does (`OnDestroy`).
  - A child object has no network object of its own: `GameObject.Network` goes by the parent chain. So on its own the
    body is local, and each machine plays out the same DeathPlan.
  - Only a network object's own transform is synced, not its children's, so nothing pulls the body back.
- A zombie's driver is on the zombie's own networked object, so it can't leave it. On a client,
  `ZombieAI.CreateLocalCorpse` makes a local copy of the driver, builds its bodies from the zombie's pose, and moves the
  zombie mesh across. The host ragdolls the zombie itself, as before.
- The Theater recorder keeps recording a bot's body after it leaves the bot (`MatchRecorder.Soldier.Leaver`). The
  body's tracks stay under the bot's, and its `Parent` records the move, as a player's does.
- The fix compiled offline on 2026-09-30 and hasn't been seen yet. To check it, watch a bot's corpse and another player's
  from a second instance, and a zombie's.
- Compiled on 2026-09-29. None of it has been seen, in-game or offscreen: the tone rates, support curves and balance
  are first guesses from the design, to tune by watching.


# Zombie hit reactions — 2026-11-04

`ZombieAI.OnDamage` previously played pain audio without an animation reaction. The zombie driver plays direct
sequences, so the citizen animgraph's procedural-hit parameters do not animate it.

Positive, nonfatal hits now broadcast a host-authorized directional impulse to `ZombieHitReactionPose`.
The layer bends the spine and kicks the neck/head over the existing animated pose. Headshots have a stronger
head kick; impact direction comes from the damage origin or attacker. A critically damped response peaks near
60ms and settles in roughly half a second. Impulses are bounded and shotgun pellets within90ms coalesce.
Burns, zero-damage hits and dead/ragdolled zombies do not react. Movement, attacks and their damage timing are
unchanged; this is a pose response without a navigation stop or a new gameplay stun.

`BotSystem` applies the layer after animation in FinishUpdate and explicitly merges it onto the visible bodies.
It reads the unmodified animation before applying the pose, preserving animated legs and preventing drift when
animation LOD reuses a frame. Bone groups and merged bodies are cached after the first impact. No work or pose
allocation occurs on a zombie that has never reacted, and dedicated servers skip the visual layer. No model,
walk clip or other animation asset was changed. The pre-existing walk refinements in ZombieAI are retained.

`verify.cs.txt` creates an isolated editor scene and checks all three zombie body assets, visible bone merging,
head displacement, exact foot preservation, recovery, frame-rate agreement at30/60/144fps, opposite directions,
headshot strength, repeated-impulse bounds, actual nonlethal damage/RPC dispatch, pellet grouping, the post-animation
system hook, burns, zero damage and dead-object guards. `verify_locomotion.cs.txt` checks walk/run/attack sequence
time and playback, exact animated feet, and nonaccumulation on reused animation poses. All34 checks passed.
The game and editor assemblies compile with zero errors. These are native isolated checks; a separate remote-client
session was not exercised. The user's Riverside scene and play state were preserved and test scenes destroyed.

Evidence: `output/zombie-hit-reactions-20261104/native-checks.json`, `locomotion-checks.json` and the raw native
neutral/impact/recovered/motion PNGs. `preview.py` encodes those unchanged poses into `hit-reaction.gif`; its only
processing is resizing/palette encoding for playback. `native.py` attaches to the user's existing editor and keeps
all run_csharp scripts in the native session exchange directory.

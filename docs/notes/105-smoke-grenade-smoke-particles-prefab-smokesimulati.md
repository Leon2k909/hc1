## Smoke grenade (`smoke_particles.prefab`, `SmokeSimulation`)
- Colour: the user saw the smoke grenade's cloud come out dark navy, almost black, in an Innocent Hotel room (2026-10-01). A
  screening smoke grenade's HC smoke is white-grey; only coloured signal smoke is anything else.
- The sprite (`smoke1.vtex`, from a cloud package) is a neutral light grey, about 0.8, and the tint was white. The cause
  was the renderer's `Lighting`. In the engine's `sprite_ps.shader`, a lit sprite gets the dynamic lights plus either
  baked light (a lightmap or light probes) or, if it has neither, the scene's flat `AmbientLightColor`. A cloud map's
  rooms are lit by baked light the sprites don't receive, so the smoke got only the sky's dark blue ambient.
- The sprite renderer can't be part-lit, so the smoke is now unlit with a tint of 0.85 (`ParticleEffect.Tint`): about 0.7
  of white with the texture. It's the same brightness everywhere, so in a dark spot it can look a little bright.
- The fire's smoke (`FireParticles`, the thermite and grass fires) is still lit, since its own flames' light falls on
  it. Indoors on a cloud map, away from the fire, it may darken the same way.
- The user's next screenshot showed it white-grey in that room (2026-10-01).
- Walls: in that screenshot the cloud showed on both sides of a wall pillar. The user: smoke shouldn't "phase through
  walls". The effect's collision kept each puff's centre out of walls. But a puff is a camera-facing sprite up to 167
  units across, which reached past them: from the other side of a wall, or past a pillar's edge, the part on your side
  showed.
  - Now `SmokeSimulation.OnAfterStep` keeps each puff to the room round its centre. It shrinks the sprite until it
    reaches (0.47 of its width, smoke1.vtex's alpha edge) no more than 6 past the nearest surface, inside the renderer's
    DepthFeather. It makes the puff denser by the area it lost (at most 2.5x and alpha 0.85), so a doorway, a corridor or
    a corner still holds its smoke, in smaller puffs. A puff grows back at 30 units of reach a second.
  - Floors count 32 further off (`FloorAllowance`). A puff sunk into the floor it's over looks like smoke lying on it,
    and held strictly to the floor the cloud's base would be lumps.
  - A probe is 26 rays out to 90: a level ring every 30 degrees and rings of 6 at 35 degrees up and down, turned
    15 degrees from each other so a pillar or door jamb between two rays meets the next ring's, then straight up and
    down.
    - Each puff is probed when it's new, every 16 units it drifts and every second (doors), at most 10 puffs a frame.
    - Between probes, the triangle inequality bounds its clearance: the probe's, less how far it has drifted since.
    - New puffs go by the vent's own probe, taken every 0.25 s in `OnUpdate`.
  - Why OnAfterStep: the engine runs the controllers' `OnParticleStep` (its `OnStep`) before it applies the
    effect's Scale and Alpha curves, which would overwrite them. `OnAfterStep` is its `OnPostStep`, called from
    `ParticleGameSystem` on the main thread once the threaded step is done, so the traces are safe there. Read from
    Sandbox.Engine.dll's IL. `Particle.Size` is the sprite's full width: the renderer passes the shader Size / 2, which
    scales a quad of ±10 by a tenth.
  - Smoke now goes through player clips (an open window's) and bots' movement boxes, in the puffs' collision
    (`CollisionIgnore`) and the probes.
  - Compiled offline on 2026-10-01, not yet seen in-game. Things to check: smoke near a wall and a pillar from the
    other side, a doorway, the cloud's base on open ground, and the frame time with several smokes out.
- A volume renderer was tried on 2026-10-12 (`SmokeRendering`, `shaders/hc1_smoke.shader`, started by
  `SmokeSimulation.OnStart`, with the prefab's sprite renderer off). It drew nothing in the engine: 200 puffs were
  queued for the camera and none showed. The user saw a grenade on the floor with no smoke. So the sprite renderer is on
  again and `OnStart` is commented out, until the volume renderer works. Its files are still there. Not yet seen in a
  match: the prefab needs recompiling after the hotload.


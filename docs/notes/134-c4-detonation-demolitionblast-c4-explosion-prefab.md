## C4 detonation (`DemolitionBlast`, `c4_explosion.prefab`)
- The user (2026-10-01): the bomb's explosion "doesnt look very realistic, it should be really destructive, not just a
  little grenade style effect". It was a puff of smoke, a small flipbook flame, a flare and glowing shrapnel. Those
  children are gone; the old prefab is in `Backups/c4_explosion_old/`.
- `DemolitionBlast` (`Code/Weapons/Grenades/DemolitionBlast.cs`) builds the blast in code on every machine, from the
  engine's own sheets, sized from the real charge:
  - 9 kg of C4 (`ChargeKg`) is ~12 kg of TNT (`TntEquivalence` 1.34). On the ground its blast acts like ~22 kg in the
    open (`SurfaceBurstFactor` 1.8, `EquivalentKg`).
  - The detonation's flash (`explosion_03`, additive), then a fireball ~8 m across: measured HE fireballs scale as
    ~3.4 m per kg^(1/3) of TNT. It's 11 `explosion_01` sprites in a dome, full size in 50 ms, white-hot for ~0.1 s,
    then orange, then soot that rolls up (`FireballParticles`).
  - The ground's own dust: a burst thrown up with the chunks (`explosion_02` on soil, `smoke_burst_c` on masonry), and
    the base surge, a ring of 24 puffs driven along the ground that stops 9-15 m out and hangs for 7-10 s
    (`BlastCloudParticles`).
  - A column of soot, then dust, fed for 3 s and rising 15-25 m, which drifts with `WorldWind` and thins out over
    24-34 s.
  - Up to 80 chunks of the ground (`rock_chunks_01`, a shape per sheet sequence: `Particle.Sequence` reaches the
    shader) and a spray of grit, thrown 10-45 m/s. They fly under real gravity (9.81 m/s², not the players' 800 u/s²)
    with quadratic drag for a stone of their size (`DebrisParticles`), bounce, and lie there for 14-22 s.
  - 60 hot sparks, a light that flares with the flash and fades with the fireball, and a 10 m scorch
    (`burnt_patch.decal`) under the old 9 m `grenade_scorchmark` decal.
  - The dust and the chunks take the ground's colours, by `WorldSounds.Classify`: soil, grass, wood or masonry.
  - Loose rigidbodies within 25 m in the open are thrown, ~12 m/s at 3 m and ~2 m/s at 10 m. Each machine throws the
    ones it simulates.
  - The view shakes when the blast reaches the viewer, by Kinney and Graham's peak overpressure there
    (`OverpressureKpa`): as hard as it goes inside ~6 m, a jolt at 30 m (~9 kPa), a faint thump at 100 m.
- The host also breaks every `BreakableGlass` pane the blast reaches in the open, out to 1 psi (`WindowBreakKpa`,
  ~37 m; `DemolitionBlast.BreakWindows`, from `TimedExplosive.Explode`). Damage is still the bomb site's
  (`BombSite.GetExplosionDamage`).
- The explosion object lasts 40 s (`DestroyAfter`) so the column can thin out, and goes at the round's cleanup
  (`DestroyBetweenRounds`).
- Lit sprites go dark on cloud maps (see Smoke grenade), so every sprite is unlit, with its colour in its tint.
- Not seen yet: it compiled offline with dotnet, and nothing has been looked at in the engine. To tune by eye: the
  fireball's size and how long it glows, the surge's and column's density, the chunks' tint, the light's brightness and
  the shake.


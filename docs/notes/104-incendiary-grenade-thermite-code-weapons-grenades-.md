## Incendiary grenade (thermite, `Code/Weapons/Grenades/Fire/`)
- The user asked for "1:1 realistic fire" and picked real thermite over a molotov. The incendiary grenade is the
  AN-M14 TH3 (`ThermiteGrenade`), with FM 3-23.30's figures. It keeps the molotov's files
  (`Assets/Weapons/Throwable/Molotov_Cocktail/`, `molotov_grenade.equip`, already named "Incendiary Grenade").
  - The M201A1 fuze burns 1.2-2 s from the throw (`MinFuze` / `MaxFuze`). Then 750 g of thermate burns for 40 s at about
    2,200 C wherever the grenade has come to rest. There's no blast and no thrown flame.
  - That's ~3 MJ (75 kW). About a third of it leaves the burning point as radiant heat (`FullRadiantPower` 24 kW), and
    after the burn the slag pool gives 3 kW, cooling with a 20 s time constant.
  - Within 16 units of the burning canister (`ContactRadius`) you're touching 2,000 C slag (300 kW/m²).
  - Drops of molten iron fly off, 10 a second, mostly within 0.35 m and never past 1.5 m. Each lights what it lands on
    with that fuel's chance (`SpatterIgnition`) and burns a foot it lands on.
  - Thrown ~25 m: `Throwable.ThrowPower` 795 in `weapon_molotov_grenade.prefab`. The game's gravity is 800 u/s², and a
    throw adds 100 up.
  - The burnt-out canister lies there for 50 s, scaled black, then goes.
- Nothing puts it out, smoke included (the user's choice). `SmokeGrenade`'s extinguish loop over `MolotovFireNode.All`
  is inert now. `MolotovFireNode.cs` is only kept so that loop compiles; `MolotovGrenade.cs` is gone, and
  `molotov_firenode.prefab` / `molotov_explosion.prefab` are unused.
- `SurfaceFire` runs fire on the ground over a grid of 40-unit cells. There's one per scene, made by the host and
  networked, with `DestroyBetweenRounds`.
  - Fuels (`FireFuels`):
    - Cured grass: terrain materials named `meadow_dry` (Ridgeback's dry meadow).
    - Green grass: other terrain grass.
    - Lawn: grass surfaces that aren't terrain, like Flatgrass's.
    - Wood and fabric: by surface.
    - Rock, earth, concrete and metal don't burn.
  - Only cured grass carries a running fire, following these models:
    - CSIRO's grassland model for the head fire's speed (fully cured, 9% moisture, `WorldWind`'s wind);
    - FBP's length-to-breadth ellipse for the burnt area's shape;
    - McArthur's slope rule;
    - Byram's flame length.
  - Each cell that lights works out when its 16 neighbours catch, and the earliest catches first.
  - Green grass and lawn are under CSIRO's curing threshold, so only a lit patch of them burns. Wood burns where it's
    lit for 90 s, fabric for 60 s.
  - A wall 20 units high between cells stops the fire.
  - The host sends each cell to every machine as it lights (`Receive`). Late joiners get a snapshot.
- Heat (host, `SurfaceFire.Heat.cs`):
  - Each burning cell radiates as a sheet of flame (60 kW/m²), and walls shade it. Inside the flames it's 84 kW/m².
    Thermite radiates from its burning point.
  - Damage is Eisenberg's thermal dose (flux^4/3 x time) at the legs, middle and head. The lethal dose (2375) takes 100
    health, and under 1.6 kW/m² does nothing (`HarmlessFlux`). Standing in 1.4 m grass flames kills in about 7 s.
  - The fire's traces, and the sparks' collisions, skip `playerclip`, as the grenade itself does (the collision rules'
    grenade/playerclip pair). So heat, sparks and drops of iron go through an open window's player clip (the Town
    House's).
- Burns aren't hits:
  - Players and bots take them as `DamageFlags.Burn`, and zombies with the tag `burn`.
  - No blood, flinch, knockback or hitmarker, no hardcore one-shot on bots, and Zombies' armour plates don't absorb
    them.
  - They hold off health regen, and the damage indicator points at the heat.
  - The kill goes to the thrower (`FireSource`), even after they respawn. A burning zombie pays only the kill.
- Bots step out of heat that hurts before anything else (`LightweightCombatBot.AvoidFire`). They go to the nearest spot
  150-450 units off with under half the harmless flux (`SurfaceFire.HeatAt`, which isn't shaded by walls).
- Fire or burning thermite within 128 units stops an instant defuse (`AllowInstantDefuse`, `SurfaceFire.IsBurningNear`).
- Burnt ground:
  - Terrain grass is painted with `materials/terrain/burnt.tmat` in the terrain's control map, and the grass clutter
    there goes with it.
  - The control map belongs to the terrain resource, which the editor shares and saves, so every texel is put back when
    the fire goes (between rounds, or when the scene closes). Don't save the terrain while ash is on it.
  - Other ground gets `decals/fire/burnt_patch.decal`, and where thermite burnt out `thermite_scorch.decal` (60 units:
    slag and drops of iron). At most 600 scorch decals.
- Scripts make the assets:
  - `Tools/fire_textures.py`: the burnt terrain material and both decals.
  - `Tools/thermite_sounds.py`: `thermite_ignite` and the 8 s `thermite_burn` loop.
  - The grass fire's crackle is the old `molotov_fire_loop.sound`.
  - The particles are built in code (`FireParticles`) from the engine's flame, smoke, spark and glow sheets.
- Not yet checked in-game.


## Hardcore hit locations (`HealthComponent.Wounds.cs`)
- Hardcore bullets go by where they hit, the same for players and bots, PvP included. Everything scales with the
  round's damage after falloff (`gunDamage` in `TakeDamage`). Bots do their gun's full damage to players in hardcore
  (`RealPlayerDamageScale` 0.75 is outside hardcore only). The table is `HardcoreTrauma`, and armour takes its share
  first (`transmission`, from `ModifyDamage`'s split).
  - Head or neck: 10x the damage, so dead (a helmet can save you).
  - Body: a chance to kill outright of damage / 40, at most 95% (`HardcoreTrauma.KillChance`: M4 50%, 9 mm 30%, a
    7.62x39 AK 65%, SCAR-H 90%, FAL and SPEAR 95%), 0.6x for the belly and pelvis, times the share armour lets
    through, and rarer with a custom game's extra health. Otherwise 4.5x the damage to the chest (3x the belly), but
    never more than 90% of your health (`SurvivedBodyHitHealth`), so a body hit that doesn't roll a kill always leaves
    you alive: M4 90, so the second kills unless you've healed; 9 mm 54.
  - History: the chance came in as the user's "real life" ask, then on 2026-10-07 commit b733fcbd made body hits
    deterministic (chest 4.5x: 5.56 always two hits, 7.62 always one). On 2026-10-16 the user saw "2 body shots every
    time", said one would kill in real life, and chose "whatever is realistic": the chance is back, and the heavy rounds
    no longer kill every time. `dotnet run --project Tools/TraumaChecks` checks the table (25 checks).
  - Arms, hands, legs and feet: 1.7x the damage, at most half your health (M4 34, so three kill; pistols four, SMGs
    five). Only these, and falls, add wounds.
- Explosions, knives and falls aren't bullets: they still kill bots (and players hit by bots) outright in hardcore,
  and otherwise use normal HP. Burns (`DamageFlags.Burn`, see Incendiary grenade) never kill outright: like the
  battle royale's zone, they only wear health down.
- There's no bleeding or bandaging: the user turned those down because they'd slow the game. Health regenerates in
  hardcore too, like Core (4 s after the last hit, 25 HP/s): the user sees it as the character patching themselves
  up. Only the arm wounds' recoil and sway last. Bots have no regen.
- Each leg/foot wound makes every gait 15% slower (`WoundSpeedScale`, up to two count; bots too, via `GoTo`), and the
  limp wears off by itself: `LegWounds` is a float the host heals at 0.6 a second from 1.5 s after the last leg hit,
  so one hit is gone in ~3 s and two in ~5 s (the user found a 20% limp that lasted until death far too slow). Any
  fall damage adds one leg wound the same way, in every mode, Zombies included (the user asked for it). Each
  arm/hand wound adds 25% recoil and a slow aim drift (`CameraController.ApplyWoundSway`, 0.35 deg, less crouched
  or prone). A bot's aim error goes up 40% per arm wound. Arm wounds last until death (`ClearWounds` on respawn).
- The player models (`models/player/*_side_player_01_v2.vmdl`) tag only head, spine and arm hitboxes (pelvis is
  "pelvis"; the legs and clavicles have none), so `SceneTraceExtensions.GetHitboxTags` falls back to the bone name.
  Bullets find bodies with a ±7 in box (see Bullet traces), which touches several hitboxes at once, so `Shootable` hits
  each body once per bullet. `SceneTraceExtensions.ThroughBody` (also used by bot shots) follows the bullet's line through that body and
  takes the first vital hitbox on it, else the first limb: a round through an arm held across the chest hits the chest.
  Before this, a leg shot also hit the pelvis, and PvP bullets did their damage several times over.


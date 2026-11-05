## Wallbangs (`Shootable.ResolvePenetration`, `Shootable.Penetration.cs`)
- Damage loss added in code (2026-11-04, no editor): `ResolvePenetrationWithDamage` tracks a cumulative damage
  multiplier while finding the same exits as the original resolver. Each entry receives its incoming damage;
  only a successful crossing reduces the damage of later hits. `Shootable.Shoot` multiplies normal range falloff
  by this value before rounding. Each pellet/shot starts at 1. Bodies and solid/unknown cover still stop rounds.
  Per-unit loss in `PenetrationDamageRules` is a gameplay approximation: wood 0.125, plastic 0.175, sheet metal 3.2,
  glass 0.05, and fabric/paper/cardboard 0.1. At their existing maximum supported thicknesses, these retain 50%,
  65%, 60%, 85% and 90% respectively. Multiple crossings multiply their retained fractions. Glass loss is modest
  because map window collision is thicker than the real pane. Custom surfaces inherit their base material's loss.
  This does not simulate cartridge-specific residual velocity, fragmentation, deflection or penetration depth.
  The original three-argument `ResolvePenetration` API remains available and returns the same hit sequence.
  Offline tests link the production penetration iterator with deterministic trace seams. Gameplay feel and map
  balance still need in-game verification.
- The user (2026-09-29): no wallbangs through brick or thick walls, where a real round couldn't go. Codex rewrote the
  penetration pass that day. Rounds used to go through anything up to 32 units thick (`PenetrationThickness`), any
  wall in the game included.
- Now the surface decides (`PenetrableDepth`), per object:
  - Wood: a round crosses at most 4 units.
  - Plastic: 2.
  - Fabric, paper and cardboard: 1.
  - Sheet metal (`metal.sheet`): 0.125.
  - Glass: 3.
  - Everything else stops it: `default`, ceramic, solid metal, dirt. s&box's core surfaces have no brick, stone,
    concrete or plaster, so the maps' masonry is `default` (Belltower's `STONE`, the Ridgeback's walls).
- The thickness is measured along the shot, back from an exit on the same collision shape. All the objects a round
  crosses share one budget: `PenetrationThickness` clamped to 8 (so 8 for every gun).
- A round stops at the first body it hits. Before, it could go on into a second one.
- Glass is 3 because maps model a pane's collision thicker than real glass: Belltower's church windows are 2 units and
  the Ridgeback's breakable panes 0.5. Codex's 1 stopped every shot at the church windows (fixed 2026-09-29). A
  `BreakableGlass` pane still breaks and lets the round on, and that isn't a wallbang.
- A thin partition authored as `default` stops rounds too, since its surface can't tell it from brick. A solid box
  with a light surface is measured whole, so a thick prop box of fabric or sheet metal stops rounds (Belltower's lorry
  tilt and cab did, before the lorries came out).
- Codex reported it passing an offscreen engine test. Not checked in a match.


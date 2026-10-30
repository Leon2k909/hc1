## Wallbangs (`Shootable.ResolvePenetration`, `Shootable.Penetration.cs`)
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


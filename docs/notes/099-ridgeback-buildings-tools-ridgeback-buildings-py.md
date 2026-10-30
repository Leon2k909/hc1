## Ridgeback buildings (`Tools/ridgeback_buildings.py`)
- Built by script, like the rest of the map. Each building is one model made of boxes, and its collision is the same
  boxes, so what you see is what stops players, bots and bullets. Frames, sills, surrounds, shutters, gutters and
  downpipes are only for the eye, so they don't catch shots through a window.
- The first is the Town House: a two-storey village house of rendered brick under a clay tile roof, 42 by 30 feet.
  - It has three doors (front, back and side). Each floor has two front rooms, with a kitchen and the stair hall behind.
    A straight stair runs along the hall's back wall.
  - Every doorway has a door, and the windows are glazed casements with shutters (see Doors and Windows below).
  - It stands ~660 units north-east of Town's crossroads (world -1615, -2040; yaw 87.5), facing west onto the Airfield
    road. That's the one spot near the crossroads on bare earth that faces a road.
- The script writes:
  - `Assets/models/buildings/<name>/`: the render OBJ, the roof's collision OBJ and the vmdl, and beside them the door
    leaves (`_door_outer`, `_door_inner`), the pane (`_pane`) and three broken panes (`_pane_broken_<n>`), each an OBJ
    and a vmdl with no collision of its own;
  - `Assets/prefabs/buildings/<name>.prefab`: a ModelRenderer and a static ModelCollider, with the doors, the panes and
    the windows' clips as children ("Doors", "Windows", "Window Clips");
  - `Assets/prefabs/buildings/glass_shatter.prefab`: the shards a breaking pane throws.
- ModelDoc reads an OBJ as Y-up, so model (X, Y, Z) is written as OBJ (Y, Z, X). The script's docstring has the model
  and plan axes.
- Materials come from `Tools/building_textures.py` (`Assets/materials/buildings/`): lime render, whitewash, concrete,
  floorboards, quarry tiles, clay roof tiles, painted wood, board shutters, brick and galvanised metal. They're drawn
  with numpy like the ground's. The UVs are world-scale, so a brick is a brick's size on any wall.
- The roof's collision is one convex hull from the upper ceiling to the tiles, plus a box under each verge. So there's
  no attic floor for the navmesh to find (a walkable island nobody could reach). The roof's 42 degrees are steeper than
  the navmesh's 40, so nothing walks on it, and drop points (`Scene.NavMesh.GetRandomPoint`) can land in the rooms but
  never on the roof.
- The stair needs room at both ends, because the navmesh keeps 16 from every wall and drop:
  - With 6 at its foot and 28 at its top it was an island. Now it has 40 at its foot.
  - The stairwell's low wall along the upper hall stops a step short of the top, so the top step opens onto the hall
    as well as the landing.
- Surfaces:
  - Walls, plinth, steps and the ground floor are "default" (concrete footsteps, the generic bullet impact). The upper
    floor and the stair are "wood", and the roof "ceramic".
  - Its "default" walls stop rounds, like all masonry (see Wallbangs), while its doors (1.375-1.75 of wood) and glass
    let them through.
- Doors: 3 outside (painted green, 1.75 thick) and 7 inside (varnished, 1.375), four-panel leaves with lever handles.
  - Each is an object in the prefab with a `TerrorTown.FuncDoorRotating` (Innocent Hotel's door type) and a wooden box
    collider that moves with it. It swings 90 degrees away from whoever opens it (`OpenAwayFromActivator`) in 0.9 s,
    and shuts in 0.75 s.
  - Its origin is on the hinge line, 42 over the floor. Its sounds play there, inside the leaf, so they aren't
    occluded (an occlusion trace would always find the leaf).
  - `check_swings` stops the script if any door, opened either way, would meet anything drawn or another door's swing.
  - Bots open the doors in their way (`MapMover.FindDoorAhead`). Doors are left out of the navmesh (the `door` tag),
    so paths go through the doorways.
  - The sounds are synthesised by `Tools/building_sounds.py`, like the kill sounds, so there are no samples: the latch
    and a hinge creak opening, a creak shutting, then the leaf's thud and the latch. A re-run keeps the `.sound` events.
  - A player who joins while a door is open gets it wrong: `MapMover.OnStart` takes the snapshot's open transform as the
    shut one. That's MapMover's, so Innocent Hotel's doors do it too. Not fixed.
- Windows: two casement sashes of three panes each, 18 windows and 108 panes.
  - Each pane is an object of its own with a `Facepunch.BreakableGlass` (`Code/World/BreakableGlass.cs`), tagged
    `glass`. A bullet, a blast or a thrown grenade breaks it.
  - A broken pane leaves one of three jagged rims in the sash, picked by the object's id so every machine shows the same
    one. It plays `glass_break.sound` and throws its shards (`glass_shatter.prefab`): the engine's glass-impact chunk
    sprites (`impact.glass.chips`) at the size of a pane's pieces, falling under real gravity and resting where they land.
  - The panes' colliders (0.5 thick) tile the whole opening, frame and sashes too, so nothing gets through a window
    without breaking a pane.
  - Map objects aren't network objects, so whoever breaks a pane sends the break through a static RPC keyed by the
    GameObject's id: the shooter, the host for bots and blasts, a grenade's owner. The host tells a player who joins
    later which panes are broken, and the between-round cleanup puts them back.
  - Glass doesn't stop anything:
    - A round through a pane breaks it and goes on, and isn't a wallbang (`Shootable`).
    - Sight checks and blasts leave glass out (the bots', `Spotter`, player markers, the flashbang, `Explosion`).
    - Bots' shots break the panes on their line (`BreakableGlass.BreakAlong`).
    - A blast breaks the panes it reaches with no wall in between (`BreakInBlast`).
    - A grenade faster than 120 u/s breaks the pane in its way and carries on (`BreakAhead`, from
      `BaseGrenade.OnFixedUpdate`).
- One object tagged `playerclip` holds a 3-thick box in each window opening, so nobody climbs in or out through a
  broken window. The player's CharacterController traces against it. Bullets, sight checks, the shards and grenades
  (the collision rules' grenade/playerclip pair) pass it.
- `PLACEMENTS` says where each building stands:
  - `--measure` reads the ground under each from `ridgeback_map`'s terrain and prints the floor height (10 units over
    the highest ground), each doorstep's height, the nearest road, and any grass ground under the footprint. Grass is
    scattered on meadow and dry meadow and would grow up through the floor.
  - `--place` writes them into ridgeback.scene: a prefab instance each under the "Buildings" object, which it replaces,
    leaving the rest of the scene as it was. Close the scene in the editor first, or saving it there puts the old
    buildings back.
  - Re-run `--place` whenever a prefab gains objects, so each one has a fixed id in the scene
    (`__PrefabIdToInstanceId`): the doors' and panes' RPCs find them by id.
  - `--preview <png>` renders flat-shaded views, and a plan of each storey with the glass, the clips and every door shut
    and open both ways.
- The Town House's floor is at z 156.8, over ground 136-147. None of its footprint is grass ground (dirt, with dry
  meadow only in the margin), and no tree stands within 1500. Its doors have two steps down (6 and 12 below the
  floor) to ground 15-20 below it.
- Checked offscreen on 2026-09-28, in a scene of its own in the editor:
  - Renders of the outside, the rooms and the stair, and of the house on the real terrain.
  - A navmesh with the scene's agent settings reaches every room on both floors from all three yards, with none on
    the roof, the porch roof or in the attic. That was before the doors, which the navmesh leaves out.
  - Renders of the doors shut, the front door opened inwards and the back door outwards, the glass and the broken
    panes' rims, with every door's and pane's component loaded as set.
- Not checked in a match: the map's own navmesh, bots using the house and its doors, bullets, the grass beside it and
  the light indoors. Nor has glass been broken in play: the shards (an offscreen scene doesn't run particles), the
  sounds and the clips.


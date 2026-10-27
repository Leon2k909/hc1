## Ridgeback (battle royale map, `Assets/scenes/maps/Ridgeback/`)
- The second battle royale map, a base to build on: a valley about 1.2 km across in a ring of mountains, on an s&box
  Terrain (61440 units square, 2048 samples, 30 units apart; heights -2000 to 11000). North is +X, as on the radar.
  The only building so far is the Town House, by Town's crossroads (see Ridgeback buildings). Otherwise the sites are
  flat pads and named markers.
- `Tools/ridgeback_map.py` builds the terrain (`ridgeback.terrain`, heights and ground painting) and, with `--scene`, the
  starting scene (refused if it exists, since the scene is hand-edited after that). `--preview <png>` draws a shaded map
  with the sites, roads, the river and slopes over 40 degrees in red, plus `<png>_ground.png` in the ground's colours.
  Change the layout there (SITES, HILLS, RIVER, ROADS) and re-run it. A re-run replaces the whole terrain, including
  anything sculpted or painted in the editor. Saving the scene in the editor also rewrites the terrain in the blob
  format (`ridgeback.terrain` plus its maps in `ridgeback.terrain_d`); the script deletes the stale `_d` when it writes.
- Ground: six materials drawn by `Tools/terrain_textures.py` into `Assets/materials/terrain/` (meadow, meadow_dry, dirt,
  gravel, rock, scree: tileable colour, roughness, height, AO and normal maps plus the `.tmat`). The painting rules are
  `ridgeback_map.paint`: green or dry meadow by sun, height and nearness to the river, scree up high, dry/scree/rock by
  slope, then the sites, roads and river bed over them. The splat keeps each sample's two strongest materials, and the
  shader height-blends them. A material change from one sample to the next shows the 30-unit grid as blocks, so blends
  have to be several samples wide.
- Grass: `Tools/ridgeback_grass.py` writes `Assets/models/grass/` (four geometry clumps with three LODs each, the blade
  atlas and `grass.vmat` on `shaders/hc1grass.shader`) and `ridgeback_grass.clutter`. The scene's "Grass" object is a
  ClutterComponent in Infinite mode: every machine scatters grass in 512-unit tiles round its own camera (radius 3) on
  meadow and meadow_dry ground only (`TerrainMaterialScatterer`, by the dominant material). The shader has its own
  breeze. Between 1000 and 1450 units out it sinks the clumps into the ground and shades them towards the ground's
  colour, so keep the fade's end inside TileSize x TileRadius (the script asserts it). It's visual only: no collision,
  and bots see through it. Measured in play in the editor (2026-09-26): 0.5-0.8 ms a frame with it on against off, at
  Density 26 (441 clumps a tile). Scattering a tile takes ~0.3 ms, and the engine does at most 8 tiles a frame.
- Clutter's GPU culling follows the scene's active camera (the editor viewport, in the editor), so a `capture_view`
  from a temporary camera elsewhere shows no grass. For captures, generate a temporary NotSaved ClutterComponent in
  Volume mode round the spot, or frame the viewport.
- Far grass: `ridgeback_grass_far.clutter` (the scene's "Far Grass", Infinite, 1024-unit tiles, radius 5) scatters about
  a sixth as many clumps of wider blades (`FAR_CLUMPS`). They rise out of the ground where the grass sinks and sink again
  4000-5000 units out (`FAR_FADE`, ~127 m). Beyond that the meadow and dry meadow ground is painted the clumps' mean
  colour (`ridgeback_grass.ground_colour` x `GROUND_MATCH`, applied by `terrain_textures.match_grass`), so the field
  doesn't turn dark where the grass ends. That's how big open-world shooters do it: dense grass near, sparse cheap clumps
  further out, and ground that matches beyond. Its cost was lost in `dev_perf`'s noise (2026-09-27).
- Trees: `Tools/ridgeback_trees.py` plans every tree, bush and hedge from the terrain's own fields (`ridgeback_map`'s
  heights and painting) and writes them into `ridgeback_trees.clutter` for `PlannedScatterer`
  (`Code/Maps/PlannedScatterer.cs`), which places a planned list (`Placements`: 7-byte records of entry, x, y, yaw and
  scale) and only traces each spot's ground height. `--preview <png>` draws the plan over the ground map.
  - Facepunch's cloud oaks (dry ones on dry ground), beech and pine bushes and beech hedges: 5449 in all (2339 oaks,
    2437 bushes, 673 hedge pieces).
  - Woods round Lumber Camp, along the valley's rim, on the hills and the river's banks; copses and lone trees in the
    valley; bushes along the woods' edges, under the trees and on the banks; the Farm's hedged fields and two roadside
    hedges, with gates and an oak every 14-26 m. Nothing on the roads, pads, runway or river bed.
  - The mountains above the woods are bare. Facepunch's low-poly `vista_oak`s were tried up there and taken out: they
    read as dark balls on the rock faces.
  - Trees and hedges collide (the models' own physics, as static bodies tagged "clutter" with no GameObject), so they
    stop bullets and bots' sight, and the navmesh goes round them. Hit code checks `hitObject.IsValid()`, and bullets
    hitting them get a wood surface (`DamageEvent.GetImpactSurface`). The bushes' models have no physics, so bots and
    bullets go through them.
- "Trees" is a ClutterComponent in Volume mode, which is baked: after re-running the script, press Generate on it and
  save the scene. The instances are stored in the component (a blob in `ridgeback.scene_d`), and every machine,
  a dedicated server too, rebuilds their rendering and collision from that on load. Disabling the component clears
  them (`OnDisabled` calls `Clear`), so never save it disabled.
  - Baked instances ignore the .clutter's per-entry CastShadows and EnablePhysics (`ClutterLayer.PopulateFromStorage`
    gives each a bare `ClutterEntry`): every model casts shadows, and every model with physics collides.
  - Before Generate, check that no entry's model `IsError`. A cloud package that isn't mounted loads as an error model,
    and mounting it under the clutter crashed the GPU (2026-09-27). The editor installs the packages named in the
    .clutter's `__references` into `.sbox/cloud/` at startup.
- What the trees cost: clutter batches have no distance culling and use at most four LODs
  (`ClutterBatchSceneObject.MaxLods`), so every tree in view is drawn, the far ones at LOD 3 (the oaks' LOD 4 goes
  unused). The worst view is from Radio Hill's top looking north over the whole valley. There, measured with
  `dev_perf 600` in play in the editor (2026-09-27, before the vista oaks came out), the trees took the frame from
  6.5 to 11.3 ms (p50): the oaks ~3 ms, the bushes and hedges ~1.2 ms and the vista oaks ~0.5 ms.
- The sun's shadows reach `r.shadows.csm.distance` from the camera, not the camera's far clip. That's s&box's own
  graphics setting (15000 by default, 20000 on the developer's machine), so only trees within ~500 m cast into the
  cascades. In s&box's source the cascades are fitted in managed code (`ShadowMapper.Directional`), which only reads
  that ConVar, so `SceneDirectionalLight.SetCascadeDistanceScale` doesn't shorten them.
- Layout (east, north): Town (centre), Farm (NW), Airfield (N, a runway pad), Lumber Camp (NE), Quarry (SW, a pit with
  32-degree walls), Military Base (SE), Radio Hill (S, flat top 1350 up), West Camp and East Crossing. A river runs
  west to east through gorges in the ring, with a bed that only falls eastward and 24-degree banks. Eight roads join
  the sites, fording the river.
- The river's water (`Tools/ridgeback_river.py`, 2026-09-28) is 21 strips (`models/maps/ridgeback/river/river_NN`)
  along `ridgeback_map.RIVER`, 22-38 over its bed, in the scene's "River" group. They're tagged `water`, with no
  collision or shadows, so players wade through.
  - The script fits the strips to the terrain the editor has, exported by `ridgeback_river_export`
    (`Editor/RidgebackRiverTools.cs`, into `output/river/`). It replaces only that group in the scene.
  - `ridgeback_river_validate` checks the depths in the running scene.
  - `shaders/ridgeback_river.shader` scrolls two normal maps downstream and fades the water out over the shallows, by
    the depth behind it. The strips are 1240 wide, and the banks cut them off.
  - Its material's keys were `TextureNormalA` / `TextureNormalB`. The shader has no inputs by those names, so the water
    drew with flat default normals and no ripples. Since 2026-10-04 the keys are `NormalA` / `NormalB`: a vmat's
    texture key is the name in the shader's `CreateInputTexture2D`. Not yet seen in-game.
- Everything in the valley is walkable (under 40 degrees, the navmesh's `AgentMaxSlope`) except a few small spots: pads
  and roads are cut and filled at 22/20 degrees at most (`terrace`), and the mountains past the foothills are the
  walls. The map's edges have invisible walls (`Map Bounds`), and the river gorges lead out to them.
- The scene: the terrain, grass, sun, sky, fog, `battle_royale.prefab`, `game_setup.prefab`, a bot manager, a spawn at
  each site (the fallback while there are no drop points; Town's is first, so `IsOnMainNavMesh` paths to it), the
  buildings (under "Buildings") and a `BattleRoyaleArea` (the first circle, radius 24000 on the valley). The navmesh has
  custom bounds (±28500), whose corners take in ledges up in the mountains that nobody can reach: a circle sampled from
  the navmesh would stretch to them, hence the area. The navmesh doesn't update in the editor by itself.
- The ground and grass were checked in play (2026-09-26), and the far grass and trees on 2026-09-27. Loading the map
  in a running game (`dev_mode battle_royale ridgeback`) takes ~18 s, with or without the trees. Play starts in the
  editor often stall first: 50-90 s before the trees, 80-160 s with them (2026-09-27, each time ending just before
  "Added new 51 cloud reference(s) to ServerPackage table"). One stalled before the grass existed. The cause isn't
  known.
- Not yet checked in-game: long navmesh paths for `IsOnMainNavMesh`, drop points and the zone. The name is a working
  name.


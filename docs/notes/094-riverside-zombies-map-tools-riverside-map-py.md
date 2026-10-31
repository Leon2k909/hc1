## Riverside (Zombies map, `Tools/riverside_map.py`)
- Rerunning `riverside_map.py` isn't safe at the moment: the shared kit has moved on and it rewrites more than you changed (note 163).
- The user asked for a Zombies trailer park map "as close to this img as possible" (2026-10-15). The picture is a night
  view down the muddy lane of a Florida trailer park:
  - the RIVERSIDE TRAILER PARK sign with GOOD TIMES / BIGGER TOMORROW under it and STILL HERE sprayed below, and a porch
    trailer strung with lights;
  - SPEED LIMIT 15, a chain-link dog run with TRAILER PARK PEOPLE TOO, an open cooler (SOME THINGS SHOULD STAY
    FORGOTTEN) and a teddy;
  - burning drums, the LUCKY STOP (BEER • SNACKS • FUEL • SURVIVAL) and its shed's FUEL FOOD GUNS A BETTER TOMORROW?,
    NO PLACE BETTER in red neon, a wrecked pickup;
  - a guard tower's searchlight, a raised trailer with SAFE HIGHER STRONGER and a ladder, a boarded camper with a
    bloody handprint, a water tower (RIVERSIDE STICKS TOGETHER), pines and palms, a full moon in broken cloud.
  Every name and slogan is the picture's own made-up one. Its game HUD and weapon name aren't copied.
- Scripts, run in this order (each docstring has the details):
  - `Tools/riverside_materials.py [names] [--scale 0.25] [--out <dir>]`: the rs_ materials in
    `Assets/materials/riverside/` (surfaces at real size, siding and board tints, chain-link, tree cards, flat paints)
    and three atlases: `rs_lit` (self-lit signs and windows), `rs_signs` and `rs_paint_*` / `rs_blood`. The spray paint,
    brush lettering and the neon script are drawn from strokes (`STROKES`, `SCRIPT`), not a font.
  - `Tools/riverside_sky.py`: a moonlit cloudy night (the moon 3 degrees west of north, 15 up, drawn big as in the
    picture, in a gap in the clouds).
  - `Tools/riverside_map.py [--preview <dir>] [--views ...] [--no-models] [--art]` with `Tools/riverside_parts.py` (the
    trailers, porches, store pieces, poles and wires, fences, props, vehicles, signs, towers and trees). It writes the
    models to `Assets/models/maps/riverside/`, the scene `Assets/scenes/maps/Riverside/riverside.scene` (rewritten
    whole) and the radar picture. `--preview` renders flat night views from the picture's camera.
- Levels (plan e, n, z): the pad (z 96, spawns, the office, the dog run, the camper), the terrace (z 96, the porch
  trailer and the sign), the flats (z 0, the park), and the levee (z 96, along the river on the east, the stilted
  trailer). The south ramp, the north ramp and the stairs by the store join them in a loop to run zombies round.
- The picture's camera is `REF_EYE` (60, -420, pad + 124), 1.5 degrees east of north and 7 down, 80 across. Things were
  placed from their bearing and distance in the picture. Its eye is about twice a standing player's over the ground (it
  sees over the camper's roof), so a timber watch deck stands there (`watch_deck`, `DECK`: 5 ft up, rails on three
  sides, sandbags along its front, steps up its back): a player standing on it sees the picture's view. The `player`
  capture view is from the pad.
- The guard tower's searchlight throws a visible beam (`riverside_parts.beam_cone`, `rs_beam`,
  `shaders/hc1_light_beam.shader`), drawn in the patches model so it casts no shadow. A new shader needs
  `EditorUtility.CompileShader` before its vmat compiles.
  - Redone on 2026-10-15 (the user: "this light needs work its awful"). It was a textured additive cone at intensity
    0.9: at night's exposure it blew out to a solid milky cone with hard edges, cut through the trailer it was aimed
    past, and pointed down while the lamp housing pointed level.
  - Now the cone is only a closed proxy (a truncated cone, outward normals) to shade inside. The shader takes each
    pixel's ray once (on the proxy's far side: its normal facing away from the eye), works out where the ray is inside
    the cone analytically, clips that at the opaque scene's depth (no depth test), and marches 24 steps of single
    scattering through it:
    - the light spreads from a virtual source behind the 8" lens (`LAMP_LENS`), 2.5 degrees to 1/e^2 (`BEAM_ANGLE`, a
      searchlight's near-collimated beam; at 4.5 it faded out before the ground), with a flat-topped soft profile,
      falling as one over the distance squared;
    - Henyey-Greenstein forward scattering (g 0.45), so it's brighter looking up the beam; looking into the lamp is
      capped (`min( sum, 6 )`) but still dazzles;
    - slowly drifting lumpy haze (value noise), and the scene's fog between the eye and the beam dims it.
  - The pool where it lands is lit by the same shader: any surface the eye sees inside the cone gets Lambert light
    (normal from the neighbouring pixels' depth) over an assumed muddy albedo (`g_flPoolIntensity` 150,
    `g_vPoolAlbedo`). It lights a zombie in the beam too, but casts no shadows.
  - There's no SpotLight for it any more. In s&box a spot as narrow as the beam lights nothing (offscreen tests: 3.5
    degrees lit nothing even 200 from the ground, 10 degrees did), and its quadratic falloff had died out 25 m away
    even at 75 times the brightness. The old one also sat inside the lamp housing with shadows on.
  - The cone's world-space geometry is in its material, so `riverside_map.py` writes `rs_beam.vmat`
    (`riverside_materials.beam_vmat`) with the models; the materials script no longer does.
  - The lamp housing points at the target (`guard_tower(..., aim=)`). The target is `(-410, 730, 0)`, down the lane
    towards the entrance: every ray of the old one at `(-1100, 900)`, centre included, went through a lowland trailer's
    roof. A scratch check (rays inside 6 degrees against the solid models' collision) found the new one clear.
  - Checked in offscreen captures (`capture.cs.txt`'s `beam_side`, `beam_under`, `beam_tower`, `beam_lane`,
    `beam_pool` and `reference`), not yet in a match.
- The wrecked pickup in the lane came out on 2026-10-15 (the user: "remove this car its trash"). `riverside_parts.pickup`
  is still there, unused.
- The sky's cloud bodies are lighter than the clear sky behind them (moonlit grey-blue), as in the picture; drawn darker,
  they vanished. The scene's sky tint is 3.4.
- Zombies only: the scene lists only `zombies.prefab` and sets `MapInformation.ZombiesOnly` (the Sewage map's flag),
  which `MatchLauncher.ZombiesMaps` reads. It isn't in `GameUtils`' match maps, so Quick Play, Ranked, the playlists
  and the map vote don't offer it.
  - `ZombieSpawnPoint` (`Code/Maps/`): `ZombiesRoundSystem.TryFindSpawnPosition` takes a map's own points first, 600-3200
    from the nearest player, unseen ones first. Riverside has 16, inside the gaps in the perimeter fence (the gaps are
    clipped for players).
  - `ZombiesStationSpot` (`Kind`, `Order`): `PlaceBuyStations` stands each kind at the map's spots, lowest Order first:
    the weapon crate in the store, the workbench by the office, wall weapons on the office, the shed and a levee
    trailer, ammo boxes on the pad and the levee.
- `MapFire` (`Code/Maps/MapFire.cs`): dressing fires (the drums, the burning trailer, a far fire across the river) with
  `FireParticles`' flames, smoke and embers and a flickering light. Each machine draws its own; it doesn't spread or
  hurt. It runs in the editor too (`ExecuteInEditor`), so the scene view and captures show it.
- `WorldWind.Velocity` is in metres per second: "18,-30" blew every flame sideways. The scene's is 0.45,-0.75.
- The signs read in the engine after tuning: the `rs_lit` atlas's self-illumination is 4.5, the Lucky Stop board's
  mask is low (the lamps over it light it), and the bulbs and lamps are 5-7 bright. Brighter, they bloomed over the
  lettering close up.
- Checked:
  - all 28 spawn and station spots (room, floor, reach) with railhead_map's checks;
  - offscreen in the editor (`Sources/Riverside/editor/navmesh-check.cs.txt`): a generated navmesh has complete paths
    from the first player spawn to all 16 zombie spawns, 7 station spots and 8 player spawns. The isolated scene used
    the default bounds, not the scene's custom ones;
  - offscreen captures (`capture.cs.txt`, views in `output/riverside/captures/config.json`), compared with the
    picture. The menu picture `ui/maps/riverside.png` is the `map_art` capture. `compile-stale.cs.txt` compiles what the
    file watcher missed.
- The burning trailer is charred (`rs_siding_burnt`), with soot blown up its walls from the windows.
- Played once in the editor (2026-10-15, round 1 only):
  - The Zombies match started on it, the 8 zombies of round 1 came at the player along the lanes, and the stations
    stood at their spots. No Riverside errors in the log. A player standing on the watch deck sees the picture's view.
  - The office's wall weapon floated 40 over the pad: its spot is against the office's wall, so the floor trace
    started inside it and took its start for the floor. `PlaceBuyStations` now keeps a spot's own height when the
    trace starts solid. Compiled with dotnet, not seen in a match.
  - Not yet checked: later rounds, downs and revives, buying at the stations, and the frame time with 97 point lights
    (8 shadowed) and 15 fires.


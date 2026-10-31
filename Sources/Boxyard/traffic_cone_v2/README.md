# Traffic cone v2

Replaced Boxyard's five cones on 2026-10-31, at the user's word after seeing both in a real match ("this is better, replace old with this"). Their
collision is new too: the user asked for it to match the new shape instead of keeping the old cone's.

The old cone was a 14-sided lathe in flat paints on a plain box, about 164 polygons, and solid. This one has a 28 in soft plastic body with an open tip
and a real hollow underneath, a little out of true and dented. Its moulded rubber base has a chamfer, a collar, four ribs and a hole through it. The
sleeves are in the old cone's places, so it reads the same from a distance. No logos or makers' marks.

- Triangles, LOD 0-2: 5,600 / 2,440 / 796. Most of those are the rounded base and the hollow.
- One material with 2048 maps (colour, roughness, normal, AO), about 36 px/in. No metal.
- Same origin, axes, height and base size as the old cone.

## In the map
- `Tools/boxyard_map.py`: `cone()` and `lying_cone()` write only collision into the merged props model and record a placement, and `cone_object()` puts the
  model in the scene with no collider of its own, as the drums do.
- `cone_collision()` is the new collision, from the model's real shape: one convex hull for the base and collar, one for the body with its lean. Surface
  plastic. The four small ribs aren't in it.
- The knocked-over cone moved. The old one's axis climbed, leaving its tip about 13 in up and in the crate. The new one's tip rests on the ground, and it
  lies 3 in back along its heading to clear the crate.
- `install_map.py` runs the map script into a scratch folder, compares every model file and the scene object by object, and copies across only if the
  differences are the expected ones. The radar picture isn't copied: it never comes out identical and the cones don't change it.
- The dry run's checks: 0 problems in 76 spots, none cut off from the spawns. The only scene change is the five new objects.
- Rollback: `output/asset-improvement-20261030/traffic-cone/before-install/` holds the props files and the scene as they were.
- Railhead's and Riverdale's cones are their own code (`railhead_furniture.cone`, `riverdale_yard.cone`) and aren't touched.

## Checked in s&box, in a real team deathmatch (2026-10-31)
- It compiled with no errors, and all five cones load their model with none.
- `collision_check.cs.txt`, rays: they hit at the model's surface at 5, 20 and 27 in up and on the base, with surface plastic. A ray at 29 in clears the
  tip, and one where the old tip hung now passes through.
- `walk_check.cs.txt`, `dev_force_move` into the cones: the player stops at -148.4 walking into the standing cone at -166, at 26.6 walking into the
  knocked-over cone's base at 42, and at -540.4 walking into an A site cone at -558. The toggle goes back off in a `finally`.
- Shots are in `output/asset-improvement-20261030/traffic-cone/engine/`: `match-*-installed.png` are the map as installed, and `match-*-before.png`,
  `match-*-after.png` and `match-*-side.png` the comparison the user approved. `match_view.cs.txt` and `match_shot.py` take them.

## Not checked
- Shooting one with a gun in play: rays show the surface, but bullet marks and sparks weren't watched.
- The navmesh: bots may path differently round the moved cone, which wasn't rebuilt or watched here.
- The LOD distances (0, 30, 80) are copied from the oil drum and haven't been watched switching.
- The Blender sheets in `final/` show the knocked-over cone pointing the wrong way. The scripts are fixed, but those sheets weren't re-rendered.

## Files
`cone.py` builds, bakes and exports. `paint_cone.py` paints. `render_cone.py` renders in Blender, `capture_engine.cs.txt` and `capture_config.py` off-screen in
s&box. `verify_cone.py` checks the files. `finish.ps1` runs the Blender side at idle priority. Rerunning the build can change the unwrap, so bake and paint after it:
the export refuses to run otherwise. Exports go to `output/asset-improvement-20261030/traffic-cone/export/`: copy them to `Assets/models/maps/boxyard/traffic_cone_v2/`.

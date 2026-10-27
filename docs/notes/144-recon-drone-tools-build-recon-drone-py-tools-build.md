## Recon drone (`Tools/build_recon_drone.py`, `Tools/build_recon_tactical.py`)
- The user asked for an extremely realistic military recon drone, made in Blender and optimised for the game
  (2026-10-08). It's a Raven-class hand-launched small UAS after the RQ-11B's published figures and photographs, at
  real size: 1.37 m span, 0.91 m long. It has:
  - an olive pod with a gimballed camera ball (EO and IR windows) on a lipped collar under its nose;
  - a parasol wing on a pylon: a flat centre panel and two outer panels at a steep dihedral, with no ailerons;
  - a pusher motor at the pylon's rear, with its two-blade prop just behind the wing;
  - a boom to a rudder and an elevator.
  Its markings are its own (orange tape squares, red and green joint marks, "RZ 04172" on the fin, a label and
  barcode on the pod): no maker's name, logo or designation.
- It replaced the old "RAZED AER-03" model and its 49 cm handheld copy. One model serves the hand-launched Recon Drone
  tactical (`weapons/recon_drone/`: the view model, world model and airborne prefabs, and the .equip's WorldModel) and
  the UAV streak reward (`prefabs/scorestreaks/recon_drone.prefab`). The old materials, textures, OBJs and
  `recon_*_handheld.vmdl`s are gone.
- `build_recon_drone.py` (Blender 5.1: `blender -b --factory-startup --python Tools/build_recon_drone.py`) writes
  `Assets/models/recon_drone/`. Its docstring has the parts, units and axes.
  - Every part is a loft of an analytic shape, F(a, b). Its UVs are (a, b) in the part's rectangle of one 2048 atlas,
    so every LOD maps the same texture.
  - Cycles bakes facts about each texel (part, position, normal, edges, noise, AO) and numpy paints the colour,
    roughness, metalness, AO and normal maps, one material (`recon_drone.vmat`, complex.shader).
  - The finished maps are bled into the gaps between the UV islands. Unbled, the gaps were black, and the poles'
    sliver triangles drew black streaks on the nose cap and the pod's tail.
  - Stages: `DRONE_STAGES` (geometry, preview, bake, textures, export, beauty; default all), `DRONE_TEX` and
    `PREVIEW_DIR` (renders go outside the project by default). The bake isn't kept between Blender runs, so textures
    need geometry and bake in the same run. A full run takes about 2 minutes.
  - The body's three LODs are 3886, 1228 and 418 triangles, the prop's two 420 and 96. `asset-info.json` has each
    LOD's count and bounds, and the prop's hub.
  - The prop is `recon_propeller.vmdl`, with its origin on its hub, so the game can spin it about x
    (`Rotation.FromRoll`). Every prefab puts it at the hub, `-5.512,0,2.283` in the drone's space.
- `build_recon_tactical.py` writes the tactical's four prefabs, its .equip and its icon:
  - The hand holds the pod's belly under the wing, `GRIP` (3.9 forward, 2.3 under the origin):
    `ThrowableViewModelGrip`'s ItemCenterHeight -2.3 and ItemOffset `-3.9,0,0`, and the world model's root at
    `-3.9,0,2.3`.
  - The icon (`ui/weapons/recon_drone.svg`) is the aircraft from above, nose up, at 153 px a metre, in the same
    viewBox as before.
- At real size the streak drone, orbiting 1400 out at 1800 up (`ReconDroneVisual`), is a speck, as a real one is.
- Checked: Blender renders, and offscreen renders of the compiled model in the editor (2026-10-08). The editor compiled
  the vmdls and the vmat with no errors, and the compiled model's bounds match the export. Not checked in-game: the
  first-person hold (at real size the wing may fill the bottom fifth of the screen), the third-person hold and the
  flight.


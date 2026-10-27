## Recon octocopter (`ReconOctocopter`, flown from a tablet)
- The user sent a photo of a soldier with a big grey coaxial multirotor and asked for a recon drone "where u fly from a
  tablet too tho like a normal recon drone" (2026-10-08). It's the Recon Octocopter, a Tactical (Price 750) beside the
  hand-launched Recon Drone.
  - The aircraft is the photo's kind, Inspired Flight's IF800 Tomcat (dronefly.com, volatusdrones.com,
    advexure.com, thedronegirl.com): a coaxial X8 of ~10 kg, four arms with a pair of 26-inch props on each, the
    upper and lower props turning opposite ways, and a zoom camera on a gimbal under the nose.
  - The photo's "IF" lettering and round logos aren't reproduced: its markings are its own, with no maker's name.
- `Tools/build_recon_octocopter.py` (Blender 5.1, `blender -b --factory-startup --python ...`) writes
  `Assets/models/recon_octocopter/`. It's built like the Raven, with `build_recon_drone.py`'s helpers (lofts, baked
  facts, numpy-painted atlases). Its docstring has the parts, axes and stages (`OCTO_STAGES`, `OCTO_TEX`,
  `PREVIEW_DIR`).
  - The airframe (12168, 4208 and 1492 triangles), the gimbal ball (440, 144), the props (`_prop_ccw`, `_prop_cw`:
    990, 266) and a spinning prop's blur (`_disc`, 576).
  - The ground station, `recon_tablet` (3634, 1062): a rugged 10.1-inch tablet between two thumbsticks, with grip
    handles, button pads and two paddle antennas. Its screen shows a standby page drawn by the script, with no brand.
  - `asset-info.json` has the hubs and their spin, the gimbal's pivot and lens, the skids' height and the tablet's
    grips, in inches. The models and materials compiled in the editor on 2026-10-08.
- `Tools/build_octocopter_equipment.py` writes `Assets/weapons/recon_octocopter/` from those figures: the airborne
  prefab, the view model (vm_c4's arms, with `TabletViewModel`), the world model, the weapon prefab (`ReconTabletLink`
  on Attack1), the .equip and the icon `ui/weapons/recon_octocopter.svg`, which the radar also uses. Every guid is a
  uuid5, so a rerun writes the same files.
- How it's flown:
  - Attack1 with the tablet out sets the drone down ~1.8 m ahead (`ReconTabletLink.LaunchDistance`) on level ground
    with room to climb, or shows NO ROOM TO LAUNCH. It spools up for 1.2 s, climbs to a 2.5 m hover and links.
  - Linked, the mouse turns the camera (slowed by the zoom; the gimbal slews 180 degrees a second, pitch -20 to 90
    down), WASD flies relative to the camera's heading, Jump climbs, Duck descends, and Duck held at the ground lands.
    Run is sport mode. Attack1 / Attack2 or the wheel zoom.
  - Use goes back to the body, and the drone holds where it is. Attack1 again links to it.
  - The operator also comes back on any hurt, a flashbang that reaches them (`FlashbangGrenade`) or death. On death,
    and with the battery empty, it lands by itself.
- The flight (`ReconOctocopter.Fly`, `UpdateAttitude`) is position-hold, as a GPS drone's: the sticks command a
  velocity, and the airframe tilts into the thrust that needs, drag included.
  - 12 m/s cruise, 18 m/s sport, 7 m/s² acceleration, 5 m/s climb and 3 m/s descent, at most 35 degrees of tilt and
    120 m over the take-off point. Drag is ½ρCdA/m for ~0.13 m² and ~9 kg.
  - The airframe turns after the camera at up to 120 degrees a second. It slides along what it touches, and a hit
    over 200 u/s (`CrashSpeed`) takes integrity.
  - The battery lasts 90 s (`BatterySeconds`). That's a game limit: the real aircraft flies 40 minutes and more.
- The camera: 62 degrees wide at 1x, zoom 1x, 2x, 4x, 8x, 16x and 30x.
  - The host scans its picture twice a second. A living enemy in frame, unhidden, and within `SpotRange` x the zoom is
    marked for the operator's team on the radar and as a marker, and stays marked a second after it's last seen
    (`Reveals`, read by `PlayerMarker`, the bots' radar icon). Off the Grid hides from it.
  - `SpotRange` 3600 (~92 m) at 1x is the Johnson criterion: 6 line pairs across a person on a 1080p sensor at 62
    degrees.
- The operator stays in their body and keeps it possessed. `Link()` makes a feed camera on the drone (IsMainCamera,
  Priority 50, the body camera's post-processing copied) and turns off only the body's camera component.
  - The body's AudioListener stays on, so they hear the world from where they stand, as a real ground station's feed
    has no sound.
  - The body stands or crouches where it was (`PlayerPawn.IsPilotingDrone` stops the movement, use, inventory and ping
    input) and can be shot. Their legs-only body is off: from up there they're seen whole.
  - The drone itself isn't drawn in its own feed (2026-10-09). The pilot's machine owns it and tags it `own_drone` while
    the feed is up, which the feed camera leaves out. Other players still see it, and it still casts its shadow.
    - The user saw something "clipping" while flying it. The lens hangs under the nose, inside the rotors' reach. Counted
      from the OBJs: tilted 20-35 degrees into a flight, the front props come into the 62-degree picture 7" from the
      lens. With the camera turned faster than the airframe follows (120 degrees a second), or looking back, the arms and
      the props fill it. Tilted with the camera looking up, the nose is 0.8" from the lens, through the near plane (1).
    - Built with dotnet. Not yet seen in-game.
  - MainHUD hides its HUD, markers, minimap and round strip, and `ReconOctocopterFeed` draws the feed's display: the link and
    recording, battery, heading tape, altitude, speed, distance, tilt, field of view, a box on each contact, zoom steps,
    warnings and key hints. Holding the tablet unlinked, it says what Attack1 does. Its 22 texts are in all ten tables.
- Damage (host): 60 integrity (`MaxIntegrity`), from bullets and blasts through `IDamageable`. The operator's teammates
  can't hurt it; the operator can. Destroyed, it throws sparks, falls tumbling and lies as a wreck for 15 s.
  - One drone a station: when it's destroyed, or lands with an empty battery or no operator, the tablet is taken out
    of the operator's inventory. A new launch retires an operator's last drone.
  - It goes at the round's cleanup and at a score reset.
- Every machine spins its rotors (`ReconRotor`) and plays their sound.
  - The hub (`recon_octocopter_hub`) looks the same turning, so it's always drawn. The blades are drawn under `BlurRpm`
    (240) and a flat disc over it.
  - The user found the disc "a fake white ring" (2026-10-09). It was a texture of each radius's blade share, with a
    bright ring where the tips' white stripes were. The stripes are gone from the blades and the disc's textures with
    them.
  - The disc's look is worked out by `shaders/hc1_rotor_blur.shader` from the prop's real chord, twist and sweep: each
    point darkened by the share of the time a blade covers it, seen edge-on or face-on. While the eye can still follow
    the blades, each leaves a fading trail (ω x 0.025 s, `Persistence`). They fuse into an even, faintly see-through
    disc between 20 and 50 blade passes a second (at hover's 2,900 rpm they pass 97 times). `ReconRotor` sets its
    `RotorSpin`, `RotorTrail` and `RotorFusion` each frame, and the shader takes where the blades are from the disc,
    which turns with the rotor.
  - Written with the editor closed: the shader, the hub and the new props haven't compiled, and none of it has been
    seen. If the disc draws as an error, check the editor's log for the shader.
- The rotor sound (`Tools/octocopter_sounds.py`, `sounds/drones/octocopter_rotors`): an 8 s loop at hover, synthesised
  from how a coaxial multirotor makes its noise. Its docstring has every layer and why.
  - The blade-pass tone (96.7 Hz at 2,900 rpm) and its harmonics, the lower props harsher. The pairs' crossing tone
    at twice that. Broadband swelling at the blade-pass rate. The motors' 676 and 1,352 Hz.
  - Each prop is trimmed ~1% apart and wanders ~0.4%, so the tones beat. Every frequency is a whole number of cycles in
    the loop, so it has no seam.
  - ~70 dB(A) at 10 m, so ~80 at 3 m, squeezed like the rest of the mix: 7.5 dB over the walk on concrete at 120
    units, heard to 6000 (152 m). `UpdateSound` plays it at the rotors' speed over hover (0.3-1.4) and its cube for
    the volume. `--preview <wav>` plays a flight.
- Game limits besides the battery:
  - The play area (`PlayArea`, Return to the AO) isn't applied to the drone, only to the body.
  - Bots don't shoot at drones.
  - What goes by `Scene.Camera` goes by the feed camera while it's linked: the bots' level of detail (`BotSystem`),
    a blast's near or far sound (`BlastSound`, though it's heard from the body) and Reef Hall's fish. Screen shakes
    don't reach the feed (it has no `ScreenShaker`).
- Made offline on 2026-10-08 with the editor closed after the models compiled. The code built with dotnet (0 errors),
  but the prefabs, the .equip, the sound and the code haven't loaded in the editor. On 2026-10-09 the user flew it in
  a match (its spinning props and the clipping above are theirs). Not yet checked otherwise:
  the tablet's first-person and third-person holds (`TabletViewModel.HoldPosition`, `HoldPitch`, `WristOffset` and the
  world model's grip are first guesses), the flight, the feed's display, spotting, damage and the sound.


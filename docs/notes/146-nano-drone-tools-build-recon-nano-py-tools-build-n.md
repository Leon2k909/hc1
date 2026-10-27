## Nano Drone (`Tools/build_recon_nano.py`, `Tools/build_nano_equipment.py`)
- Added 2026-10-10, continuing the user's tiny helicopter scout request. Generic markings, no manufacturer's branding.
  `Assets/weapons/recon_nano/recon_nano.equip` is a purchasable Tactical item (500). The normal class/loadout picker
  discovers it. In a locally hosted match, `dev_give recon_nano` gives and equips its recon tablet.
- Primary fire releases it from the right hand, then opens its feed after 0.65 s. `ReconTabletLink.HandLaunch` uses
  the current eye position and aim, including crouch/prone. It sweeps the whole aircraft from the hand to the release
  and checks overhead clearance. It needs no level ground or octocopter-sized pad. A blocked launch keeps the station.
  `TabletViewModel` briefly lifts the right hand off the tablet for the release.
- `ReconOctocopter` flies both aircraft. The nano prefab sets its camera/flight/damage values; the octocopter keeps
  its original defaults. Main and tail `ReconRotor` components turn inside fixed mounts, with the tail's local Z
  pointing along the aircraft's -Y. Main hover RPM 4800; tail 4.2 times faster. Both use the existing analytic rotor
  blur at their own radius (`RotorScale`, no folding yoke).
- Geometry: a roughly 250 mm dark composite helicopter, a 190 mm main rotor, slender boom, tail fin/tailplane,
  36 mm tail rotor and stabilised nose camera with two sensor windows. Solid parts share a 1024 px baked PBR atlas.
  Body, camera, two props, two hubs and two discs are separate OBJ/ModelDoc models with LODs. Modelling is metres,
  X forward/Y left/Z up; export is inches in ModelDoc's OBJ Y-up convention. `asset-info.json` gives their transforms.
- Flight: cruise 6 m/s, sport 10 m/s, acceleration 4 m/s², climb 2 m/s, descent 1.5 m/s, 28° tilt, 60 m ceiling above
  release and 120 s battery. These are game settings. It has 10 integrity; a bullet or a hard impact can destroy it.
  The flight box includes every rotating rotor tip and the tail. `ReconFlightMath.RotatedHull` encloses it at the
  actual yaw/tilt. Turning into a wall is refused, and a hull that starts inside a solid does not tunnel through it.
- Tablet: WASD moves relative to camera yaw, mouse aims, Jump/Duck climb/descend, Run uses sport speed, wheel or
  primary/secondary fire steps 1x/2x/4x zoom, Use returns to the body. Primary fire on its tablet reconnects to the
  same aircraft. The body stays vulnerable and hears sound from its own position. Spotting, team contacts, landing,
  loss of the operator, battery retirement and round cleanup use the existing recon controller. Only the matching
  aircraft's station resource is removed when it is lost. Its minimap uses the helicopter icon.
- Sound: `Tools/nano_sounds.py` synthesises an original 8 s loop, main blade-pass 160 Hz and tail 672 Hz. The quiet
  level is baked into the PCM, with event volume 1, so the flight's volume control preserves it. It is 15 dB below
  the octocopter mix at its reference distance, with attenuation to 18 m, pitch/thrust from flight and
  a small occlusion radius. `.wav.meta` enables looping. No sampled manufacturer audio.
- Rebuild with background Blender 5.1 (`--factory-startup`); the builder refuses an existing open file. It loads the
  octocopter's mesh/bake/export helpers into a private module and changes no octocopter assets. Then run
  `Tools/nano_sounds.py` and `Tools/build_nano_equipment.py` with Python. The equipment script shares the existing
  tablet/arms, remaps every copied prefab ID and writes stable import IDs while preserving existing ones.
- Offline validation: `Tools/check_recon_nano.py` checks meshes/UVs/normals, all model and prefab references (including
  the installed SDK cache for the human arms), full rotor sweeps within the collision hull, textures, audio, metadata
  and equipment wiring. `Tools/ReconChecks/ReconChecks.csproj` links the actual C# helper and installed s&box math
  types to test optics, rotated bounds and standing/crouching/prone/pitched-view release positions. The game C#
  project builds with zero errors. Previews are in `output/recon-nano/`.
- Made with no MCP or editor. When the editor next opened (2026-10-12) it compiled the models, materials, textures,
  prefabs, the .equip and the sound, each leaving a compiled file. Nothing has been seen in-game: the flight, the hand
  release, the rotor blur at its size, the sound and network play.


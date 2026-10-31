# Reef Hall's bench v2

Created 2026-10-30, installed 2026-10-31 at the user's word ("reef hall bench new better"). All 8 of Reef Hall's benches draw this model. Notes: `docs/notes/175-*`. Nothing is committed.

The old bench is a black laminate plank on two gunmetal boxes. This one has seven hardwood slats on steel bearers, two round-tube sled
frames bolted to the floor, and a brass plaque with made-up lettering. It's a colour change as well: wood, where the old one is black.

- Triangles, LOD 0-2: 2,608 / 1,082 / 360, against 36. One 2048 atlas at about 18 px/in.
- It fits inside the old bench's collision boxes (96 x 18 x 18). Its length is +X and its front +Y. A map yaw of h is an engine yaw of h - 90.
- `bench.py` builds, bakes and exports, `paint_bench.py` paints, `render_bench.py` renders, `verify_bench.py` checks, `make.ps1` runs them. `install_map.py` installed it. `check_config.py` and `capture_installed.cs.txt` are the engine check, for Lowtide's bollards too.

**Which moved:** both rotunda benches, 42 in along their length with their collision, because each ran 27 in into a display case's plinth. They clear it by about 2 in. The lobby's two also turned end for end, in the same space, so the plaque faces the balcony and not the wall.

Checked in s&box on 2026-10-31, in an isolated editor scene loaded from `reefhall.scene`, with the editor on another map and no play session (shots in `output/asset-improvement-20261030/bench-bollard-check/reefhall/`):
- The rooms and the model compiled by themselves with no errors in the log, and no renderer has an error model.
- All 8 stand where the map's code says, with no colliders of their own and the old faces gone. The rotunda's two are clear of their plinths, from in front and from above.
- 58 rays: every one stopped on the seat or leg box at the expected distance, on wood or metal, or passed over the seat and between the legs. Rays through where the old benches' ends stood find nothing.
- It fixed one fault: the slat edges' wear read as pale dashes, which the Blender renders didn't show.

**Not checked:** a real match, because the editor is shared and play wasn't to be started. So walking into them, bullets and marks, bots' paths round the two moved benches, and how they look under the player camera's look: Reef Hall's scene carries no tonemapping of its own, so these shots are lit by the map but aren't graded as a game is. Frame time. The LOD thresholds (estimates, 30 and 80): the shots at 12, 25 and 40 m show nothing wrong, but I haven't watched one switch.

The tunnel's two benches stand over the floor drain, as the old ones did, so their frames cross its grate. Not changed.

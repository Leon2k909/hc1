# Lowtide's mooring bollard v2

Created 2026-10-30, installed 2026-10-31 at the user's word ("mooring new better"). All 12 of Lowtide's quay bollards draw this model. Notes: `docs/notes/174-*`. Nothing is committed.

The old one is three stacked 12-sided cylinders in the shared `iron_black`. This is a cast-iron bollard with a flanged foot on six bolts, a waisted neck,
and a flared, domed head. Black bitumen flakes to rust, with rust running down the paint. The harbour side of the neck is rope-worn, there's salt at the
foot, and it has a made-up foundry mark.

- Triangles, LOD 0-2: 3,574 / 1,786 / 464, against 84 or so. One 1024 atlas at about 16 px/in, shared by all twelve.
- It fits the old collision box (9 in round, 25 high), on the same origin at the ground. It's round, so its yaw only turns the wear: -X looks at the harbour.
- `bollard.py` builds, bakes and exports through `prop_stages.py`, `paint_bollard.py` paints, `render_bollard.py` renders, `verify_bollard.py` checks,
  `make.ps1` runs them. `install_bollards.py` installed it. The engine check is `Sources/ReefHall/bench_v2/check_config.py` and `capture_installed.cs.txt`.

**Which moved:** the two at e = +-690, 4 in towards the harbour with their collision, because each ran 3 in into a crane leg's bogie.

Checked in s&box on 2026-10-31, in an isolated editor scene loaded from `lowtide.scene`, with the editor on another map and no play session (shots in `output/asset-improvement-20261030/bench-bollard-check/lowtide/`):
- The dressing models and the model compiled by themselves with no errors in the log, and no renderer has an error model.
- All 12 stand where the map's code says, with no colliders of their own and the old faces gone. The two by the crane legs are clear of the bogies. The metal doesn't draw near black, and the rope wear, rust and salt all read. The thin vertical line on the neck is the casting seam, painted on purpose.
- 36 rays: every one stopped on the collision box at the expected distance, on metal, or passed over the top.

**Not checked:** a real match, because the editor is shared and play wasn't to be started. So walking into them, bullets and marks, bots' paths round the two moved ones, and the player camera's own look (Lowtide's scene look was on, with exposure held at 2.4). Frame time. The LOD thresholds (estimates, 30 and 80): the shots at 12, 25 and 40 m show nothing wrong, but I haven't watched one switch.

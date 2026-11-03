# Reef Hall's information stand v2

Created and installed 2026-10-31, at the user's word after seeing old and new side by side in a real match ("Yes, replace them"). All 3 of Reef Hall's stands draw this model: 2 in the rotunda, 1 in the tunnel hall. Not committed.

The old stand is a black box post on a black slab, with a glowing panel lying on a black plate. This one is a folded steel column on a rubber kick and a bolted floor plate, with an etched plate on its front ("VISITOR INFORMATION", made up), a service door with louvres, locks and hinges on its back, and a sloped head with a speaker strip, a steel trim and a touch screen behind black glass.

- Triangles, LOD 0-2: 2,408 / 1,210 / 294, against about 40. One 2048 atlas at about 20 px/in, plus the screen's quad.
- Its column fits the post's collision box (16 x 10), and it stays in the old stand's space. Its width is +X and the visitor stands on +Y. A map yaw of h is an engine yaw of h - 90.
- Collision is unchanged: only the post, up to 34 in. The head above it has none, as the old panel had none, so a bullet at head height passes through it and a player can brush through its overhang.
- The screen has the map's own picture and glow, cropped so it's no longer stretched, on matt glass: `info_stand_screen.vmat`. `rh_screen_map`'s gloss showed the hall's lights as a blown-out spot. That material stays in the project.
- `stand.py` builds, bakes and exports, `paint_stand.py` paints, `verify_stand.py` checks the files, `install_map.py` installed it, and `compiled_check.cs.txt` tests what compiled. `compare_config.py` and `capture_compare.cs.txt` shot old and new in an isolated copy of the hall. `match_view.cs.txt`, `in_game_shots.py` and `match_check.cs.txt` do real match shots, rays and a walk.

Checked:
- Before installing, old and new side by side in a real match with the HUD and gun: `output/asset-improvement-20261030/in-game/`. The screen washes out pale under the game's camera, as the old one's does.
- After installing, `verify_stand.py` on the files, and `compiled_check.cs.txt` on what compiled: the rotunda and tunnel no longer use the old screen's material, the 3 stands load with no error and no colliders of their own, and rays stop 60 in out on each post's box on metal. The script's own checks: 0 problems in 89 spots, 0 cut off, 0 Retakes pairs in sight.

Not checked: the stands in their final places in a match, walking into them, bullets, or a LOD switch being watched. `match_check.cs.txt` and the `stand_*` views of `in_game_shots.py` are ready for that. The LOD distances (30, 80) are estimates.

## Reef Hall information stand v2 (`models/maps/reefhall/info_stand_v2`, `Sources/ReefHall/info_stand_v2/`, 2026-10-31)
- Replaced all 3 of Reef Hall's stands at the user's word, after they saw old and new side by side in a real match: 2 in the rotunda, 1 in the tunnel hall.
- `Tools/reefhall_map.py`: `lectern()` writes only the post's collision box (16 x 10 x 34) and appends a prop. `write_scene` places props by `kind` as "<Room> Stand <n>" under "Aquarium" with no collider, numbered per kind so the benches' keys didn't move.
- Collision is the old post's. The head above 34 in has none, as the old panel had none.
- The screen is its own `info_stand_screen.vmat`, with `rh_screen_map`'s picture and glow on matt glass: the original's gloss showed the hall's lights as a blown-out spot. The picture is cropped so it isn't stretched.
- Paint had to be judged in the engine: in the hall's dim blue light, sRGB 58, 66, 78 read as a black shape with no detail, and 106, 116, 130 as pale beside the dark furniture. It's 80, 90, 104.
- **Copying into an open editor:** `install_map.py` first stopped half way, as the editor compiled each file as it landed and held the next, so `os.replace` gave Access Denied. It now waits and retries. Test the compiled result as well as the files: `compiled_check.cs.txt` needs no play and no drawing, so it can run beside a match.
- Checked in a real match before installing, and on the compiled files after. Not yet seen in its final places in a match: see the folder's README.

# Riverdale's first aid cabinet v2

**Installed 2026-10-31** at the user's word ("Install it"), after they said of the old one "this needs to look better" and saw both in s&box: see `docs/notes/186`. On 2026-11-03, after seeing both in a Riverdale match, the user chose the scan-based finish ("trial looks good, replace what was there before with trial") and said to keep both ("they're both good"). The model draws `scanned/first_aid_scanned.vmat`; the code-painted `first_aid.vmat` stays beside it. Nothing is committed.

The old one was a 14 x 17 x 5 green box with a flat picture from the signs atlas, at z 54, four of them in the reactor hall. The new one is a steel cabinet covering the same box: a case on four wall tabs, a door with a black seal in its gap, a piano hinge, louvres, a riveted sign plate, and a lock, handle, rating plate, red seal and yellow inspection tag. All the lettering is generic, with no maker's names.

- About 3.6k / 1.3k / 270 triangles (LOD thresholds 12, 40). One material, one 2048 atlas, about 65 px/in, so the print stays hard close up.
- `first_aid.py` builds, bakes and exports; `paint_first_aid.py` paints, with `scans` for the scan-based finish; `make.ps1` runs them at idle priority, then `paint_scanned.ps1`; `sheet.py` makes the before and after image; `verify_first_aid.py` checks the files.
- `match_shots.py` and `match_view.cs.txt` take in-game shots from a short Riverdale match (modes `scanned`, `painted`, and `pair`, which stands a code-painted copy beside the east wall's cabinet). `render_scan_compare.py` is the Blender comparison of the two finishes.
- `install_first_aid.py` did the install, cutting by position from the live OBJs, because the hall isn't to be rebuilt whole and other sessions change these files. `installed_shots.cs.txt` checks it in s&box. `capture_engine.cs.txt` was for the before and after: since the install, its "before" draws the new cabinet too.
- The scan-based finish takes its mottle, the shapes of its chips and scratches, and its dulled patches from `forestbase/scans/` (`metal_plate_02`, `container_side`, CC0), as the eye wash does, with a third of the mottle on the sign. The kept code-painted finish is procedural throughout.
- One of the case's sides goes near black from some angles. So did the old box's: it's the hall's light on that side, not the paint.

Seen in a short Riverdale match on 2026-11-03, with the HUD and gun (`output/asset-improvement-20261030/first-aid/first-aid-in-game-compare.png`). The tag and seal stand proud of the old box, which had no collision and neither has this. The lower two wall tabs sit inside the walls' 0.25 in epoxy band, so they don't show.

To go back, restore `riverdale_hall_detail.obj`, `riverdale_hall_fine.obj`, `riverdale.scene` and the two tools from git. Other sessions' Riverdale changes were uncommitted in all of them on the day, so check the diff first.

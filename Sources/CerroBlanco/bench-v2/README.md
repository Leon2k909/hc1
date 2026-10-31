# Cerro Blanco bench v2

Created 2026-10-30, as a trial. **Rejected by the user the same day**, after seeing both side by side in s&box: the old bench looks better. It is not in the game: the
map still builds the old bench, and no map file changed. Nothing uses these files.

The museum's long bench, placed ten times on Cerro Blanco. The old one (`bench` in `Tools/cerroblanco_parts.py`, 70 triangles) is one stone box and
five wooden boxes. This keeps its 96 length and 18.6 height and rebuilds it: a honed travertine block with bedding and small pores, jointed in two, on a
shadow gap at the floor; five teak slats with eased edges and real end grain, gone silver where the weather reaches, on two stainless rails, screwed down.
No lettering.

**The sheets' "before" is wrong, so don't judge from them.** The scene draws `cerroblanco_dressing_v2` with the materials in `materials/cerroblanco/quality-v1/`,
and `read_old.py` and `render_bench.py` used the base model's materials instead. They show flat brown slats where the game has real wood grain, and that's the
old bench looking worse than it is. `output/asset-improvement-20261030/cerroblanco-bench/ingame/old-front-new-behind.png` is the fair comparison, from s&box.

- Triangles: 1,454 / 524 / 304 / 156 (LOD 0-3), against the old 70 with no LODs. One material, one 2048 atlas, about 16 px/in.
- `bench.py` builds, bakes and exports. `paint_bench.py` paints. `render_bench.py` renders. `verify_bench.py` checks. `read_old.py` makes the old bench
  from the map's own code, for the "before". `finish.ps1 -Old -Build` runs it all at idle priority and stops at the first step that fails.
- Work files and sheets are in `output/asset-improvement-20261030/cerroblanco-bench/final/`.

## Checked

From the files, by `verify_bench.py`: 0 of 8 solid pieces inside out on LOD 0, within 0.05 of the old bounds, normals, UVs in range, every texture and mesh
named exists, and no map asks for it. I looked at Blender renders of LOD 2 from one angle: no holes.

Compiled by the editor on 2026-10-30 with no errors reported, and seen there beside the old bench, placed by hand for the comparison and not saved into the map.

## Not checked

- Seen only in the editor, from one courtyard spot, without the match camera's finish. Not seen in a match.
- `switch_threshold`s (30, 90, 220) are estimates.

## To install it

The old bench is merged into `cerroblanco_dressing`, so `bench` in `Tools/cerroblanco_parts.py` would keep its collision box and stop drawing, each bench would
become a placed copy of this model, and the map would be regenerated, which needs the editor to compile. The map's benches run from 72 to 110 long. Scaling this along
X covers that but stretches the grain up to 25%, and three builds would be cleaner if that shows.

## Known weaknesses

- **In s&box the stone is too yellow and its bands too strong.** It doesn't match the map's own stone, which the old bench does, and the bands read a little like wood.
- A few bright, thin chips along its top edge look slightly dashed.

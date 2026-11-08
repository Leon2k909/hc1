# Riverside spawn-pad watch deck v1 — timber rebuild (approved and kept, 2026-11-06)

**Status: approved by the user on 2026-11-06 ("lets use the new one"), with both assets kept. Not committed.**
- New: `models/props/riverside/watch_deck_v1/deck.vmdl`, placed by the scene's "Watch Deck" object.
- Old, kept unused: `models/props/riverside/watch_deck_original/deck_original.vmdl` (812 triangles, `rs_wood` + `rs_concrete`,
  same origin as the new one: place it at world (-445, -60, 96) and it stands exactly where the old deck did). Made by
  `keep_original.py`; it loads with no errors (812 triangles).
- `Tools/riverside_map.py` now matches: the Pad no longer draws the old render, `watch_deck_objects()` writes the scene
  object (the scene is rewritten whole on every run), and `OLD_DECK_IN_PAD = True` brings the old look back. Checked offline
  against the previous generator: with the flag on the polygons, UVs and normals are identical to before; with it off the
  deck draws nothing and its collision, rail clips and sandbags are identical.
- The generator was not run (it rewrites the whole map); the Pad OBJ and scene were edited in place as described below, which
  is what the generator now produces for them.

## Why this prop

The deck on the Riverside spawn pad is the first thing every player sees and stands on: eye level, on the main route.
The old one was four thin posts, flat joists, boards with a pinstripe grain, pipe-style rails and a steel-style stair, all
the same thin `rs_wood` stripes (`riverside_map.watch_deck`, 812 triangles merged into the Pad mesh).

## What changed

| | before | after |
|---|---|---|
| geometry | 812 triangles inside `Assets/models/maps/riverside/riverside_pad.obj` (48 `rs_concrete`, 764 `rs_wood`) | `models/props/riverside/watch_deck_v1/deck.vmdl`, LOD0 8,796 / LOD1 5,024 / LOD2 1,728 triangles (switch 0 / 35 / 80) |
| frame | four thin posts, flat joists | concrete piers with bolted steel base plates, six 6x6 posts, doubled 2x8 beams, 2x8 rim boards, 2x6 joists at 16 in, X braces on both sides |
| top | boards with a stripe grain | sixteen gapped 5/4 boards cut from the approved crate-atlas plank crops, screws on LOD0 |
| rails | pipe-style | 4x4 posts bolted outside the rim, capped, with a mid rail; open at the stair |
| stair | steel-style | three notched 2x12 stringers, two-board treads, ties, posts and sloped handrails, three concrete pavers at the foot |

Unchanged: footprint (96 x 96 in), deck height (60 in over the pad), the stair's 8 x 7.5 in rise and 80 in run, **every
collision shape** (the Pad's collision hulls are separate files and were not touched), the sandbags and lights.
No new textures: the crate atlas (`materials/riverside/crate_v2/crate.vmat`), `materials/lowtide/lt_steel.vmat` and
`materials/riverside/rs_concrete.vmat`.

Installed as scene root **Watch Deck** > **Timber Watch Deck** (one `ModelRenderer`) at world (-445, -60, 96), no
rotation. The old deck's 812 triangles were cut out of the Pad OBJ face line by face line (vertices stay, CRLF kept):
the Pad model goes from 33,152 to 32,340 triangles.

## Before / after

Real editor viewport captures (`screenshot_game`, cropped), same camera pose and same scene for each pair, nothing
retouched. The editor's light gizmos show in both. World poses (engine x, y, z, pitch, yaw):

1. `before-1.png` / `after-1.png`: from the south-east, standing height: (-560, -250, 160), 8, 66
2. `before-2.png` / `after-2.png`: straight up the stair: (-690, -60, 160), 6, 0
3. `before-3.png` / `after-3.png`: from the west, standing height: (-445, 160, 150), 4, -90

`comparison-N.png` puts each pair side by side. `detail-after-deck-top.png` and `detail-after-rear.png` are after-only
close checks. In pair 2 the stair rails look dark because the stair sits in the deck's own shadow; the old rails are dark
there too. All files are in `output/riverside/watch-deck-v1/`.

## Files

- `build.py` writes `Assets/models/props/riverside/watch_deck_v1/` (three LOD OBJs, `deck.vmdl`) and `manifest.json`
  (counts, checks: 0 inward faces, 0 wound/flat faces on every LOD, sha256 of each file).
- `legacy_deck.py` redraws the old deck from commit `3bec244c`'s Tools (`python legacy_deck.py <dir>/Tools`) to find its
  triangles in the Pad; `prepare_install.py` finds them twice (vertex fingerprint and region) and stages the cut Pad OBJ.
- `install.py` / `revert.py` / `editor.py` do the editor work through `sbox-cli --call`; Riverside is brought to the front
  only for the few seconds it needs, then the scene that was in front goes back.
- `compose.py` makes the `comparison-N.png` sheets.
- `output/riverside/watch-deck-v1/install-before/` holds the original Pad OBJ, Pad ModelDoc and Riverside scene.

Shared tracked files this change touches (both were already modified against `HEAD` by other sessions' relief work, so
`git diff` shows more than this change; compare against `install-before/` instead):

| file | sha256 before | sha256 now |
|---|---|---|
| `Assets/models/maps/riverside/riverside_pad.obj` | `236703b9…1bc4088a` | `25b6605e…f2c0845a` |
| `Assets/scenes/maps/Riverside/riverside.scene` | `16574ed7…131a1284` | `2616f03e…c6ab3d1f` |

(Full hashes: `install-plan.json` and `sha256sum` of the files in `install-before/`.)

The scene differs from the saved copy by the 68-line Watch Deck block and one prefab-instance GUID pair that the
editor rewrote when saving (the last entry of a prefab instance's map, around line 14844).

## Revert

```
python Sources/Riverside/watch-deck-v1/revert.py --check          # looks, changes nothing
python Sources/Riverside/watch-deck-v1/revert.py                  # deletes the two objects, restores the Pad OBJ
python Sources/Riverside/watch-deck-v1/revert.py --delete-assets  # ...and deletes Assets/models/props/riverside/watch_deck_v1/
```

It only swaps a file back while it is still exactly what `install.py` wrote, and it compares the editor's copy of the
scene with `riverside.scene` object by object before saving (the editor's "unsaved changes" flag on Riverside is set
without any content difference: 441 objects, 0 differences on 2026-11-06). `--check` was run; the revert itself has not
been run against the live editor. By hand: delete the "Watch Deck" object in Riverside and save, copy
`install-before/riverside_pad.obj` over the Pad OBJ.

## Still to do

Commit together: `Assets/models/props/riverside/watch_deck_v1/`, `.../watch_deck_original/`, `Tools/riverside_map.py`, this
folder and the CLAUDE.md line. The Pad OBJ and `riverside.scene` also hold other sessions' uncommitted Riverside work, so
committing them takes that along.

## Cost, new vs old (measured 2026-11-06)

- Triangles: old 812 (764 `rs_wood`, 48 `rs_concrete`, merged into the Pad, one LOD). New LOD0 8,796 (steel 3,988: 98 bolt
  heads 2,940, 208 screws 832, 18 base plates 216; wood 4,412; concrete 396), LOD1 5,024 (bolts and screws gone), LOD2 1,728
  (bevels gone), switching at 0 / 35 / 80.
- Textures: old `rs_wood` 1024x1024 x3 maps; new wood is the crate atlas, 2048x2048 x5 maps (colour, normal, roughness,
  metalness, AO); steel has no texture files (flat values); concrete is shared. All of them are already loaded by other
  Riverside models (the crates, steps, board and fence use the atlas; 64 models use `rs_wood`), so the swap adds no new
  texture to the map. The new deck is its own object: 3 material draws against none extra for the old one.

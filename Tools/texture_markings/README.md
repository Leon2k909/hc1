# Texture markings: no writing, numbers or logos on ripped guns and parts

The guns and parts ported from Call of Duty rips (the AK family: AK-47, AKS-74U, PP-19-01 Vityaz, RPK, PP-19 Bizon,
AK-105, Vepr-12; the M16A4; the FN P90; the MWII M4 parts and optics in `attachments/mw2022`; the MW2019 MP5 parts in
`attachments/mpapa5`) must not carry CoD's writing, numbers, logos or labels, so the game isn't a CoD clone (the user's rule, 2026-09-26). This folder
holds the tools and the record of what was removed: `specs/*.json`, one per group of materials.

## What to remove, what to keep

Remove anything that reads as writing or identifies a maker or origin:
- letters and words in any script (Latin, Cyrillic, Korean, Chinese...), including selector markings (АВ/ОД, 련/단,
  SAFE/SEMI/AUTO, F/S/A);
- numbers: serial, part, calibre and date stamps, range and sight scale numbers, capacity numbers;
- logos, brand emblems, insignia, arsenal and factory marks (stars in circles, triangles or arrows in circles or ovals,
  stylised initials), proof marks;
- QR codes, barcodes, data matrices, warning and caution labels with writing, sticker labels with writing;
- CoD's own iconography (stylised skulls and brand marks on stickers).

Keep the surface: screws, rivets, holes, pins, knurling, grooves, rail slots, seams, welds, wear, scratches, dirt,
paint chips, grip stippling, and plain marks without writing (a lone line, dot, arrow or notch, e.g. a selector
position line). Anything a player could read or recognise in the gunsmith's close-up has to go; illegible specks don't.

## Tools

Run from this folder. Paths to .vmat files are relative to `Assets`. Previews and backups go to `HC1_TEXTURE_WORK`
(default `%TEMP%/hc1_texture_markings`), not the repo.

- `python tiles.py <vmat>...` writes `out/<stem>/overview.png` plus `full.png` (maps up to 1024 px) or full-resolution
  `tile_<x>_<y>.png` crops. They show the colour map shaded by the normal map (light from the top left), so engraving
  shows as well as print. The grid is in colour-map pixels: cyan labels are x, magenta y.
- `python zoom.py <vmat> <x> <y> <w> <h> [--scale N] [--map TextureNormal] [--raw]` magnifies a crop, with a finer grid.
- `python clean.py <spec.json> [--dry] [--only <vmat stem>]` removes a spec's marks and writes before/after previews
  (`out/<stem>/fix_<n>_<x>_<y>.png`, before above after). The spec format is in `markings.py`. Each region is covered
  with the same shape copied from clean surface nearby (picked automatically, or `"offset": [dx, dy]`), plus a smooth
  correction so it meets its surroundings; every map of the material gets the same edit. `"mode": "glyphs"` replaces
  only the mark's own pixels, for marks on detail worth keeping. `"ring": [cx, cy, r0, r1, a0, a1]` limits a region
  to a band round a centre, from angle a0 round to a1, for lettering round a ring (a drum's face, a shell's
  headstamp): it's covered a sector at a time, each copied from plain surface, as in `specs/vepr12.json`. Fit the
  centre to the grooves or rim in the normal map first; a few pixels off and the band clips the lettering at one end.
  `"clear_translucency": true` makes a decal material invisible.
- `python restore.py <vmat>` puts a material's maps back from the backup that `clean.py` took before its first write.
- `python clean.py --check` lists the materials in `specs/` whose maps aren't as cleaned (`cleaned.json` has each map's
  pixel hash before and after). `python clean.py --all` cleans every one that's back to the rip's.

## The converters clean up after themselves

`Tools/kastov_materials.py` (AK-47), `Tools/ks74u_assets.build_material` (AKS-74U, Vityaz, RPK, Bizon, AK-105,
Vepr-12, M16A4, P90) and `Sources/MW2022/convert_materials.py` (M4 parts and optics) write every texture again from the rip
when they're run, so they call `markings.after_rip()`, which cleans each material that has a spec. The result depends only on the rip's
pixels and the spec, so it comes out the same every time. A material with no spec is left as ripped, with no warning:
the converter cleaning up doesn't mean a new port is clean. The MP5 parts' textures aren't rewritten by any script.

`convert_materials.py` hides the MWII optics' decal sheets (`*_decals`, all writing and part numbers) with
`hidden.vmat` instead of converting them: they're overlays about 0.003 units above the optic's body, so nothing shows
through. Their textures were deleted.

## A new port

Before a new gun or part ships, go through every material it uses, the shells and magazines included: `tiles.py`, `zoom.py` on anything suspicious, add
its regions to a spec, `clean.py --dry` and look at every preview (the mark gone with no outline left, no screw or edge
copied into the patch, edges crossing it still lined up, no smudge), then `clean.py` without `--dry`. If its converter
writes textures, call `markings.after_rip()` there as the others do.

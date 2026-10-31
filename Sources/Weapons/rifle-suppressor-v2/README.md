# HC1 rifle suppressor v2

Created 2026-10-30. The rebuilt `attachments/hc1/rifle_suppressor`. The user first chose it over the old one from Blender sheets, then saw both in s&box and said to keep both.
So it's its own gunsmith part, "HC1 Pattern 6 Suppressor" (`Assets/gunsmith/hc1/rifle_suppressor_pattern6/`), and "HC1 Rifle Suppressor" has the old model again.

**Few players will see it.** It fits only the SCAR-H, which is `IsWip`: tagged WIP in the gunsmith, and kept out of Tactical
buying, the Zombies crate and wall-buys, and the bots. A player has to choose that gun, then this part out of its three
suppressors. It was picked for how weak it looked, before that was checked. Check `IsWip` first when picking a gun part.

The old one is a plain tube in flat colour with a shared atlas, no normal or metalness map. This keeps its layout and size
and rebuilds it: threaded socket, locking collar with a knurled band and its 16 grip bars, shoulder, a can with witness grooves
and a fluted middle, a riveted plate, an end cap with true wrench flats. The wear tells one story, heat: a dark ceramic coat
that's sound at the rear, chalks and flakes toward the muzzle, with temper colours in the bare steel and soot in the flutes.

It's game art, exterior only. The bore and socket are blind holes and nothing inside is modelled. Lettering is invented and
plainly descriptive ("PATTERN 6", "LOT 4408", "HOT WHEN FIRED"). No brands.

## Files

- Triangles: 12,198 / 7,248 / 3,378 / 1,550 (LOD 0-3), against the old 13,364 with no LODs.
- One material, `rs_can`, its own 1024 atlas at about 82 px/in: colour, normal, roughness, metalness, AO. The old one shares
  `hc1_attachment_atlas_color.png` with the other HC1 parts, so this adds texture memory the old one didn't need.
- `suppressor.py` builds, bakes and exports. `paint_suppressor.py` paints. `render_suppressor.py` and `make_sheets.py` make the
  comparison. `verify_suppressor.py` checks the files. They import `Sources/Gameplay/capture-flag-v2/`'s `build.py` and `paint.py`.
- Rerunning the build can change the unwrap, so bake and paint after it. The export refuses to run otherwise.
- Work files and renders are in `output/asset-improvement-20261030/rifle-suppressor/`.

The `MuzzleShift` of 6.26 still holds, since the length is unchanged. `Tools/part_masses.py` names the `.gnsmth`, not the model, so
it didn't need changing.

## Checked

From the files, by `verify_suppressor.py`: 0 of 25 solid pieces inside out on LOD 0, length within 0.02 of the old, radius no
more than the old's, normals, UVs in range, every texture and mesh the vmat and vmdl name exists, and the prefab and audit tool
ask for v2. I looked at Blender renders of LODs 1-3 from one angle: no holes.

## Not checked

- **Seen in the editor only, floating beside the old one**, on 2026-10-30: compiled with no errors, not too dark, and its lettering reads the right way. Nothing has been seen on the gun. The sheets' images are Cycles renders, with ray-traced light
  that flatters any asset, of the suppressor alone. The "from behind" camera is my estimate of the player's angle.
- The old model's roughness in the renders is its vmats' scale factor taken as flat roughness, since the default texture it
  multiplies wasn't read. It may look a little different in the engine.
- `switch_threshold`s (40, 120, 300) are estimates.

## Known weaknesses

- **The muzzle end lost detail.** The soot is heavy enough that the wrench flats and dimples nearly vanish, and the old model's
  brighter face arguably reads better there. Players mostly see the other end.
- The burnt band just behind the cap is blotchy, with chunky dark flakes.
- A couple of grip bars catch the sky and look pale. That's a reflection off their flat tops, and may not happen in a map.
- The socket's inner edge looks slightly lumpy up close. The gun hides it when fitted.
- LOD 3 is visibly angular and has lost the grip bars. It's meant for far away, but the distance is an estimate.
- `compact_suppressor` is the same old art, and would no longer match this one beside it in the gunsmith.

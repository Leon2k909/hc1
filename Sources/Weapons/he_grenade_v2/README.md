# Frag grenade v2: the K-31 skin

Created 2026-10-30. The user liked both grenades, so this one is now a skin the player can pick (see
`docs/notes/161-equipment-skins-equipmentskins-the-gear-picker.md`). The cloud model
`models/weapons/sbox_grenade_explosive/w_he_grenade.vmdl` stays as the Standard skin and the default, and the prefabs still
point at it. Nothing is committed.

Players hold this grenade close in first person. The old one has a body of about 24 sides, so its outline is faceted, plus
squiggly scratches, blurry lettering and real designations ("M67", "FUZE M213", "COMP B"). The new one is a generic
fictional grenade, modelled from the outside only: a 60-sided body with a lapped equator seam, a turned nut and lock ring,
a cast head, a sheet steel lever with a curl and ears, and a doubled-wire pull pin on a ring. Its lettering is made up:
"HAND FRAG K-31", "LOT RZD 26-0417" and "RZD K-31 / 26-0417" stamped on the lever. "K-31" happens to match the name of a
Swiss rifle, the K31, so change it in `paint_grenade.py` if that matters.

- Triangles, LOD 0-2: 11,962 / 5,932 / 1,380, against 2,777 / 1,535 / 464.
- One material with 2048 maps (colour, roughness, metalness, normal, AO), against the old 1024. About 211 px/in, with the
  atlas only 35% full, so a tighter packer would sharpen it.
- Same origin and axes. Same three body groups in the same order (`grenade`, `spoon`, `pin`, the last two with an empty
  second choice), so the prefabs' `BodyGroups: 11` should still show all three. Same mesh names. LOD distances 0, 4 and 8,
  which look like the old model's own (the last values in its data block).
- No physics in the model, as far as the old one's PHYS block shows (it lists no shapes). The prefabs bring their own
  collider, which isn't changed.

## Checked, from the files
`verify_grenade.py` passes: 0 inside out on all three LOD 0 meshes, every group within 0.05 in of the old group's bounds,
body groups in order, all 5 textures and all 8 meshes the files name exist, the grenade's prefabs and `.equip` unchanged.
No `_c` files in the model's folder when this was written.

## Not checked
- **Never compiled or seen in s&box.** The sheets are Blender Cycles renders with matched camera, light and exposure, and
  Cycles flatters any asset.
- The vmdl has never been read by ModelDoc, so the body group mask of 11 and the LOD distances are unproven.
- Not seen in the hand: the fingers against the new lever and ring are unchecked. The neck is slimmer than the old one's.

## Known flaws
- LOD 2 shears the lettering and the band if seen close up. It should only appear far away.
- The lever's worn lip looks slightly dashed from the pin side.
- The end of one pin leg catches a tiny white highlight in the close top view.

## The "before" renders
`read_old.py` decodes the old mesh and textures from the compiled cloud files (meshopt and LZ4, no editor), and
`old_maps.py` unpacks them for Blender. It assumes s&box's packing: hemi-octahedral normal in RG, roughness in B, metalness
in the colour map's alpha. The result looks right, but that's a judgement from the renders.

## Files
`grenade.py` builds, bakes and exports. `paint_grenade.py` paints. `render_grenade.py` renders, `sheet.py` makes the sheets,
`finish.ps1` runs the repaint, renders and checks. Both use `Sources/Gameplay/capture-flag-v2/` as a toolkit. Rerunning the
build can change the unwrap, so bake and paint after it: the export refuses to run otherwise. Work files and sheets are in
`output/asset-improvement-20261030/he-grenade/`.

## To make it the default
Move its line first in `EquipmentSkins.All`. It only needs compiling once for the skin to work: until then, picking it shows
the stock model. `picker_pictures.py` makes the picker's two pictures from the `picture` view of `render_grenade.py`.

# Incendiary grenade v2 (the K-52 skin)

Created 2026-10-30. The user liked both this and the old cloud model ("i like both do skins"), so it's a skin in `EquipmentSkins`, beside
the old one, which stays the default Standard. Nothing replaces anything, no prefab changed, and the other session's red and grey AN-M14
versions (`Sources/Weapons/thermite_grenade_v2/`) are further skins of the same item. Players pick it in the loadout's LETHAL picker.

The old model, `models/weapons/sbox_grenade_incendiary/w_incendiary_grenade.vmdl`, is not weak: it's a properly textured 3,498 triangles.
So this is a modest step: a turned fuze, a formed lever, a filler plug, rolled beads and a black band, in the same brick red so it still
reads as the red can. Its lettering is invented ("INCENDIARY", "THERMITE K-52", "KEEP CLEAR WHEN LIT"), where the old can has the real
designations "AN-M14" and "TH3". "K-52" is made up, but check it doesn't clash if that matters.

- Triangles: 12,744 / 6,324 / 1,442 (LOD 0-2), against the old 3,498 / 1,536 / 720. One material, 2048 maps, about 139 px/in, atlas 33% full.
- Same origin and axes as the old model, with its three body groups in order, so the prefabs' mask of 11 should still show all three.
- The burnt-out canister is tinted by `ThermiteGrenade` through `ModelRenderer.Tint`, so the material keeps tint amount 1.

## How it's built

The old incendiary and smoke grenades are the same mesh family, to the thousandth of an inch, so this runs the smoke grenade v2's scripts
with its names, can, colours and lettering changed (`adapt.py`). It reads a frozen copy in `base/`, because those scripts were being edited
by their owner: a moving base would change this model without anyone asking. Each change must find its text or the run stops.

`finish.ps1 -Build -Old` runs everything at idle priority, and stops at the first step that fails. `picker_pictures.py` makes the picker's
two pictures. Work files and sheets are in `output/asset-improvement-20261030/incendiary-grenade/final/`.

## Checked

From the files, by `verify_incendiary.py`: 0 inside out on all three LOD 0 meshes, every group within 0.05 of the old group's bounds, body
groups in order, every texture and mesh named exists, and the grenade's prefabs and `.equip` are unchanged.

## Not checked

- **Never compiled or seen in s&box.** No editor was allowed, and no `_c` files exist. Until it compiles, picking K-52 shows the stock model.
- The new `EquipmentSkins` rows haven't been compiled either, and the picker's layout with this many rows hasn't been seen.
- Not seen in the hand, on the body, thrown or dropped. The sheets are Blender Cycles renders, which flatter any asset.

## Known flaws

- Pale dust on the top plate still looks a little pink close up.
- The pull pin catches a tiny white highlight in the close top view.
- The lever's worn edge looks slightly dashed.

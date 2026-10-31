# Flashbang v2

Created 2026-10-30. The user liked both this and the old one ("i like both of those, they should be skins"), so both are skins in the loadout's gear picker: Standard (the cloud model, and the
default) and K-47 (this). See `docs/notes/161-equipment-skins-equipmentskins-the-gear-picker.md`. The prefabs and `flashbang_grenade.equip` still name the cloud model, which `EquipmentSkins.Apply`
swaps by name. The comparison sheets are in `output/asset-improvement-20261030/flashbang/final/`.

## How much it gains

The old model, `models/weapons/sbox_grenade_flash/w_flash_grenade`, was **not weak**: its worn metal has more richness than this one's paint. What this adds is twice the texture size, truly round
drilled ports with a can behind them, turned hex caps, a family look with the frag v2, and invented lettering in place of the old model's real "FUZE" markings.

## What it is

A generic fictional stun grenade: a steel tube with three rows of six ports between two hex caps turned from bar, a can inside, a phosphated fuze shared with the frag v2, a pressed lever, a plated pin
and ring. Lettering is made up: "K-47 STUN", "RZD 26-1182", "LOT 1182".

- Same origin and axes. It keeps the old model's three body groups in order (grenade, spoon, pin), so the prefabs' mask of 11 still shows all three.
- One material and one 2048 atlas. 12,110 / 6,006 / 1,362 triangles by LOD, against the old model's 5,572 at its closest.

## Pipeline

Copied from `Sources/Weapons/he_grenade_v2/`, with the geometry and the paint's shape-dependent parts rewritten. `flash.py` builds, bakes and exports to the work folder; `paint_flash.py` paints; `finish.ps1`
paints, exports, renders and checks; `install.ps1` copies the export into `Assets/Weapons/Throwable/Flashbang/flashbang_v2/`; `picker_pictures.py` makes the picker's two images. Rerunning the build can
change the unwrap, so bake and paint after it: the export refuses to run otherwise.

- The tube's skin is told from its ports by distance from each port's centre line. Telling it by which way a face looks or how far out it is painted the big triangles round each port as if they were the port.

## Checked and not checked

Checked from the files by `verify_flash.py`: LOD 0 of each body group has 0 pieces inside out; each group stays within 0.05 in of the old model's bounds; the body groups are in order, with the empty second
choices; every file named exists; the prefabs still name the stock model, as a skin needs.

**Not checked: it has not been seen in s&box.** The images are Blender Cycles renders. Not known in the engine: the hand's grip on the new lever, the throw animation's pin and spoon switches, and the LOD
thresholds. LOD 2 is rough up close (its ports go octagonal and the band's edge wanders), so check it's only used far away.

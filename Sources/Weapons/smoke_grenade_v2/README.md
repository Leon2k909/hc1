# Smoke grenade v2

Created 2026-10-30. The user liked both this and the old one, so both are skins in the loadout's gear picker: Standard (the cloud model, and the default) and K-44 (this). See
`docs/notes/161-equipment-skins-equipmentskins-the-gear-picker.md`. The prefabs and `smoke_grenade.equip` still name the cloud model, which `EquipmentSkins.Apply` swaps by name. The comparison sheets are in
`output/asset-improvement-20261030/smoke-grenade/final/`.

## Why this one, and how much it gains

Every mode with grenades shows it: in the hand, thrown, and lying on the ground while it pours smoke. But the old model, `models/weapons/sbox_grenade_smoke/w_smoke_grenade`, was
**not weak**: it's a properly textured 1,670 + 944 + 884 triangle model with LODs. This is a smaller step up than the other rebuilds. What it adds is real vents, a turned fuze
well, a formed lever, a family look with the frag v2, and invented lettering in place of the old model's real "M18" and "M201A1" designations.

## What it is

A generic fictional screening-smoke can: rolled chimes, a white top and band that say what's inside, four collared vents, a phosphated fuze, a pressed lever, a plated pin and ring.
Lettering is made up: "SMOKE SCREENING K-44", "WHITE HC", "LOT RZD 26-0418".

- Same origin and axes. It keeps the old model's three body groups in order (grenade, spoon, pin), so the prefabs' mask of 11 still shows all three.
- One material and one 2048 atlas, about 138 px/in (the packing trick from the frag v2).

## Pipeline

Copied from `Sources/Weapons/he_grenade_v2/`, with the geometry and the paint's shape-dependent parts rewritten. `finish.ps1 [-Build] [-Old]` runs it all in the background at idle
priority. `read_old.py` and `old_maps.py` unpack the old model for the "before". Rerunning the build can change the unwrap, so bake and paint after it: the export refuses to run otherwise.

## Checked and not checked

Checked from the files by `verify_smoke.py`: LOD 0 of each body group has 0 pieces inside out; each group stays within 0.05 of the old model's bounds; the body groups are in order, with
the empty second choices; every file named exists; the prefabs still name the stock model, as a skin needs.

**Not checked: it has not been compiled or seen in s&box.** The images are Blender Cycles renders. Not known in the engine: the hand's grip on the new fuze, the throw animation's
pin and spoon switches, and the LOD thresholds.

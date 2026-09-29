# FAMAS F1 development asset

## In game

- Primary assault rifle: `weapons/famas/famas.equip`, displayed as **FAMAS F1**.
- 25-round magazine; automatic, three-round burst and semi-automatic modes; 1,000 rpm and 930 m/s.
- Imported hip, ADS, fire, draw and two reload animations, retargeted to the existing arms. Existing M4 sprint motion is reused.
- The port uses the pack's carry-handle rail and folding sights. This is an accessorized F1 representation, not a museum-accurate factory model.
- Optic, muzzle and laser mounts accept the existing compatible parts. Ammunition and cosmetic customization use the normal Gunsmith systems. The pistol grip remains integral to the rifle.
- Gunsmith also offers ten weapon-specific parts: Compact Short, Lightweight Long and Heavy Long barrels; Cutaway, Padded and Weighted stocks; 50/60-round magazines; Classic Carry Handle and Low Profile Rail. These add Barrel, Stock, Magazine and Rail to the existing four Build categories.
- These parts replace the corresponding meshes on both models. Muzzle devices follow barrel length, extended magazines select their matching empty reloads and foley, and the low rail changes both the optic mount and ADS offsets. Tactical reloads share the original clip because the source has no separate tactical variants.
- Gameplay damage, recoil, reload times, ballistic coefficient, zero and price are game tuning.

The F1's capacity, cyclic rate and muzzle velocity are based on the [French Army's FAMAS page](https://www.defense.gouv.fr/terre/nos-materiels/nos-equipements-terre/nos-armes/famas).

## Source and rights

The source is the locally downloaded [MW2019 Assault Rifles pack, Workshop 2528829149](https://steamcommunity.com/sharedfiles/filedetails/?id=2528829149), using `v_falpha`, the standard magazine and barrel, and their textures/animations/sounds. The laser clamp texture comes from shared pack 2459720887.

These are CoD-derived development assets. A real firearm name and removal of fictional branding do not establish permission to distribute the models, textures, sounds or animation. Original or appropriately licensed replacements are still needed before a release can be treated as cleared.

The small FSS stamp in the upper texture was removed with imagegen in both color and normal maps. Only the 48 by 36 pixel rectangle at (286, 982) was composited from each generated edit, keeping every pixel outside that rectangle unchanged. The cleaned 1024-square maps are preserved in `Sources/FAMAS/branding`; the material builder restores these after conversion so regeneration does not reintroduce the stamp. Other UV islands and the normal-map convention are unchanged.

## Rebuild

The existing tools directory is `D:/tmp/hc1-mw22-tools`. Extracted sources are under `extracted/2528829149` and `extracted/2459720887`. Crowbar decompiles the FAMAS model and attachment models into `decompiled/falpha`. The attachment preparation step maps the low rail's replacement charging assembly to the original animated charging-handle bone. The integral factory stock is separated by its source `tag_stock_hide` weights.

From the project root:

```powershell
rtk proxy python Tools/famas_attachments.py
rtk proxy python Tools/famas_assets.py
rtk proxy python Tools/port_kastov.py --weapon famas
rtk proxy python Tools/kastov_vmdl.py --weapon famas
rtk proxy python Tools/kastov_animgraph.py --weapon famas
rtk proxy python Tools/kastov_prefabs.py --weapon famas
```

The definitions are in `kastov_weapons.FAMAS` and `kastov_prefabs.PREFABS["famas"]`. The measured factory mesh mask is **153231489**. Optic ADS correction is `(3.305, 0, -0.418)`. The low rail adds `(-0.605, 0, -1.338)` at the optic mount, `(0.605, 0, 1.338)` to optical ADS, and `(0, 0, 1.669)` to iron ADS. The latter follows the measured sight geometry, whose front post is at `z=-1.6623` in the uncorrected ADS pose.

## Verification

`Editor/Hc1FamasQa.cs` provides isolated scene checks that do not move the live player or change saved loadouts:

- `hc1_famas_compile`: registers and compiles materials, sounds, models, animation graph, prefabs and equipment; refreshes shared part eligibility.
- `hc1_famas_check world` / `left`: checks primary-picker availability, 25 rounds, fire modes, model and factory bodygroups, then renders each side.
- `hc1_famas_check hip` / `ads`: renders the actual retargeted first-person sequences and merged arms.
- `hc1_famas_check reload 0.5` / `reload_empty 0.75`: renders the two reloads at representative points.
- A third argument accepts a `.gnsmth` resource path. The check equips it, verifies the fitted bodygroups, removes it and verifies the defaults are restored, then fits it for the render. Optic ADS also measures the reticle bone against the camera axis.

Output is in `output/famas`. Checked a mini red dot, slim suppressor and compact laser, including the raised/folded sight, muzzle tip and laser clamp switches. Iron sight front-post alignment was visually checked at screen center. This is an asset/pose check, not a full multiplayer match test.

Final validation on 2026-09-28: the game project built with 0 errors (82 warnings), and the editor project including dependencies built with 0 errors (98 warnings). Asset compilation and all checks above passed. The final mini-dot reticle target was `(6.8762, 0, -0.0003)` in camera space. An earlier unrelated flashbang compile error was resolved by concurrent work; no flashbang code was changed by this addition.

### Attachment expansion validation

`Editor/Hc1FamasAttachmentsQa.cs` adds `hc1_famas_parts_check`: ten registered parts, eight Build slots, unlock levels, equip/reset on both models, magazine poses/foley, and both equip orders for muzzle/barrel and optic/rail combinations. `hc1_famas_loadout_check` verifies actual 50/60-round capacity, matching reload selection, no free ammunition from switching magazines, restoring the factory magazine, and saved rail ADS. It restores all temporarily changed cookies and the current-pawn reference in `finally`.

`hc1_famas_check` also accepts an optional fourth argument containing a rail resource path. Fresh low-rail iron and optic ADS renders passed; the wide-window mini-dot target is `(6.7252, 0, -0.0003)`. The ten part checks and loadout checks passed, as did the M16 attachment suite as a shared-bodygroup regression check. Both magazine empty reloads were rendered from the actual sequences. Final editor build including game dependencies: 0 errors, 85 warnings. These checks are isolated scene tests, not a full multiplayer match.

# AK-47 Gunsmith parts

Source: the AK-47 already used by the game, Workshop 3803722029 (mg_mw4_ak47).
This integrates 13 previously unused parts: six stocks, three rear grips, three magazines, one short barrel.
Generic descriptive names are used in the menu. This work does not establish commercial asset rights.

## Import
- Decompile the selected models/dqr/mw4/ak47 models to D:/tmp/hc1-mw22-tools/decompiled/kastov.
- Run python Tools/ak47_gunsmith.py.
- The builder preserves the existing gameplay tuning and factory animation clips.
- The polymer folding and lightweight skeleton stocks enable the source receiver adapter.
- The short barrel retains the factory grip and laser attachment transforms. Its muzzle mount moves -4.976562 units.
- Other pack barrels move the support hand or rails and need separate fitting before they can be enabled.
- The extended box and drum have their own normal/empty reload clips and frame-timed foley.
- One missing source drum-grab sound is replaced by its fast-reload counterpart.
- In-game magazine capacities: 30 polymer, 40 extended, 75 drum.
  Capacity references: [Arsenal](https://arsenal-defense.com/wp-content/uploads/spec-sheets/LMG.pdf),
  [Century Arms](https://www.centuryarms.com/media/Rhet/Resources/Post/Attachment/106026480392288.pdf).

## Editor checks
hc1_ak47_compile registers/compiles the parts.
hc1_ak47_parts_check true 0 checks the factory mesh mask.
Variants 1–6 check all stock/adapter combinations with grips and magazines.
hc1_ak47_parts_check false 1 reload_dmag 0.45 poses the drum reload in an isolated scene.
hc1_ak47_ammo_check checks capacity, reload selection and no refill on swapping.
hc1_ak47_ui_check clicks every option in an open Gunsmith and restores the original choices.

QA artifacts go to output/ak47-gunsmith. Model checks use disposable scenes and do not move the active player.

## Verified 2026-09-28
- View/world default bodygroup mask 340002817; mounted prefab updated too.
- All 13 parts equip and restore Standard; both stock adapters and the short-barrel/suppressor tip precedence pass.
- Six world builds plus first-person idle, ADS and magazine reload poses rendered.
- Magazine capacities 30/40/75 and reload selection/foley pass without adding free ammo.
- Live Gunsmith: nine categories; all 13 options clicked, saved, and restored.
- Editor/game project build: 0 errors.

# AUG Gunsmith parts

Build the AUG-specific stock, barrel and magazine assets with `python Tools/aug_gunsmith.py`, then run `hc1_aug_compile` in the s&box editor.

The AUG now has seven attachment categories: muzzle, barrel, optic, laser, stock, magazine and ammunition. The integrated pistol grip and folding foregrip remain part of the base model and its existing hand animations.

New choices:

- Lightweight Stock: 6% more vertical/horizontal recoil.
- Padded Tactical Stock: 8% less vertical/horizontal recoil.
- Heavy Long Barrel: extended barrel with matching flash hider; shifts attached muzzle devices 6.102728 engine units forward. Existing long-barrel effects increase damage falloff distance by 12%.
- 60 Round Drum: 60 rounds before tuning/chamber, dedicated normal/empty reload clips, 2.3/3.4-second reload times and matching sound events.

Both model prefabs use default bodygroup mask 21665. Muzzle-tip choices are factory=0, long=1, hidden=2. A muzzle attachment hides either factory tip; removing it restores the tip appropriate to the equipped barrel. Standard restores the factory stock, barrel and magazine.

Tactical-stock material rebuilds preserve the cleaned color/normal maps. Their edit prompts and paths are recorded in `output/aug-gunsmith/texture-edit.md`.

Validation: C# build passed; live editor checks passed for both view/world part fitting and resets, default prefab mask, long-barrel/suppressor interaction, 60/30-round capacity, reload selection, sound events and no free ammunition when changing magazines. The live Gunsmith displayed all seven categories and both stock choices saved and previewed correctly. The full UI click test was interrupted when Gunsmith closed; `hc1_aug_ui_check` can repeat it with Gunsmith open and restores the previous saved selections afterward.

Preview: `output/aug-gunsmith/view-2.png` (tactical stock, long barrel, drum); `world-1.png` shows the lightweight stock.

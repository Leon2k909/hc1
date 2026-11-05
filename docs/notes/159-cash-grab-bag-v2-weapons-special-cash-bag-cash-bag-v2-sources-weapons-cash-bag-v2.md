## Cash Grab bag v2 (`weapons/special/cash_bag/cash_bag_v2`, `Sources/Weapons/cash_bag_v2/`, 2026-10-30)
- The mode's objective, in hands, on the back and dropped, replacing the cloud dev model `models/dev/duffelbag/dufflebag_money` (on `dev/white_flat`) at the user's word after a
  before/after. Same origin and about the same size, so the prefabs hold it the same way. The banknotes are invented and copy no real currency.
- Its prefabs keep the old package in `__references`, because `ZombiesPowerUp`'s Point Boost still loads the old model by name. That drop is off today.
- A dropped bag's size comes from `DroppedSize` and `DroppedCenter` in `cash_bag.equip`, which are unchanged. The model's own hull is a new simple box.
- Native full model/material compilation and matched isolated-scene captures checked on 2026-11-04. Still check it in the hands, on the back and dropped in a match.
- Hardware detail pass approved on 2026-11-04: actual zipper teeth (LOD 0 only), open metal pull tabs, and an open two-slot strap adjuster aligned to the strap path.
  Mesh counts 12,616 / 5,504 / 1,924, one material and the existing 2048 maps. Offline geometry/reference/user checks passed; the hull and prefab/equipment
  settings were kept. Current work files and approved native renders are in `output/cash-bag-detail-20261104/work` and `after`. Superseded build/before/comparison
  files and the OLD cash-bag gallery group and label were deleted. The shared cloud dev-bag package remains for the existing Point Boost reference.

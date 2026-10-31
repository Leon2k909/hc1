## Cash Grab bag v2 (`weapons/special/cash_bag/cash_bag_v2`, `Sources/Weapons/cash_bag_v2/`, 2026-10-30)
- The mode's objective, in hands, on the back and dropped, replacing the cloud dev model `models/dev/duffelbag/dufflebag_money` (on `dev/white_flat`) at the user's word after a
  before/after. Same origin and about the same size, so the prefabs hold it the same way. The banknotes are invented and copy no real currency.
- Its prefabs keep the old package in `__references`, because `ZombiesPowerUp`'s Point Boost still loads the old model by name. That drop is off today.
- A dropped bag's size comes from `DroppedSize` and `DroppedCenter` in `cash_bag.equip`, which are unchanged. The model's own hull is a new simple box.
- Built offline and **not yet compiled as an asset or seen in s&box**: check it in the hands, on the back and dropped. See the folder's README.

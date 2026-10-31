## LPG cylinder v2 (`models/props/lowtide/lpg_canister_v2`, `Sources/Lowtide/lpg_canister_v2/`, 2026-10-30)
- Lowtide's four shootable forklift bottles, replacing `lpg_canister`, `_ruptured` and `_cap` at the user's word after a
  before/after. Rollback: `output/asset-improvement-20261030/lpg-canister/retired-lpg_canister/`, and git history.
- The shell profile keeps the stations `LpgCanister.PunctureAt` hard-codes, and the valve stays in the scene's collider at
  y = 17.8. Change those and leaks start in the wrong place. Physics is the old model's, word for word.
- `Tools/lowtide_canisters.py` now only places the bottles and writes their audio. The models come from the Sources folder.
- The scene's references became plain paths, since its old `Id`s would resolve to the old files.
- No impact damage on the intact bottle: shots show through the game's own leak and fire.
- Built offline and **not yet compiled or seen in s&box**: see the folder's README for what is still owed.

# Defuse update

## Playing

- Loadout rounds with one life, two sites, and a first-to-six win condition.
- Slot 5 equips the original RAZED device. Hold primary fire (or Use) inside a site for four seconds to plant.
- The planted device has a 45-second timer. Defenders look at it and hold Use for 7.5 seconds.
- Interrupted plants/defuses release the movement freeze. Planting is restricted to a living, grounded attacker with the device equipped at an active site.
- Attackers win on detonation; defenders win on defuse or expiry of the pre-plant timer. Eliminating attackers after the plant leaves the device running.
- In an unranked editor-hosted Defuse match, `dev_defuse_planter true` (the default) keeps the local host on the attacking team and gives them the bomb each round. `dev_defuse_planter false` restores ordinary assignment. `dev_defuse flatgrass` launches the local test mode.

## Art

- New original geometry: `Assets/Weapons/C4/field_device/field_device.obj` and `.vmdl`.
- Generated albedo: `Assets/Weapons/C4/field_device/field_device_color.png`.
- Generation used the built-in image_gen tool. The complete final prompt is in `Tools/field_device_prompt.txt`.
- Rebuild mesh/material source using `rtk proxy python Tools/build_field_device.py`.
- Prefab setup helpers: `Tools/configure_defuse.py`, then `Tools/configure_defuse_world.py`.
- `held-device.png` and `planted-device.png` are captures from the running game.

## Validation (2026-09-28)

- Project build: succeeded, 0 errors (83 existing warnings).
- Visually checked the held device, both hand grips, procedural planting motion, planted model, and objective HUD.
- Through temporary editor diagnostics, exercised the real host-side objective methods: valid/invalid plant locations, a four-second completed plant, cancellation, holstering during planting, the armed countdown, two-second interrupted defuse, completed 7.5-second defuse, detonation scoring, and automatic cleanup/respawn.
- A completed defuse changed the score from 2–1 to 2–2. The following round restored the local attacker with the bomb and nine bots.
- Fixed allocation selecting a stale pawn during forced respawn; bot refill waits for the previous roster's destruction.
- Removed the broken billboard from the planted beep effect; replaced it with a brief orange light pulse and checked the result in-game.
- Temporary diagnostics and test input components were removed. Damage immunity was switched off after testing.

Physical keyboard/mouse input and a second network client were not verified; the editor bridge's synthetic input did not reach gameplay reliably. Objective logic was exercised through editor diagnostics. Bots retain their existing combat behavior; this update does not add bot planting/defusing AI.

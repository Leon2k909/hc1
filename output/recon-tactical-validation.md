# Hand-launch recon tactical

28 September 2026.

## Use

Select **Recon Drone** in the class's **Tactical** slot. In a match, press the tactical binding (default **6**), hold primary fire to ready it, and release to launch. Secondary fire cancels while readying. The tactical is consumed and the inventory selects a remaining weapon.

## Implementation

- New equipment resource, inventory silhouette, first-person hand model, third-person model and airborne prefab.
- Uses the original textured AER-03 aircraft, resized to a 49 cm wingspan. The propeller remains still in the hand and spins in flight.
- Uses the established throwable animation and hand-local attachment, with smaller movement inertia and a drone-specific grip offset.
- The host launches one aircraft with the player's throw direction and inherited movement velocity. It briefly follows the throw, climbs and circles above the release area.
- It lasts 30 seconds and scans every half second within 1,600 game units. Line-of-sight traces prevent spotting through walls; Ghost blocks player detection. Contacts are shown to the operator's team, or the operator alone in free-for-all.
- Supports player pawns and lightweight combat bots. Replenishing and throwing another replaces that operator's earlier drone.
- Swept collision stops blocked launches; expiry, round reset and loss of the operator clean up the aircraft.
- The overhead streak aircraft remains separate from this tactical item.
- Shared throwable handling now prevents restarting a committed throw and checks the RPC caller before creating a payload.

## Validation

- Game code build passed with 0 errors and 121 warnings.
- Both handheld models, all four equipment prefabs and the equipment resource compiled in the engine.
- Tactical picker availability and portable model bounds verified in an isolated editor scene.
- Idle and ready poses rendered and inspected. Preview files: `recon-tactical-held.png` and `recon-tactical-ready.png`.
- Ready/release state transitions, item visibility after release and hand attachment across 120 movement/turn samples passed.
- A simulated ten-second flight climbed into a stable orbit.
- Detection checks passed for nearby enemies, friendly exclusion, range, enemy-team privacy and wall occlusion.
- Expiry and repeated deployment/round-reset cleanup passed.
- The actual launch factory produced the initialized aircraft. Host-side consumption removed the tactical and deployed the remaining weapon.
- A swept throw into an obstacle stopped the aircraft; removing the operator cleaned up the orphaned drone.
- The temporary editor test command and all isolated test scenes were removed after validation.
- No second-client network test or full live input playthrough was performed; tests used isolated scenes to preserve the running game.
- A separate editor-project build encountered disappearing temporary files belonging to concurrent editor work. The game-code build and isolated engine tests are the verification used here.

Regenerate the models, icon and equipment prefabs with `rtk python Tools/build_recon_tactical.py`.

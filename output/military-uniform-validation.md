# Military uniform replacement

## Implemented

- CT player and bot outfit pools now select the realistic human rig with camouflage shirt and cargo trousers, tan tactical vest, tactical helmet/headset and combat boots.
- Both full-body and first-person body prefab components declare the five clothing resources, so asset dependency discovery includes them.
- Legacy police selections resolve to the military uniform. The player's initial legacy model is retained only to deserialize its authored sockets before migration in `MilitaryUniform.OnStart`.
- Garments bone-merge to the body, follow its shadow mode, and are removed on switching to the other team. Reapplying the same outfit does not duplicate clothing.
- Weapon and holster sockets migrate between skeletons. Player, bot and replay weapon holders use the converted hand offset; hand IK rotations account for the new bone axes.
- ModelPhysics changes model with the renderer. Menu podium police selections also migrate on startup.

## Verified in an isolated editor scene

- Actual player prefab: five clothing pieces on full body and first-person body.
- Military → other team → military removes/reapplies clothing, without duplicates.
- All nine authored weapon/holster sockets survive and attach to valid bones.
- Player ModelPhysics points at the same model as the dressed renderer.
- Native human bot hand offset agrees with the converted player socket.
- Rendered the actual player prefab with M4 world model and corrected left-hand IK; inspected the saved preview.
- Player and bot prefabs successfully recompiled.
- Game project build passed with zero errors at 21:32 on 28 September 2026 (120 existing warnings).

## Remaining validation limit

The final full build at 21:36 is blocked by an unrelated ongoing edit: `Code/Weapons/Grenades/FlashbangGrenade.cs:77` references missing `FlashbangEffect.LifeTime`. This also prevents the editor from loading the newest QA helper. The subsequent bot prefab, hitbox and live ragdoll assertions therefore did not run; do not count them as passed. The latest menu podium change was not visually checked. No editor restart or gameplay interruption was performed. Temporary QA scripts were removed.

The outfit appears on newly spawned characters after the project compiles; characters already alive may retain their previous outfit until respawn.

# Field military kit and store preview

Validated on 28 September 2026, final runtime check at 22:36.

## Changes

- Store Mastery Camo card uses the original 1536 × 1024 artwork instead of the 256 × 256 UI thumbnail texture.
- Field Operator uses the realistic human model, camouflage shirt/trousers, olive combat helmet and tactical vest, fingerless gloves, and boots.
- Player and bot team model pools use the human model. Team selection applies the corresponding uniform style, including first-person player clothing.
- Legacy field models also resolve to the new kit. Model physics and animation settings match the human skeleton.
- Updated gallery portrait, description and translations. The portrait has a new asset path so the running UI does not reuse its old cached image.

## Checks

- `dotnet build Code/razedtest.csproj --no-restore -v minimal`: 0 errors, 82 warnings.
- Player and bot prefabs parse as valid JSON; targeted `git diff --check` passes.
- Isolated engine checks: both uniforms load, all six field garments are present, and switching styles on the same human model rebuilds the clothing.
- Cloned player and bot prefabs: all field clothing dependencies load, Field style applies, and attached model physics uses the matching model.
- Live menu: store artwork and Field Operator selection captured and visually reviewed. The field gallery shows the updated outfit, portrait and description.
- Temporary editor check code and edit scripts removed.

Screenshots: [Field Operator](field-menu.png), [Store](store-sharp.png).

No multiplayer match was started or restarted during these checks.

# Equipment HUD and recon drone validation

Validated 28 September 2026.

## Changes

- Equipment list runs from primary at the top to tactical and lethal at the bottom. Mouse wheel direction follows the displayed order.
- Tactical defaults to **6**, lethal to **7**. Both are editable under input settings and input hints refresh after rebinding.
- Removed a duplicate streak action and assigned its default to **8**, avoiding the existing previous-weapon and utility bindings.
- Added an original textured AER-03 reconnaissance aircraft to the overhead UAV reward: composite fuselage, carbon tail booms, camera pod, navigation markings and animated pusher propeller.
- The host moves one aircraft per team. Repeated rewards refresh it; expiry and round reset remove it.

## Verification

- `dotnet build Code/hc1.csproj --no-restore -v:q -clp:ErrorsOnly -nr:false -p:UseSharedCompilation=false`: passed with 0 errors (119 warnings).
- Engine compiled both models and the prefab. Both models loaded with valid materials.
- Isolated engine scene rendered and visually checked from above and below; corrected mirrored markings and intersecting wing panels.
- Both team orbits have the intended radius and aircraft heading follows the tangent.
- Isolated manager checks passed for repeated reward reuse, simultaneous opposing-team aircraft, reward expiry and round-reset cleanup. These checks used existing local aircraft and did not network-spawn test objects into the live game.
- Runtime input origins confirmed `Slot6=6`, `Slot7=7`, `Scorestreak=8`.
- Temporary editor QA command removed after validation.

## Assets and scope

- Body: 2,646 triangles; propeller: 108 triangles.
- Geometry and procedural textures can be regenerated with `rtk python Tools/build_recon_drone.py`.
- Preview: `recon-drone-preview.png`; underside: `recon-drone-underside.png`.
- Implemented as the overhead UAV reward model, pending clarification about a separately pilotable drone.
- The existing UAV reveal behaviour and 30-second reward duration are retained. This adds the aircraft visual, not a new pilotable or destructible drone mechanic.
- No second-client network session or live inventory interaction test was performed. The active game/editor session was left running.

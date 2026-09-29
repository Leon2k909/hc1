# Smoke grenade validation — 28 September 2026

## Implemented

- White smoke texture and tint, with scene lighting enabled. Removed the old texture's dark edges.
- Emission starts at the canister and builds gradually. Emission ends after 70 seconds; remaining particles fade before the effect is removed at 84 seconds. The spent canister remains for 86 seconds after ignition.
- Shared, host-controlled wind velocity in metres per second, with travelling gusts. Map authors can override the default light breeze using the World Wind component.
- Smooth spatial turbulence, with a different seed for each grenade. Fresh smoke rises; the buoyancy contribution decreases as particles age.
- Approximate shelter attenuation using upwind and overhead traces, and native particle collisions against geometry. Particles ignore their own canister.
- A physical canister follows the animated right-hand grip in first person.

## Verification

- Code build: `dotnet build Code/hc1.csproj --no-restore -v:q -clp:ErrorsOnly -nr:false -p:UseSharedCompilation=false` completed with 0 errors and 117 warnings.
- Smoke particle asset recompiled successfully.
- Live flatgrass inspection confirmed white smoke and a visible held canister. Screenshots: `smoke-white-calm-verified.png` and `smoke-held-canister-verified.png` alongside this note.
- Forward wind produced positive Y drift. Reversing wind produced negative Y drift and particle velocity.
- Calm wind produced zero imposed air velocity, while turbulence and upward motion remained.
- An overhead test collider reduced exposure from 1 to approximately 0.2.
- Separate grenades received different turbulence seeds.
- Initial lifetime sampling (before the burn-duration correction below) showed a gradual rise from 4 particles after one second to approximately 200 after nine seconds, followed by decay to zero. The effect and spent canister expired.
- Final code changes also keep the emission point above the floor when the canister tips and treat a disabled World Wind component as calm. These changes compiled; the final tipped-canister case was not visually rerun.
- Automated input did not trigger a throw. The optional final throw lifecycle check could not run after the local game ended. First-person visibility and the physical grenade's smoke lifecycle were verified independently.
- No second-client multiplayer test was performed.
- Temporary QA commands and prefab-editing scripts were removed after running cleanup to restore saved test settings.

## Scope and limitations

This is a particle approximation, not a 1:1 fluid simulation. Shelter is sampled at the smoke source; it does not solve pressure, ventilation, room filling, humidity or combustion. Native particle collision does not make the rendered sprite volume impermeable to walls. Wind currently drives this smoke effect; other game systems are not automatically connected to it. The burn duration is a representative value within the published range, not a measured replica of an individual grenade. Residual particle lifetime is still a fixed approximation; wind moves the cloud but does not physically calculate its concentration or visibility lifetime.

## Follow-up: burn duration

The original 20-second emission duration was too short for the user's realism requirement. The Army product page linked below lists 55–90 seconds of emission for M83 white screening smoke (and 50–90 seconds for M18 coloured smoke). The asset retains its existing M18 directory/model; the white smoke behaviour uses the M83 as its reference.

- Set emission and burn sound duration to a representative 70 seconds.
- Retimed the normalized emission curve so its original buildup still reaches the 1-, 4- and 8-second milestones. Sustained output continues until 65 seconds, then falls to zero at 70 seconds.
- Extended effect cleanup to 84 seconds and spent-canister cleanup to 86 seconds so neither truncates the burn or the final 13-second particle tail.
- Validation: particle prefab recompiled successfully; parameter checks confirmed emission milestones at 0, 1, 4, 8, 65 and 70 seconds, matching sound duration, and cleanup after the final particle lifetime. Code build passed with 0 errors and 117 warnings. A complete 70-second live burn was not rerun for this timing-only adjustment.

## Follow-up: held canister movement

Fixed the canister sliding during camera movement. Camera setup moves the viewmodel after render-bone world positions have been sampled. The previous attachment copied those stale positions. The item now parents to `hand_R` and calculates its grip in hand-local coordinates, so subsequent camera and skeleton movement carries the item with the hand.

An isolated scene in the running editor reproduced the old error and exercised the actual grip component with the smoke viewmodel prefab:

- A translation and rotation produced a 55.37-unit stale hand-position error before the fix.
- After attachment to the hand, 120 movement/turn samples had a maximum positional discrepancy of 0.000156 units and no measured rotational discrepancy.
- Another 60 samples with the walking bob/inertia animation advancing had a maximum positional discrepancy of 0.000186 units and no measured rotational discrepancy.
- The held item correctly hid in the thrown state, with disabled hands, and without equipment.
- Code build completed with 0 errors and 117 existing warnings. The temporary test scene and command were removed. This was an engine regression check, not a new manual gameplay recording.

## Background references

- [US Army smoke grenade descriptions](https://www.cpeae.army.mil/Project-Offices/PM-CCS/Organizations/PdD-Combat-Armaments-and-Protection-Systems/Products/Grenades/Smoke-Grenades/) describe white smoke for screening.
- [EPA atmospheric transport overview](https://www.epa.gov/cmaq/overview-science-processes-cmaq) describes wind transport and turbulent dispersion.

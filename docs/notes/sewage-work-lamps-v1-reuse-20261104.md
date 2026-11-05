# Sewage caged work lamps v1 reused (2026-11-04)

Installed the existing staged set of 24 caged work lamps after checking available Sewage, Riverside, ReefHall and Ares alternatives. The Sewage version already matched the map's anchors and four lamp colours, so no duplicate geometry or materials were built.

The saved scene's `Waterworks details` renderer uses `models/maps/sewage/work-lamps-v1/base_details.vmdl`. A single `Waterworks caged work lamps` object renders `lamps.vmdl`. The base strips exactly 2,016 old fixture faces and retains all 90,858 unrelated faces and original ModelDoc physics. The original details asset stays available for comparison/reversion.

Native model checks and installed-scene captures passed. Verification confirms all 43 existing light components and eight collision components are unchanged, the saved scene has one lamp group, and both staircase versions remain available with the new version active. Sources, existing-model audit, comparison and checks: `Sources/sewage/work-lamps-v1/` and `output/sewage/work-lamps-v1/current-review/`. User's original active scene is restored after integration.

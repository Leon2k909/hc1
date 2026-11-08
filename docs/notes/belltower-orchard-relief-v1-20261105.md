# Belltower orchard lawn relief — installed review trial, 2026-11-05

Following the Cerro Blanco trial, the user requested the same restrained treatment somewhere suitable
on another map. Belltower's lower orchard has a grass strip beside the cross path, away from the stairs,
buildings, well and furniture. The trial covers plan E -1370..-1150, N -1198..-1080 at base Z -48.
Its smooth crown rises at most 3 inches (7.62 cm), tapering to zero on all four edges. The steepest
triangle is 4.37 degrees. The adjacent gravel path and stair footprints are not modified.

`Tools/belltower_orchard_relief.py` stages a separate 528-triangle overlay using the original lawn
material and `belltower_west` UV phase. It does not regenerate or overwrite any town meshes. The
single static collision-mesh schema derives from the native-compiled Cerro Blanco lawn trial.
The asset is `models/maps/belltower/orchard-relief-v1/orchard_lawn_relief.vmdl`.

The editor asset API imported and compiled the candidate successfully. Native scene tools added one
`Orchard lawn relief - REVIEW TRIAL` object (ID `3ea0e349-1dcc-4624-94a8-03aeac4a6f40`) with a renderer
and static ModelCollider. A runtime trace at world (-1139,1260) hits the trial at Z -44.985, matching
the 3-inch rise plus its 0.015-inch anti-flicker offset. All four boundary-height and slope checks
pass. No existing tree or prop transforms were changed; the small rise meets the orchard trunk bases.

`output/belltower/orchard-relief-v1/` contains geometry checks, the installed object receipt,
runtime hit result, a pre-install scene backup and matched native `before.png`/`after.png` views.
The scene was saved and Belltower play mode was started for inspection. This is still a review trial;
the canonical town generator has not been changed to preserve the extra instance on regeneration.
Native navigation/AI route sweeps and a performance benchmark have not been run. Nothing was staged,
committed or pushed in Git. Cerro Blanco's accepted-for-inspection trial remains installed separately.

To reject this trial, remove the named object through native scene tools and save. Use the backup
as a reference rather than overwriting later unrelated scene work.

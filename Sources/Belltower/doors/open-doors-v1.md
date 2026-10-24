The two north-facing Town Hall entrances now have weathered wooden double doors,
held open at 165 degrees. Each leaf has separate stiles and rails, two recessed
timber panels, butt hinges, bronze knobs and an iron holdback. Both faces are
modelled. The narrow grain strips are applied to individual panel boards rather
than stretched across an entire door.

`Tools/belltower_open_doors.py` owns the independent render model
`models/maps/belltower/belltower_open_doors.vmdl`. `belltower_map.py` generates it
and adds the `Hall Entrance Doors` visual object under `Town` on regeneration.
The installed scene object was created with native `spawn_model` and saved in
the editor. It has one ModelRenderer and no collider, interaction or movement
components. The existing town meshes and gameplay geometry were not replaced.

The staged geometry checks find four leaves, no degenerate faces or physics
shapes, and a central clear width of at least 54 inches in each 56-inch opening.
Native model compilation succeeded. Saved-scene front, oblique and matching
entrance captures are under `output/belltower/quality/open-doors-v1-after/`.
The capture method restores the editor camera, exposure, active scene and play
state. No play session was started or stopped for this change.

`output/belltower/open-doors-v1/scene-before.json` preserves the source before
the edit. Native save refreshed 1,938 resource IDs and four prefab cache entries;
comparison by resource path confirms that all pre-existing scene data is
unchanged. Exactly one visual object was added. The first save request exceeded
its response timeout; the resulting saved source and clean native editor status
were inspected before continuing, and the save mutation was not retried.

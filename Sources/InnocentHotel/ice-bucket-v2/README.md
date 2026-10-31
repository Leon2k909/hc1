# Innocent Hotel ice bucket v2

Created 2026-10-31. **Not installed.** The old model is untouched, nothing is committed, and the user decides.

The old `models/3t/maps/inno_hotel/ice_bucket/ice_bucket.vmdl` is a plain tapered cylinder with two rings, on a full-metal
`steel.vmat`. There are few reflections for that metal to show in this map, so s&box draws it as a black shape with no detail.
Five rooms have one, on the counter by the bathroom. The new one has stitched black vinyl, a rolled brass rim and base band,
brass rings on riveted plates, a gold-foil crest with the map's own name on the front and back, and ice in melt water.

- Triangles 10,692 / 4,728 / 1,434 (LOD 0-2, thresholds 30 and 80), against 4,508 and no LODs. One 2048 atlas at 37 px/in.
- Same origin, handle axis (Y) and footprint as the old model. The ice stands 0.6 in above the old top. No physics of its own.
- `bucket.py` builds, bakes and exports; `paint_bucket.py` paints; `capture_engine.cs.txt` renders old and new in an isolated
  editor scene through the map's real lights and the player camera's look. The toolkit is `Sources/Gameplay/capture-flag-v2/`.
- Metal is about 0.45 rather than 1.0, and vinyl is sRGB 27, because that's what reads in this map.

Why the install differs from other maps: Innocent Hotel is a cloud map (`thieves.innocent_hotel`), so its props can't be cut
from an OBJ. They load as plain `SceneObject`s. The comparison sets `SceneObject.Model` on all five, and the map's own collision
stays. To adopt it, add a small component to `innocent_hotel.scene` that does the same once `MapInstance.IsLoaded` is true, and
check it in a real match. That code isn't written, and the swap has only run in the isolated scene. If the map's author renames
the model in an update, the swap stops matching and the old bucket simply shows again.

Motel isn't a match map (`GameUtils.IsMatchReadyMap`), so it wasn't considered.

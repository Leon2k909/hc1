# Railhead platform PA speaker preview

One speaker on the central platform's column at plan `(7.7,820,214)`, facing
`+e`, is rebuilt with a rounded weather-resistant cabinet, a recessed baffle,
two drivers, a perforated steel grille, retaining screws, a swivel arm and tilt
pivot, and a short cable with a weather boot. The original cabinet's overall
dimensions and downward angle are retained.

The grille's 384 holes are open geometry, including sheet thickness. A fitted
internal baffle exposes the drivers and closes the perimeter behind the grille.
The whole candidate is 17,254 triangles with five private materials. It adds no collision,
lights or audio components. This is one isolated proposal for review; other
speakers, public assets, the scene and generator are unchanged.

The public central dressing model already imports the approved station clock
separately. The private preview retains that import, all remaps and all original
physics. Only the old speaker's 36 render triangles are removed from the actual
current base, `clock-v1/dressing_without_clock.obj`, using exact material and
vertex-position signatures. All vertex/UV/normal records and unrelated faces
are retained. This does not rebuild the shared map.

Commands from the canonical checkout:

```powershell
rtk python Sources/Railhead/pa-speaker-v1/build.py
rtk python Sources/Railhead/pa-speaker-v1/setup.py
rtk python Sources/Railhead/pa-speaker-v1/review.py
rtk python Sources/Railhead/pa-speaker-v1/verify.py
```

Native imports are restricted to the private proposal directories. Compilation
precedes an actual offline play-mode check. Matched front/side screenshots copy
the player's post effects and use identical camera, exposure and map lighting,
with 180 normal texture-streaming frames per view. Texture residency is not
forced. The runner restores the editor's prior scene and stopped state and
aborts on scene switches instead of capturing stale scene objects.

Outputs, hash guard, manifest, comparisons and validation receipt live in
`output/railhead/pa-speaker-v1/`. No frame-time benchmark is claimed.
`check_cavity.py` traces eight rays through the saved mesh's corner perforations
from both review cameras to confirm cabinet surfaces block the background.

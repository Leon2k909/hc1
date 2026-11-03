# Railhead PA speaker refinement

The user asked for more refinement of the first PA speaker proposal. This pass
retains the selected placement, cabinet envelope and downward angle, and adds:

- A tapered moulded housing with smoothly rounded corners.
- One continuous front bezel, a separate panel seam and recessed gasket.
- A finer staggered grille: 781 open perforations with modelled thickness.
- Smaller captive screws, a small PA badge and lower drain weeps.
- Fine paint normal/roughness data, a satin light-grey finish, toothed pivot
  details and a gasketed rear connector cover.

The 32,386-triangle candidate is isolated under `pa-speaker-v2`. The first
proposal remains intact under `pa-speaker-v1`. No public model, scene, other
speaker, collision, light, audio component or map generator is changed.

The native play comparison replaces the same selected speaker with v1 for
`before` and v2 for `after`, retaining the identical trimmed base for both. Its
labels are **PREVIOUS PASS** and **REFINED**, not original legacy versus revised.
It uses the same front/side cameras, exposure, lighting and player post effects,
180 normal streaming frames per view, and no forced texture residency.

The public central dressing model's installed station clock, remaps and physics
are retained. Only the legacy speaker's exact 36 triangle signatures are removed
from a private copy of the actual current base. Original vertex/UV/normal records
and unrelated faces remain intact. `check_cavity.py` checks 222 perimeter-hole
rays against front-facing triangles from both review cameras.

```powershell
rtk python Sources/Railhead/pa-speaker-v2/build.py
rtk python Sources/Railhead/pa-speaker-v2/check_cavity.py
rtk python Sources/Railhead/pa-speaker-v2/setup.py
rtk python Sources/Railhead/pa-speaker-v2/review.py
rtk python Sources/Railhead/pa-speaker-v2/verify.py
```

Imports and compilation use the native editor. The capture runner starts play
only from a stopped editor, restores its previous scene/state, and aborts if
another user changes the session. Outputs, source guard, manifest and receipts
are in `output/railhead/pa-speaker-v2/`. This is a preview for review, with no
frame-time benchmark claimed.

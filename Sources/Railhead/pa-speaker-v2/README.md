# Railhead PA speaker refinement

Approved and installed 2026-11-05. Exactly 36 old speaker faces were removed from the active central dressing import, and native resource saving added one `Central Platform PA Speaker` renderer. The approved model/materials are unchanged. Public dressing compilation and installed detail/side images passed. `verify_installed.py` confirms every other OBJ record, the complete public ModelDoc physics, other scene objects and source-generator persistence. Unused background preview assets are archived outside Assets. Original backups remain under `output/railhead/pa-speaker-v2/install-before`. The user's Cerroblanco scene remained stopped, clean and unchanged. Historical review follows.

Final 2026-11-05 detail/side review images use one identical temporary inspection light for both versions, because the grille is hard to assess in the roof's normal shade. The light exists only in the disposable capture scene; saved map lighting is unchanged. `verify_current.py` passes current hashes, finite/nondegenerate geometry, 100% normal/winding agreement, all 222 cavity rays, native model loading, no added colliders and preserved editor scene/play state. These latest images compare the original legacy speaker against v2.

On 2026-11-05 the existing uninstalled v2 asset was selected for the next map improvement after an upgrade audit. `current_review.py` compares the CURRENT original 36-triangle embedded speaker directly against this 32,386-triangle refined model, rather than the earlier v1-versus-v2 comparison described below. It checks the current base hash and exact face scope, retains the installed station clock and all complete physics, compiles both private models natively, and renders matched front/side views in a disposable editor scene using existing map lighting. The installed taxi post and platform help point remain present. Fresh captures/guards/receipts are under `output/railhead/pa-speaker-v2/current-native`. No public scene/import, original speaker, other placement, audio or lighting changes; current editor scene/play state preserved. This remains a preview awaiting approval. Existing detailed construction is reused rather than duplicated. No LOD or frame-time performance claim.

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

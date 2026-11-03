# Riverside camping lantern preview

The battery lantern beside the dog-run gate at plan `(-50,-205,96)` was a
ten-sided luminous cylinder with flat caps and two straight rods for a handle.
The proposed mesh has a rolled green housing, rubber foot, smooth closed globe,
six protective stays, metal retaining rings, pivot bosses, a continuous rounded
carry handle with a soft grip, and a knurled dimmer with an indicator.

The 15,524-triangle candidate is render-only. It uses three private materials and
the installed `materials/riverside/rs_lantern.vmat` unchanged. No new light is
added, and the original lantern light is not moved or edited. Its height remains
about 14 inches; the control dial projects slightly beyond the original base.

This is an isolated proposal awaiting visual approval. The public pad model,
scene, light definitions, collision and generator are not modified. Do not run a
full Riverside rebuild: the map notes document unrelated changes in the shared
kit that make regeneration unsafe.

`build.py` removes only the old lantern's 92 render triangles from a private copy
of `riverside_pad.obj`, by exact material and saved vertex-position signatures.
Every vertex, normal and UV record and all unrelated faces are retained. The
complete ModelDoc physics section is copied unchanged.

Commands from the canonical checkout:

```powershell
rtk python Sources/Riverside/lantern-v1/build.py
rtk python Sources/Riverside/lantern-v1/setup.py
rtk python Sources/Riverside/lantern-v1/review.py
rtk python Sources/Riverside/lantern-v1/verify.py
```

Native import/compilation is followed by actual offline Riverside play. The
temporary camera copies the player's post effects, uses the same view and
exposure for both variants and allows 180 normal streaming frames per view.
Texture residency is not forced. The editor's prior scene and stopped state are
restored. Interrupted sessions abort instead of capturing stale scene objects.

Outputs and receipts: `output/riverside/lantern-v1/`. The initial source guard is
retained. Another ongoing task changed the green/red lawn-chair colour textures
during this work; verification explicitly records those two external changes
and still requires the public lantern source, glow material, scene, all geometry
and physics files to match the original guard. Native imports are restricted to
this proposal's private directories. No frame-time benchmark is claimed.

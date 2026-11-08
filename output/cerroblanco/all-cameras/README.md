# All Cerro Blanco cameras replaced, 2026-11-06

User explicitly requested all primitive cameras be replaced and the old asset
removed. All six museum camera placements now use the approved Riverdale CCTV
construction/materials. The final batch removes 232 old triangles and adds
11,328 new triangles; the two previously installed replacements remain. Full
face-multiset checks confirm all unrelated geometry is unchanged and no triangle
from any of the six legacy cameras remains in the public render source.

The old primitive camera function/fallback is removed from the active generator.
`cerroblanco_fitout.camera` delegates every placement to `cerroblanco_cctv`.
There was no standalone legacy camera asset to delete: it was embedded geometry
in the shared fitout mesh. The shared mesh, unrelated models and historical
backups are preserved. No obsolete primitive camera is active or regenerated.

Native compile succeeded, public model IsError=false, all six CCTV materials load
without errors. Actual viewport frame bridge_window_172046_135.png was inspected.
No scene, physics, light or navigation changes. All new/approved variants retained.

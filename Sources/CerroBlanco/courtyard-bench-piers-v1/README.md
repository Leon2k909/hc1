# Cerro Blanco courtyard bench — original active; reusable alternative, 2026-11-06

One bench on the central courtyard player route, plan (-250,-800), rebuilt with
two chamfered honed-stone piers, recessed feet, longitudinal steel seat supports,
shaped teak boards, end grain and flush fixings. Reuses the existing pending
`cerroblanco_courtyard_bench` seat and Veridant bench helpers/materials; the older
rejected yellow-stone bench-v2 is not used. The new version changes the bench's
silhouette rather than only adding small surface details.

`build.py` stages a private complete dressing variant. Exactly 70 original bench
triangles are removed; all 25,974 unrelated dressing faces/indices/UVs are kept.
The replacement contains 8,560 triangles, for this single trial bench only.
The inherited screw recess polygon is triangulated about its centre to avoid
folded fan triangles in its concave outline. Geometry checks cover finite data,
nondegenerate triangles, normals/winding and clear space between the stone piers.

Imported and compiled through native editor APIs; the model loads with
IsError=false. Only the live Dressing ModelRenderer was temporarily changed.
Original colliders are retained (including the original solid bench envelope),
and no scene save or gameplay/navigation changes were made. The original dressing
model is restored pending approval. No LOD or frame-time test is claimed.

Before/after are direct native `screenshot_game` editor-window captures, at the
same actual viewport position (-885,340,57), angles (18,-43,0), FOV 80 and original
lighting/display settings. No temporary scene/camera or offscreen render.
Evidence is in `output/cerroblanco/courtyard-bench-piers-v1/`.

User decision: keep the original bench in Cerro Blanco and retain the new design
for another map. No map generator hook or quality-state change is installed.

`standalone.py` exports the reusable asset at
`models/props/shared/stone_pier_teak_bench_v1/bench.vmdl`. It has a ground-centred
origin, the same material/UV appearance, and three collision boxes for the separate
stone supports and timber seat, leaving the centre gap physically open. Native
compilation succeeded. It is not placed in any saved scene. The earlier packed
dressing review variant is also retained. Do not expand this dense mesh to many
benches without a geometry/LOD pass.

# Lounge coffee tables — applied review, 2026-11-06

Replaced the two 14-sided stone drums with eased honed-stone tops, a narrow
steel shadow reveal and recessed stone pedestals. Original 32-inch diameter,
16-inch height, centers, collision and lighting retained. Reuses existing
vr_table_honed and vr_stone_dark/vr_steel materials; no added collision.
Each new model is 2,302 triangles.

Reusable new model: models/props/shared/lounge_coffee_table_v1/coffee_table.vmdl.
Original retained, floor-centered: models/props/shared/lounge_coffee_table_original_v1/coffee_table_original.vmdl.
Generator Tools/veridant_lounge_table.py; lounge() emits its geometry on full
regeneration. Current scene uses two dedicated model objects.

Staging removed exactly 80 original render triangles from Buildings source
imports, retained all unrelated source records and unchanged ModelDoc physics,
and redirected only touched render sources. Original render sources and parent
snapshot retained under output/veridant/lounge-tables-v1/before/. Both models
compiled through the native editor; Buildings and both models load without error.

Matching actual displayed viewport before.png/after.png are under
output/veridant/lounge-tables-v1/. No temporary cameras, offscreen rendering,
or changed lighting/display settings. Import is guarded against parent changes.

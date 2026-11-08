# Veridant reception entrance wall light — applied 2026-11-05

User accepted trying the new fixture on Veridant while retaining the original.
The original is also a separately compiled reusable asset at
`models/props/shared/wall_light_original_v1/wall_light_original.vmdl`, with its
origin at the wall mounting centre and lens facing local -X. Its original emissive
material is retained; add the scene light separately when placing it elsewhere.
`retain_original.py` builds/imports this model without modifying the active upgrade.

Replaces only the four flat fixture triangles above the glazed reception entrance
with a 106-triangle constructed fixture: recessed emissive lens, bevelled metal
frame, side returns, weather lip and four small captive fasteners. The rectangular
design and original light colour, intensity, radius, position and shadow setting
are retained. Original sign and desk remain active; the walnut desk is still
available as its separate shared prop.

The scoped source patch retains every unrelated base OBJ record and index; the
buildings ModelDoc imports that copy plus the small fixture mesh. All other model
imports and the entire physics suffix are unchanged. No scene settings or light
components were edited. The narrow `veridant_parts.wall_washer` hook retains this
one named fixture on regeneration and leaves light registration unchanged.

`build.py` stages; `prepare_import.py` imports through the native editor with source
and parent guards; `verify.py` checks finite/unit data, nondegenerate triangles,
preserved records, exact installed hashes and unchanged physics. Do not rerun old
imports over newer work without deliberately refreshing the baseline.

Matched actual editor viewport frames are `output/veridant/reception-wall-light-v1/before.png`
and `after.png`. Both use the same existing editor camera at player eye height,
with no temporary cameras, isolated scenes or RenderToBitmap. Native
ScreenshotService.RequestCapture captures the displayed scene frame; the visible
SceneRenderingWidget is focused/updated to ensure a real frame is displayed.

# North terrace bar timber frontage — unused alternative, 2026-11-06

User rejected this frontage for Veridant. The dedicated scene object and map
generation hook were removed; the original plain bar is active. New geometry
and compiled model remain available at
models/maps/veridant/terrace-bar-front-v1/front.vmdl for use elsewhere. This model
uses map-space coordinates; it is a fitted frontage rather than a complete bar.

Fitted chamfered timber slats, dark backing and metal plinth to the existing
terrace bar front and exposed west return. Original stone structure, countertop,
LED strip, stools and collision remain. 868 added triangles; existing materials;
no added collision. Source Tools/veridant_terrace_bar_front.py.

Original plain bar retained as a floor-centered reusable model, 200 by 28 by 42
inches: models/props/shared/terrace_bar_original_v1/bar_original.vmdl. Includes
the original geometry and collision, without a scene light component.

Native compilation succeeded. Matching displayed viewport captures are
output/veridant/terrace-bar-front-v1/before.png and after.png. No offscreen render
or lighting/display changes.

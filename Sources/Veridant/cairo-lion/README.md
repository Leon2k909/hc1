# Fountain lion replacement — applied 2026-11-08

Selected the Rigsters/Barye seated lion after comparing the CC0 Cairo reclining
scan and the earlier reconstructed model in the actual editor viewport.
The Barye model has complete facial anatomy and an authored normal map and UV
layout. Its seated posture differs from the original generated reference.

Installed asset `models/props/shared/veridant_fountain_barye_crown/crown.vmdl`.
Generator `Tools/veridant_barye_lion_crown.py`. 123,456 triangles for two lions,
the central curved stone pier, capital and acanthus relief. Keeps the original
sculpture's integral bases and removes redundant added slabs. The shader uses
the source UV colour and normal maps, remaps the colour to muted aged bronze,
and uses roughness 0.72 / metalness 0.38 under normal scene lighting.

Scene component `14cc7dcb-4dde-40c3-bfc0-f11d723ef91d` uses ModelIncludesPier and
SculpturalMouth `29.35,1.7,71.85`. Saved through the native editor. Source model,
textures, normal map and attribution are preserved. CC-BY credit also lives
next to the runtime model as ATTRIBUTION.txt. See BARYE-ATTRIBUTION.md.

Native asset/material compiles passed, model loaded without errors, and the
front and side were checked in the live viewport. Matching comparison captures
are `output/veridant/fountain-flow/barye-before.png` and `barye-after.png`.
Front check is `barye-front.png`. No offscreen render or lighting changes.
Earlier fountain variants and the Cairo candidate remain available for reuse.

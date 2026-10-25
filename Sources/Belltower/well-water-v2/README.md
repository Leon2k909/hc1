# Garden well water

The well uses `Assets/shaders/belltower_well_water_v2.shader`, published from
`well_water.shader` in this directory. Its material is
`Assets/materials/belltower/well-v1/well_water.vmat`; `Tools/belltower_well.py`
reproduces the installed material on map regeneration.

The material reduces the saturated diffuse sheen, tightens the surface reflection,
and combines two slowly moving normal samples at different scales. Opacity 0.78
keeps the shallow backing mesh subdued; grazing views increase surface opacity.
The shader is private to the well.

Native publication and compilation receipts are under
`output/belltower/well-water-v2/trial2/`. The accepted editor captures are
`output/belltower/quality/well-water-v2-trial2/above.png` and `oblique.png`.
Their restoration receipts confirm camera, lighting settings, renderers, scene
objects and editor state were restored after each capture. The material and shader
compiled successfully. These are editor checks, rather than a gameplay test.

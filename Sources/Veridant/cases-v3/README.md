# Veridant transport cases

All 82 black and olive hard cases use rounded, tapered moulded shells, closed
opaque lid gaskets, recessed folding handles, over-centre catches, pin hinges,
stacking ribs/feet and pressure valves. Separate polymer, rubber, gasket, coated
steel and identification-label materials replace the flat original fittings.

`Tools/veridant_parts.hard_case()` delegates to `veridant_transport_case.py`.
`case_stack()` retains its existing offsets, rotations, heights and random-number
consumption. The layout-only replay in `veridant_case_placements.py` captures the
precise 82 poses. `previous-parts.py` preserves the original case construction.

Publication: `output/veridant/cases-v3/stage-v3/manifest.json`. The stage matched
and removed all 20,500 old case triangles from the current buildings and dressing
base imports. Every retained OBJ byte, vertex index and unrelated import remains.
Six dedicated case meshes are appended to the current model documents, retaining
the complete physics suffix byte for byte. The scene and shared canonical map
OBJs retain their hashes. Inspect the current RenderMeshList for future edits.

Each replacement is 3,754 triangles; the six imports contain at most 16 cases
each. Frame-rate impact was not benchmarked. All six materials and both parent
models compiled natively. Matched olive before/after views and the black variant
were inspected with full editor/camera restoration. Evidence:
`output/veridant/cases-v3/validation.json` and
`output/veridant/quality/cases-v3-after/`.

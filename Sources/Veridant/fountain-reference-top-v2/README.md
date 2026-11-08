# Complete reference crown, 2026-11-08

The v2 top reconstructs both lions, the carved architectural pier, capital and
joined plinth as one asset. The previous individually reconstructed lion/pier
assembly remains under `veridant_fountain_reference_top`.

The transparent `crown-source.png` was made with the built-in imagegen tool from
the user's close-up reference. Prompt requested extraction of only the complete
two-lion crown, retaining anatomy, flowing manes, paws, tails, moulded cap and
acanthus pier, with no water, bowl or background, in neutral studio lighting.

`crown.glb` is the local TripoSG reconstruction at 384 SDF grid resolution. No
third-party model was imported. `Tools/veridant_fountain_reference_crown_v2.py`
repairs thin perforations through a sub-unit volumetric closing, reduces to
220,000 triangles and exports the runtime OBJ/ModelDoc. It maps the isolated
source onto the crown and separates limestone and bronze. The custom material
reduces broad studio illumination, keeps fine relief contrast, and uses normal
engine lighting and reflections. There is no emissive image overlay.

Rebuild with Python containing trimesh, scipy, numpy, Pillow, scikit-image and
fast-simplification, passing a reconstruction GLB from outside this source
directory to the build script. The reconstruction wrapper accepts a local
TripoSG environment directory followed by the isolated source image.

Runtime model `models/props/shared/veridant_fountain_reference_top_v2/crown.vmdl`.
The existing ForecourtFountainFlow component uses ModelIncludesPier and mouth
coordinates `26.4,0.5,68.9`. Lower bowl and waterfall implementation retained.

Validation uses the actual displayed editor viewport, unchanged lighting and
display settings. Matching previous/replacement captures are under
`output/veridant/fountain-flow/crown-v2-before.png` and `crown-v2-after.png`.
Model and both materials compiled successfully. Scene saved through native tools.

Limitations remain: single-image reconstruction approximates occluded surfaces,
facial anatomy and fine relief. Source projection is less exact around side and
top returns. This is an improved in-engine approximation, not an exact replica
of the reference image or a claim of production sculpt quality.

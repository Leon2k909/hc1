"""Export the preserved full Rotunde as a standalone model, centred at its base.

    python Tools/railhead_rotunda_export.py
Then run Blender with --python Tools/railhead_rotunda_bake.py to refresh the distant bake.
The full model is intentionally not instantiated in Railhead.
"""
import numpy as np
import railhead_backdrop as B
import railhead_map as R
from map_kit import Model

model = Model()
B.rotunda_geometry(model)
offset = np.array((B.ROTUNDA[0], B.ROTUNDA[1], B.ROTUNDA_BASE))
for paint, faces in model.polygons.items():
    model.polygons[paint] = [([p - offset for p in points], normal) for points, normal in faces]
B.configure(model)
R.K.write_model(R.OUT_DIR, R.RESOURCE_DIR, "railhead_rotunda_full", model)
print(f"Preserved standalone Rotunde: {model.triangle_count()} triangles")

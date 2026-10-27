"""Rebuild only the centre mesh while iterating on the fountain."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/"Tools"))
import belltower_map as B
import numpy as np

model=B.build_centre([])
B.Detail.configure(model)
for paint,polygons in model.polygons.items():
    for pts,normal in polygons:
        assert np.isfinite(pts).all() and np.isfinite(normal).all(),paint
for normals in model.polygon_normals.values():
    assert np.isfinite(normals).all()
print("Materials:",sorted(model.polygons))
print("Triangles:",B.K.write_model(B.OUT_DIR,B.RESOURCE_DIR,"belltower_centre",model))

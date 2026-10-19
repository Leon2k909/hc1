"""Build the beech placements, checking original garden geometry and collision."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[3]
out = Path(__file__).resolve().parent
sys.path.insert(0, str(root / "Tools"))
import map_kit as K
import veridant_map as current

spec = importlib.util.spec_from_file_location("veridant_before_hedges", out / "before/Tools/veridant_map.py")
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)

def normal(value):
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, dict):
        return {key: normal(v) for key, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [normal(v) for v in value]
    return value

def digest(value):
    return hashlib.sha256(json.dumps(normal(value), sort_keys=True).encode()).hexdigest()

before, after = K.Model(), K.Model()
old.P.reset()
old.gardens(before, K.Model())
current.P.reset()
current.gardens(after, K.Model())
assert digest(before.boxes) == digest(after.boxes), "Garden collision changed"
assert digest(before.hulls) == digest(after.hulls), "Garden hull collision changed"
assert "vr_hedge" not in after.polygons
assert digest({k: v for k, v in before.polygons.items() if k != "vr_hedge"}) == digest(after.polygons)
assert all(p["path"] == current.HEDGE_MODEL for p in after.props)
assert len(after.props) == 88, len(after.props)
manifest = {"model": current.HEDGE_MODEL, "package": current.HEDGE_PACKAGE,
            "props": normal(after.props), "scene_objects": current.hedge_objects(after.props),
            "verification": {"hedge_runs": 13, "leaf_instances": len(after.props),
                             "garden_collision_unchanged": True, "other_garden_surfaces_unchanged": True,
                             "garden_collision_sha256": digest(before.boxes)}}
(out / "manifest.json").write_text(json.dumps(manifest, indent=2))
print(json.dumps(manifest["verification"], indent=2))

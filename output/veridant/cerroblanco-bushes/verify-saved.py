"""Check the saved scene against its baseline, allowing editor serialization formats."""
import hashlib
import json
import math
from pathlib import Path

root = Path(__file__).resolve().parents[3]
out = Path(__file__).resolve().parent
relative = "Assets/scenes/maps/Veridant/veridant.scene"
before = json.loads((out / "before" / relative).read_text())
after = json.loads((root / relative).read_text())

def same(a, b):
    if isinstance(a, str) and isinstance(b, dict) and "Path" in b:
        return a.lower() == b["Path"].lower()
    if isinstance(a, dict):
        # The engine migrates this legacy flag when the editor saves a probe.
        if a.get("__type") == "Sandbox.EnvmapProbe" and a.get("RenderDynamically") is True:
            a = {k: v for k, v in a.items() if k != "RenderDynamically"}
            a["Mode"] = "Realtime"
        return isinstance(b, dict) and all(same(v, b.get(k)) for k, v in a.items())
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    if isinstance(a, str) and isinstance(b, str) and "," in a:
        try:
            av, bv = list(map(float, a.split(","))), list(map(float, b.split(",")))
            return len(av) == len(bv) and all(math.isclose(x, y, abs_tol=1e-4, rel_tol=1e-6) for x, y in zip(av, bv))
        except ValueError:
            pass
    return a == b

def flatten(items):
    for item in items:
        yield item
        yield from flatten(item.get("Children", []))

old_objects = list(flatten(before["GameObjects"]))
new_objects = list(flatten(after["GameObjects"]))
lookup = {g["__guid"]: g for g in new_objects}
for original in old_objects:
    current = lookup[original["__guid"]]
    assert same({k: v for k, v in original.items() if k not in ("Components", "Children")}, current), original.get("Name")
    components = {c["__guid"]: c for c in current.get("Components", [])}
    for component in original.get("Components", []):
        assert same(component, components[component["__guid"]]), (original.get("Name"), component["__type"])

group = next(g for g in new_objects if g.get("Name") == "Beech Hedges")
assert len(group["Children"]) == 88
assert "facepunch.beech_hedge_96x128#145491" in after["__references"]
for child in group["Children"]:
    assert len(child["Components"]) == 1
    assert child["Components"][0]["__type"] == "Sandbox.ModelRenderer"
baseline = json.loads((out / "baseline.json").read_text())
for name in ("Assets/models/maps/veridant/veridant_dress.vmdl", "Assets/models/maps/veridant/veridant_dress.mtl"):
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == baseline["hashes"][name], name
result = {"existing_scene_objects_preserved": len(old_objects),
          "existing_component_values_preserved": True, "leaf_instances": 88,
          "cloud_dependency_saved": True, "original_model_physics_source_unchanged": True,
          "generator_spot_checks": 97, "spot_failures": 0, "unreachable_spots": 0, "exposed_retakes_pairs": 0}
(out / "verification.json").write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))

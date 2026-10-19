"""Verify the saved native edit against the exact pre-edit C: scene documents."""
import ast
import copy
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "Tools"))
from map_daylight import apply_profile, same_value

def differences(a, b, path=""):
    if isinstance(a, dict) and "Path" in a and set(a) <= {"Id", "Path"}:
        a = a["Path"]
    if isinstance(b, dict) and "Path" in b and set(b) <= {"Id", "Path"}:
        b = b["Path"]
    if same_value(a, b):
        return []
    if isinstance(a, (int, float)) and not isinstance(a, bool) and isinstance(b, (int, float)) and not isinstance(b, bool):
        if math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-7):
            return []
    if isinstance(a, dict) and isinstance(b, dict):
        result = []
        for key in sorted(set(a) | set(b)):
            if key not in a or key not in b:
                result.append({"path":path + "/" + key, "before":a.get(key), "after":b.get(key), "key_changed":True})
            else:
                result.extend(differences(a[key], b[key], path + "/" + key))
        return result
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return [entry for i, (x, y) in enumerate(zip(a, b)) for entry in differences(x, y, path + "/" + str(i))]
    return [{"path":path, "before":a, "after":b}]

def ids(value):
    result = set()
    if isinstance(value, dict):
        if "__guid" in value:
            result.add(value["__guid"])
        for child in value.values():
            result.update(ids(child))
    elif isinstance(value, list):
        for child in value:
            result.update(ids(child))
    return result

def concurrent_lowtide_addition(scene, before):
    # Independently added after the lighting save: preserve these 56 pipe colliders.
    # Compare all other content to the original lighting candidate, and report the
    # exact addition instead of silently accepting arbitrary scene differences.
    guid = "d5525647-0722-58dc-9d03-c947eb7f5ba5"
    if guid in ids(before):
        return []
    def visit(objects):
        for index, obj in enumerate(objects):
            if obj.get("__guid") == guid:
                children = obj.get("Children", [])
                assert obj.get("Name") == "Downpipe Collisions" and len(children) == 56
                assert all(len(x.get("Components", [])) == 1 and
                           x["Components"][0].get("__type") == "Sandbox.CapsuleCollider" for x in children)
                assert not (ids(obj) & ids(before)), "Concurrent addition reused an existing identity"
                record = {"name":obj["Name"], "id":guid, "colliders":len(children),
                          "sha256":hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()}
                objects.pop(index)
                return [record]
            found = visit(obj.get("Children", []))
            if found:
                return found
        return []
    return visit(scene["GameObjects"])

plan = json.loads((OUT / "native-plan.json").read_text())
results = []
for entry in plan:
    expected = json.loads((OUT / "candidates" / (entry["slug"] + ".json")).read_text())
    before = json.loads((OUT / "candidates" / (entry["slug"] + ".before.json")).read_text())
    current = json.loads((ROOT / "Assets" / entry["path"]).read_text(encoding="utf-8-sig"))
    compared = copy.deepcopy(current)
    concurrent = concurrent_lowtide_addition(compared, before) if entry["slug"] == "lowtide" else []
    unexpected = differences(expected, compared)
    result = {"map":entry["map"], "mood":entry["mood"], "authored_changes":len(entry["changes"]),
              "profile_persisted":not apply_profile(copy.deepcopy(current)),
              "identities_preserved":ids(before) <= ids(current), "concurrent_changes_preserved":concurrent,
              "unexpected_differences":unexpected}
    results.append(result)
    print(json.dumps({**result, "unexpected_differences":len(unexpected)}))

sources = ("belltower_map.py", "boxyard_map.py", "cerroblanco_map.py", "lowtide_finish.py", "railhead_map.py",
           "riverdale_map.py", "orion_map.py", "veridant_map.py", "ares_map.py")
hooks = {}
for name in sources:
    tree = ast.parse((ROOT / "Tools" / name).read_text(encoding="utf-8-sig"))
    hooks[name] = sum(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "apply_profile"
                      for n in ast.walk(tree))
report = {"maps":results, "generator_hooks":hooks,
          "passed":all(r["profile_persisted"] and r["identities_preserved"] and not r["unexpected_differences"] for r in results)
                   and all(count == 1 for count in hooks.values())}
(OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"passed":report["passed"], "generator_hooks":hooks}))
sys.exit(0 if report["passed"] else 1)


"""Boxyard perimeter wall v1: adds / removes the "Perimeter Wall" object in boxyard.scene (boxyard-model session, 2026-11-06).

The scene file is the generator's own format (json.dumps( indent=2 ) with CRLF line ends and no final newline, which a
round trip reproduces byte for byte), so adding the group and taking it out again leaves every other byte alone. The group
(a parent with 56 draw-only ModelRenderer children) is what Tools/boxyard_map.py wall_objects() writes, and it goes at the end
of the "Boxyard" root object's children.
"""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCENE = "Assets/scenes/maps/Boxyard/boxyard.scene"
GROUP = "Perimeter Wall"
ROOT_OBJECT = "Boxyard"


def _load(path):
    raw = Path(path).read_bytes().decode("utf-8")
    scene = json.loads(raw)
    assert json.dumps(scene, indent=2).replace("\n", "\r\n") == raw or json.dumps(scene, indent=2) == raw, \
        "the scene file does not round-trip through json.dumps( indent=2 ): refusing to rewrite it"
    return scene, ("\r\n" in raw)


def _dump(scene, crlf):
    text = json.dumps(scene, indent=2)
    return text.replace("\n", "\r\n") if crlf else text


def _write(path, text):
    path = Path(path)
    data = text.encode("utf-8")
    if path.read_bytes() == data:
        return False
    temp = path.with_name(path.name + ".writing")
    temp.write_bytes(data)
    import time
    for attempt in range(20):
        try:
            temp.replace(path)
            return True
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(0.5)


def _root_object(scene):
    found = [o for o in scene["GameObjects"] if o.get("Name") == ROOT_OBJECT]
    assert len(found) == 1, f"expected one top-level object named {ROOT_OBJECT}, found {len(found)}"
    return found[0]


def group_from_generator():
    sys.path.insert(0, str(ROOT / "Tools"))
    sys.dont_write_bytecode = True
    import boxyard_map as B
    assert B.OLD_WALL_IN_YARD is False
    made = B.wall_objects()
    assert len(made) == 1 and made[0]["Name"] == GROUP and len(made[0]["Children"]) == 56
    return made[0]


def has_group(scene_file):
    scene, _ = _load(scene_file)
    return [c for c in _root_object(scene)["Children"] if c.get("Name") == GROUP]


def add_group(scene_file):
    scene, crlf = _load(scene_file)
    root = _root_object(scene)
    root["Children"] = [c for c in root["Children"] if c.get("Name") != GROUP]
    root["Children"].append(group_from_generator())
    return _write(scene_file, _dump(scene, crlf))


def remove_group(scene_file):
    scene, crlf = _load(scene_file)
    root = _root_object(scene)
    before = len(root["Children"])
    root["Children"] = [c for c in root["Children"] if c.get("Name") != GROUP]
    return before - len(root["Children"]), _write(scene_file, _dump(scene, crlf))


if __name__ == "__main__":
    f = ROOT / SCENE
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "add":
        print(json.dumps({"changed": add_group(f)}))
    elif cmd == "remove":
        print(json.dumps({"removed": remove_group(f)}))
    else:
        print(json.dumps({"groups": len(has_group(f))}))

"""Audit the generated Railhead scene and collision sources after railhead_map.py."""
import json
import math
import re
from pathlib import Path

import railhead_map as R
from map_kit import Model


def main():
    assets = R.K.ASSETS
    scene = json.loads(R.SCENE_FILE.read_text())
    objects = []

    def walk(value):
        if isinstance(value, dict):
            if "Components" in value:
                objects.append(value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(scene)
    checked = set()
    boxes = 0
    for obj in objects:
        for component in obj.get("Components", []):
            if component.get("__type") != "Sandbox.ModelCollider":
                continue
            assert not component.get("IsTrigger", False), obj.get("Name")
            path = component["Model"]
            if path in checked:
                continue
            checked.add(path)
            text = (assets / path).read_text()
            assert "PhysicsShapeList" in text, f"Empty collider: {path}"
            for dimensions in re.findall(r"dimensions\s*=\s*\[([^]]+)\]", text):
                size = [float(v.strip()) for v in dimensions.split(",")]
                assert len(size) == 3 and all(math.isfinite(v) and v > 0 for v in size), (path, size)
                boxes += 1
            for hull in re.findall(r'filename\s*=\s*"([^"]+_hulls_[^"]+\.obj)"', text):
                assert (assets / hull).is_file(), f"Missing hull: {hull}"

    expected = {f"models/maps/railhead/{name}.vmdl" for name, _, collide, _ in R.SCENE_MODELS if collide}
    assert expected <= checked, f"Missing scene colliders: {expected - checked}"
    clips = [obj for obj in objects if obj.get("Name", "").startswith("Player Clip ")]
    assert len(clips) == 3, "Missing map boundary clips"
    for obj in clips:
        assert any(c.get("__type") == "Sandbox.BoxCollider" and not c.get("IsTrigger", False)
                   for c in obj["Components"]), obj["Name"]

    sign = Model()
    R.warn_plate(sign, 0, 0)
    assert len(sign.boxes) == 2, "Warning sign needs separate post and plate collision"
    print(f"PASS: {len(checked)} solid models, {boxes} valid collision boxes, hull sources and 3 boundary clips")
    print("PASS: warning sign post and plate both solid")


if __name__ == "__main__":
    main()

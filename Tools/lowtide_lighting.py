"""Preserve the native warehouse lighting bake when rebuilding Lowtide.

The engine exports the spotlight and volume schemas in warehouse-lighting.json.
Re-bake after static geometry, fixtures or daylight change; do not run a full map
rebuild merely to apply lighting. This function only updates the Lights root.
"""
import copy
import json

import map_kit as K

SOURCE = K.ROOT / "Sources/Lowtide/lighting/warehouse-lighting.json"


def apply_scene(scene):
    data = json.loads(SOURCE.read_text())
    lights = next(o for o in scene["GameObjects"] if o.get("Name") == "Lights")
    by_name = {o.get("Name"): o for o in lights["Children"]}
    for saved in data["lights"]:
        obj = by_name[saved["name"]]
        points = [c for c in obj["Components"] if c["__type"] == "Sandbox.PointLight"]
        if len(points) != 1:
            raise ValueError(f"Expected the original point light for {saved['name']}")
        # Retain the original light and its GUID for references and reversibility.
        points[0]["__enabled"] = False
        obj["Rotation"] = saved["rotation"]
        spots = [c for c in obj["Components"] if c["__type"] == "Sandbox.SpotLight"]
        if spots and any(c["__guid"] != saved["spot"]["__guid"] for c in spots):
            raise ValueError(f"Unrecognised spotlight on {saved['name']}; inspect before replacing")
        obj["Components"] = [c for c in obj["Components"] if c["__type"] != "Sandbox.SpotLight"]
        obj["Components"].append(copy.deepcopy(saved["spot"]))
    for saved in data["volumes"]:
        existing = by_name.get(saved["Name"])
        if existing is None:
            lights["Children"].append(copy.deepcopy(saved))
        elif existing != saved:
            raise ValueError(f"Modified {saved['Name']}; inspect or re-bake before rebuilding")

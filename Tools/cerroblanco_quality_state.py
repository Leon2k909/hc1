"""Retain editor-verified visual state when regenerating the base museum.

Export reads the saved scene and writes Sources only. Scene publication while
the editor is open remains an editor operation, as with the other map sources.
"""
from pathlib import Path
import copy
import json

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "Sources/CerroBlanco/quality-state.json"


def objects(scene):
    pending = list(scene["GameObjects"])
    while pending:
        obj = pending.pop()
        yield obj
        pending.extend(obj.get("Children", []))


def apply_saved_quality(scene):
    if not STATE.exists():
        return
    state = json.loads(STATE.read_text())
    remaining = set(state["component_patches"])
    for obj in objects(scene):
        for component in obj.get("Components", []):
            guid = component.get("__guid")
            if guid in remaining:
                component.update(copy.deepcopy(state["component_patches"][guid]))
                remaining.remove(guid)
    if remaining:
        raise ValueError(f"Quality state no longer matches {len(remaining)} base components; refresh it in the editor")
    for name, replacement in state["objects"].items():
        index = next((i for i, obj in enumerate(scene["GameObjects"]) if obj.get("Name") == name), None)
        if index is None:
            scene["GameObjects"].append(copy.deepcopy(replacement))
        else:
            scene["GameObjects"][index] = copy.deepcopy(replacement)


def export():
    scene = json.loads((ROOT / "Assets/scenes/maps/CerroBlanco/cerroblanco.scene").read_text())
    patches = {}
    for obj in objects(scene):
        for component in obj.get("Components", []):
            kind = component.get("__type")
            patch = {}
            if kind == "Sandbox.ModelRenderer":
                model = component.get("Model")
                path = model.get("Path", "") if isinstance(model, dict) else model or ""
                if not path.startswith("models/maps/cerroblanco/"):
                    continue
                if (component.get("Materials") or {}).get("indexed"):
                    patch["Materials"] = component["Materials"]
                if path.endswith("quality-v1/cerroblanco_dressing_v2.vmdl"):
                    patch["Model"] = model
            elif kind == "Sandbox.DirectionalLight":
                patch = {key: component[key] for key in ("LightColor", "SkyColor")}
            elif kind == "Sandbox.PointLight":
                patch = {"LightColor": component["LightColor"]}
            if patch:
                patches[component["__guid"]] = patch
    retained = {obj["Name"]: obj for obj in scene["GameObjects"]
                if obj.get("Name") in {"Reflection Probes", "Museum indirect light", "Cerro Blanco construction details"}}
    assert len(retained) == 3
    assert all(obj.get("NetworkMode") == 2 for obj in objects({"GameObjects": list(retained.values())})), \
        "Static visual objects must be included in the network snapshot"
    assert all(c["Mode"] == "CustomTexture"
               for obj in objects({"GameObjects": list(retained.values())})
               for c in obj.get("Components", []) if c.get("__type") == "Sandbox.EnvmapProbe")
    state = {"component_patches": patches, "objects": retained}
    STATE.write_text(json.dumps(state, indent=2) + "\n")
    print(json.dumps({"component_patches": len(patches), "retained_objects": list(retained)}))


if __name__ == "__main__":
    export()

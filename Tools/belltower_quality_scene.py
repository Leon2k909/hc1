"""Stage reviewed Belltower lighting; the editor validates and saves the resource."""
import hashlib
import json
from pathlib import Path
import belltower_map as B

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "output/belltower/quality"


def reflections_object():
    return B.reflections_object()


def main():
    source = ROOT/"Assets/scenes/maps/Belltower/belltower.scene"
    original = source.read_bytes()
    scene = json.loads(original)
    settings = json.loads((DIRECTORY/"capture-config.json").read_text())
    changes = settings["overrides"]
    # Regeneration and native staging share one source for the reviewed look.
    # Explicit capture overrides take precedence for the version being reviewed.
    look = changes.setdefault("Look", {})
    for component in B.look_object()["Components"]:
        defaults = {k:v for k,v in component.items() if not k.startswith("__") and k != "Flags"}
        defaults.update(look.get(component["__type"], {}))
        look[component["__type"]] = defaults
    for obj in scene["GameObjects"]:
        for component in obj.get("Components",[]):
            component.update(changes.get(obj.get("Name"),{}).get(component["__type"],{}))
        if obj.get("Name") == "Sky":
            obj["Rotation"] = B.K.angles_rotation(0,90)
    scene["GameObjects"] = [x for x in scene["GameObjects"] if x.get("Name") != "Reflections"]
    scene["GameObjects"].append(reflections_object())
    indirect = B.indirect_light_object()
    if indirect:
        scene["GameObjects"] = [x for x in scene["GameObjects"] if x.get("Name") != "Indirect Light"]
        scene["GameObjects"].append(indirect)
    landscape = B.landscape_tree_object()
    if landscape:
        scene["GameObjects"] = [x for x in scene["GameObjects"] if x.get("Name") != "Landscape trees"]
        scene["GameObjects"].append(landscape)
        dry_oak = "facepunch.treeoakdrymediuma#289352"
        if dry_oak not in scene["__references"]:
            scene["__references"].append(dry_oak)
    (DIRECTORY/"scene-import.json").write_text(json.dumps(scene,indent=2)+"\n",encoding="utf-8")
    (DIRECTORY/"scene-import-source.sha256").write_text(hashlib.sha256(original).hexdigest())
    print("Staged Belltower lighting, reflection probes and landscape; scene import remains native.")


if __name__ == "__main__":
    main()

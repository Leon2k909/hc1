"""Build AUG stock/barrel/magazine choices without overwriting tuned weapon settings.

Uses the same source assets and port as the existing AUG. Only new attachment
materials/foley, meshes, drum reloads, model definitions and Gunsmith slots change.
Run: python Tools/aug_gunsmith.py
Then compile the AUG assets in s&box and refresh the Gunsmith preview.
"""
import json
import re
import sys
from pathlib import Path

import aug_assets as A
import kastov_dmx as D
import kastov_prefabs as P
import kastov_weapons as W
from port_kastov import Kastov


def attachment_assets():
    path = A.DEST / "aug_assets.json"
    manifest = json.loads(path.read_text())
    for source in ("weapon_vm_sm_augolf_stocklight", "weapon_vm_sm_augolf_stocktactical", "weapon_vm_sm_augolf_lmg_mag"):
        name, base, pack = A.MATERIALS[source]
        material = A.build_material(name, base, A.DEST / "materials", pack)
        manifest["materials"][source] = A.asset_path(material)
    events, aliases = A.clip_events(), A.alias_files()
    def event_for(alias):
        [file] = aliases[alias]
        name = re.sub(r"^wfoly_sm_augolf_", "", Path(file).stem)
        event = A.DEST / "sounds" / f"aug_{name}.sound"
        wav = event.with_suffix(".wav")
        A.ffmpeg(["-i", str(A.EXTRACTED / "sound" / file), "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", str(wav)])
        A.sound_event(event, [wav], pitch="1", decibels=70, distance=1000, falloff=[{"y": 1}, {"x": 1}])
        manifest["sounds"][name] = A.asset_path(event)
        return A.asset_path(event)
    for clip in ("reload_drummag", "reload_empty_drummag"):
        manifest["reloads"][clip] = A.timed(events[clip], event_for)
    path.write_text(json.dumps(manifest, indent=2) + "\n")


def meshes():
    weapon = W.AUG
    port = Kastov(weapon)
    pose = port.presentation()
    mesh_dir = weapon.folder / "models"
    pieces = {"": port.triangles(), **port.optional_triangles(), **port.choice_triangles()}
    for name, triangles in pieces.items():
        suffix = f"_{name}" if name else ""
        vname, wname = f"v_aug{suffix}", f"w_aug{suffix}"
        D.write_model(mesh_dir / f"{vname}.dmx", vname, port.nodes, port.locals_(pose), port.rebind(triangles, pose))
        nodes, bind, world = port.world_triangles(triangles)
        D.write_model(mesh_dir / f"{wname}.dmx", wname, nodes, bind, world)
        print(f"{name or 'receiver'}: {len(triangles)} triangles", flush=True)
    # Existing idle, fire, ADS and normal reload files stay as tuned.
    for name, frames, fps in port.clips():
        if name.endswith("_drummag"):
            D.write_animation(mesh_dir / "anims" / f"{name}.dmx", name, port.nodes,
                              [port.locals_(frame) for frame in frames], fps)
            print(f"{name}: {len(frames)} frames", flush=True)


def slots():
    weapon, config = W.AUG, P.PREFABS["aug"]
    P.own_parts(weapon, config)
    for prefix in ("vm", "wm"):
        path = weapon.folder / f"{prefix}_aug.prefab"
        document = json.loads(path.read_text())
        root = document["RootObject"]
        for component in root.get("Components", []):
            if component.get("__type") == "Sandbox.SkinnedModelRenderer":
                component["BodyGroups"] = config.default_mesh_groups
        updates = P.attachment_points(weapon, config, prefix)
        children = root.setdefault("Children", [])
        for point in updates:
            category = point["Components"][0]["Category"]
            old = next((obj for obj in children if any(c.get("Category") == category and
                       c.get("__type", "").endswith("GunsmithAttachmentPoint") for c in obj.get("Components", []))), None)
            if old is None:
                children.append(point)
            elif category == "Muzzle":
                next(c for c in old["Components"] if c.get("Category") == category)["FittedBodygroups"] = {"muzzle_tip": 2}
        path.write_text(json.dumps(document, indent=2) + "\n")


def main():
    attachment_assets()
    meshes()
    # These generators write only AUG's model definitions and animation graph.
    import kastov_vmdl
    import kastov_animgraph
    sys.argv = [sys.argv[0], "--weapon", "aug"]
    kastov_vmdl.main()
    kastov_animgraph.main()
    slots()
    print("Built two stocks, a heavy long barrel and a 60-round drum for AUG.")


if __name__ == "__main__":
    main()

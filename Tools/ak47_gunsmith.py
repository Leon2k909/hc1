"""Import AK-47 parts from Workshop 3803722029, preserving existing weapon tuning.

Run: python Tools/ak47_gunsmith.py
Only new materials/foley and reload clips are converted. Factory animations stay intact.
"""
import json
import re
import sys

import kastov_dmx as D
import kastov_materials as M
import kastov_prefabs as P
import kastov_sounds as S
import kastov_weapons as W
import ported_foley
from port_kastov import Kastov

WEAPON = W.KASTOV_762
SOURCE = M.ADDON.parent
CLIPS = ("reload_xmag", "reload_empty_xmag", "reload_dmag", "reload_empty_dmag")


def attachment_assets():
    for name, source in M.ATTACHMENT_MATERIALS.items():
        if not (M.OUT / f"{name}.vmat").exists():
            M.convert(name, source)
    lua = (SOURCE / "lua/weapons/mg_base/modules/sounds/mw4_ak47_sound.lua").read_text(encoding="utf-8")
    aliases = {}
    for block in re.findall(r"sound\.Add\(\s*\{(.*?)\}\s*\)", lua, re.S):
        name = re.search(r'name\s*=\s*"([^"]+)"', block)
        if name:
            aliases[name[1]] = re.findall(r'"([^"\n]+\.ogg)"', block)
    # The pack references a missing normal-speed drum grab; its fast reload
    # supplies the same hand/charging-handle contact sound.
    aliases["wfoly_rex_plr_ar_akilo_drum_reload_empty_06"] = ["ak47/rex_vm_ar_akilo_drum_reload_fast_empty_grab.ogg"]
    qc = (WEAPON.decompiled / "v_akm/v_akm.qc").read_text()
    sequences = {m[1]: m[2] for m in re.finditer(r'\$sequence "([^"]+)"(.*?)(?=\$sequence |\Z)', qc, re.S)}
    reloads = {}
    for clip in CLIPS:
        events = {}
        for frame, alias in re.findall(r'event 5004 (\d+) "([^"]+)"', sequences[clip]):
            files = aliases[alias]
            assert files, alias
            name = "kastov_" + alias.removeprefix(S.FOLEY)
            clips = []
            for index, file in enumerate(files):
                wave = f"{name}_{index}"
                if not (S.OUT / f"{wave}.wav").exists():
                    S.convert(SOURCE / "sound" / file, S.OUT / f"{wave}.wav")
                clips.append(wave)
            S.sound_event(S.OUT / f"{name}.sound", clips, gunshot=False)
            events[f"{int(frame) / 30:.6f}"] = f"{S.OUT_ASSET}/{name}.sound"
        assert events, clip
        reloads[clip] = events
    (WEAPON.folder / "kastov_attachment_assets.json").write_text(json.dumps({"reloads": reloads}, indent=2) + "\n")
    # The foley, with kastov_sounds.py's, voiced away from CoD's sound design (ported_foley.py).
    ported_foley.voice("kastov762")


def meshes():
    port = Kastov(WEAPON)
    pose = port.presentation()
    mesh_dir = WEAPON.folder / "models"
    for name, triangles in {"": port.triangles(), **port.optional_triangles(), **port.choice_triangles()}.items():
        suffix = f"_{name}" if name else ""
        vn, wn = f"v_kastov{suffix}", f"w_kastov{suffix}"
        D.write_model(mesh_dir / f"{vn}.dmx", vn, port.nodes, port.locals_(pose), port.rebind(triangles, pose))
        nodes, bind, world = port.world_triangles(triangles)
        D.write_model(mesh_dir / f"{wn}.dmx", wn, nodes, bind, world)
        print(f"{name or 'receiver'}: {len(triangles)} triangles", flush=True)
    for name, frames, fps in port.clips():
        if name in CLIPS:
            D.write_animation(mesh_dir / "anims" / f"{name}.dmx", name, port.nodes,
                              [port.locals_(frame) for frame in frames], fps)
            print(f"{name}: {len(frames)} frames", flush=True)


def slots():
    config = P.PREFABS[WEAPON.name]
    P.own_parts(WEAPON, config)
    for prefix in ("vm", "wm", "mount"):
        path = WEAPON.folder / f"{prefix}_kastov762.prefab"
        document = json.loads(path.read_text())
        root = document["RootObject"]
        def update_renderer(obj):
            for component in obj.get("Components", []):
                if component.get("Model") in ("weapons/kastov/v_kastov.vmdl", "weapons/kastov/w_kastov.vmdl"):
                    component["BodyGroups"] = config.default_mesh_groups
            for child in obj.get("Children", []):
                update_renderer(child)
        update_renderer(root)
        if prefix != "mount":
            children = root.setdefault("Children", [])
            for point in P.attachment_points(WEAPON, config, prefix):
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
    import kastov_vmdl
    import kastov_animgraph
    sys.argv = [sys.argv[0], "--weapon", "kastov762"]
    kastov_vmdl.main()
    kastov_animgraph.main()
    slots()
    print("Built six stocks, three rear grips, three magazines and one short barrel for AK-47.")


if __name__ == "__main__":
    main()

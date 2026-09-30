"""Build the physical parts listed by the source M16's customization menu.

Reuses shared attachment models through M16-only resources; never rewrites another
weapon's resources. Run before regenerating the M16 with the Kastov pipeline.
Run: python Tools/m16_gunsmith.py [--skip-meshes]
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

import kastov_dmx as D
import kastov_prefabs as P
import kastov_vmdl as V
import kastov_weapons as W
import m16_assets as A
import part_masses
from kastov_smd import Smd, matrix, euler_to_mat, write_smd
from port_kastov import Kastov

ROOT = W.PROJECT
ASSETS = W.ASSETS
DEST = ASSETS / "gunsmith/m16"
SHARED = ASSETS / "gunsmith/m4a1/mw2022"
REPORT = ROOT / "output/m16-gunsmith"
RESOURCE = "weapons/m16/m16.equip"
BARRELS = ["att_vm_p01_ar_mike4_" + name for name in
           ("barhvy_v0", "barhvyshort_v0", "barmidhvy_v0", "barrel_base")]
STOCKS = ["att_vm_p01_" + name for name in
          ("ar_mike4_stockl_v0", "ar_mike4_stockno_v0", "ar_mike4_stocktac_v0", "dm_msecho_stock_v0",
           "dm_stango25_stock_v0", "sm_alpha57_stock_v0", "sm_alpha57_stockwire_v0", "ar_mike4_stock_base")]
GRIPS = ["att_vm_p01_ar_mike4_" + name + "_v0" for name in ("grpass", "grpskel", "grpsn", "grpstdy", "grptac")]
MAGAZINES = {"standard": ("att_vm_p01_ar_mike4_mag_v0", 30), "smag": ("att_vm_p01_ar_mike16_smag_v0", 15),
             "xmag": ("att_vm_p01_ar_mike4_xmag_v0", 45), "xmaglrg": ("att_vm_p01_ar_mike4_xmaglrg_v0", 60)}


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    if not path.exists() or path.read_text(encoding="utf-8") != text:
        path.write_text(text, encoding="utf-8", newline="\n")


def protect_other_weapons():
    paths = [p for p in (ASSETS / "gunsmith").rglob("*") if p.suffix in (".gnsmth", ".prefab") and DEST not in p.parents]
    return {str(p.relative_to(ASSETS)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def prepare_magazines():
    """Combine shell and rounds, retaining both reload magazines and omitting the loose chamber round."""
    for choice, (key, _) in MAGAZINES.items():
        folder = W.M16.decompiled / key
        if not (folder / f"{key}.qc").exists():
            source = next((A.EXTRACTED / "models").rglob(f"{key}.mdl"))
            folder.mkdir(parents=True, exist_ok=True)
            result = subprocess.run([str(A.TOOLS / "CrowbarCommandLineDecomp.exe"), "-p", str(source), "-o", str(folder)],
                                    capture_output=True, text=True, timeout=120)
            if result.returncode or not (folder / f"{key}.qc").exists():
                raise RuntimeError(f"Cannot decompile {key}: {result.stdout[-1000:]}")
        shell = Smd(folder / f"{key}_LOD0.smd")
        nodes = list(shell.nodes)
        frame = shell.dense_frames()[0]
        locals_ = [matrix(frame[i][0], euler_to_mat(*frame[i][1])) for i in range(len(nodes))]
        world = shell.world(frame)
        triangles = list(shell.triangles)
        rounds = Smd(folder / "ammo_unspent_556n_LOD0.smd")
        source_world = rounds.world(rounds.dense_frames()[0])
        mapping = {}
        for i, (name, parent) in enumerate(rounds.nodes):
            found = next((j for j, (n, _) in enumerate(nodes) if n == name), None)
            if found is None:
                found = len(nodes)
                target_parent = mapping[parent] if parent >= 0 else -1
                nodes.append((name, target_parent))
                local = np.linalg.inv(source_world[parent]) @ source_world[i] if parent >= 0 else source_world[i]
                locals_.append(local)
                world.append(world[target_parent] @ local if target_parent >= 0 else local)
            mapping[i] = found
        for material, vertices in rounds.triangles:
            if any(rounds.name(b) == "j_ammo_31" and weight > .5 for *_, links in vertices for b, weight in links):
                continue
            moved = []
            for pos, normal, uv, links in vertices:
                transform = sum(weight * (world[mapping[b]] @ np.linalg.inv(source_world[b])) for b, weight in links)
                moved.append((transform[:3, :3] @ pos + transform[:3, 3], transform[:3, :3] @ normal, uv,
                              [(mapping[b], weight) for b, weight in links]))
            triangles.append((material, moved))
        write_smd(W.M16.decompiled / f"derived/mag_{choice}.smd", nodes, [locals_], triangles)
        print(f"{choice}: {len(triangles)} magazine triangles", flush=True)


def magazine_materials_and_sounds():
    path = A.DEST / "m16_assets.json"
    manifest = json.loads(path.read_text())
    shared_materials = json.loads((ROOT / "Sources/MW2022/materials.json").read_text())["materials"]
    for key in ("wpn_p01_ar_mike16_smag_556n_v0", "wpn_p01_ar_mike4_xmag_556n_v0", "wpn_p01_ar_mike4_xmaglrg_556n_v0"):
        manifest["materials"][key] = shared_materials[f"easy/mw/weapons/iw9_mike4/{key}"]["vmat"]
    aliases, events = A.alias_files(), A.clip_events()
    def event_for(alias):
        [file] = aliases[alias]
        name = re.sub(r"^p01_ar_mike16_", "", Path(file).stem)
        event = A.DEST / "sounds" / f"m16_{name}.sound"
        if name in manifest["sounds"]:
            return manifest["sounds"][name]
        wav = event.with_suffix(".wav")
        A.ffmpeg(["-i", str(A.EXTRACTED / "sound" / file), "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le", str(wav)])
        A.sound_event(event, [wav], pitch="1", decibels=70, distance=1000, falloff=[{"y": 1}, {"x": 1}])
        manifest["sounds"][name] = A.asset_path(event)
        return A.asset_path(event)
    for suffix in W.M16.reload_variants:
        for prefix in ("reload", "reload_empty"):
            clip = prefix + suffix
            manifest["reloads"][clip] = A.timed(events[clip], event_for)
    save(path, manifest)


def build_meshes():
    port = Kastov(W.M16)
    pose = port.presentation()
    for name, triangles in {"": port.triangles(), **port.optional_triangles(), **port.choice_triangles()}.items():
        suffix = f"_{name}" if name else ""
        vname, wname = f"v_m16{suffix}", f"w_m16{suffix}"
        folder = W.M16.folder / "models"
        D.write_model(folder / f"{vname}.dmx", vname, port.nodes, port.locals_(pose), port.rebind(triangles, pose))
        nodes, bind, world = port.world_triangles(triangles)
        D.write_model(folder / f"{wname}.dmx", wname, nodes, bind, world)
        print(f"{name or 'receiver'}: {len(triangles)} triangles", flush=True)
    for suffix in W.M16.reload_variants:
        for prefix in ("reload", "reload_empty"):
            clip = prefix + suffix
            frames = port.play(clip, W.M16.hip)
            D.write_animation(W.M16.folder / "models/anims" / f"{clip}.dmx", clip, port.nodes,
                              [port.locals_(frame) for frame in frames], 30)
            print(f"{clip}: {len(frames)} frames", flush=True)


def resources():
    for category, keys in (("Stock", STOCKS), ("RearGrip", GRIPS), ("Barrel", BARRELS)):
        for key in keys:
            part = json.loads((SHARED / f"{key}.gnsmth").read_text())
            part["EligibleEquipment"] = [RESOURCE]
            part["Bodygroups"] = {}
            part.pop("ModelBodygroups", None)
            part["ModifyBodygroups"] = False
            # Only the M4 grip needs the original slightly reduced scale. M16 uses the source receiver dimensions.
            if category == "RearGrip":
                prefab = json.loads((SHARED / f"{key}.prefab").read_text())
                prefab = P.remap_guids(prefab, "m16/" + key)
                mount = P.component(prefab["RootObject"], "GunsmithMw22Attachment")
                mount["PartScale"] = "1,1,1"
                save(DEST / f"{key}.prefab", prefab)
                part["MainPrefab"]["prefab"] = f"gunsmith/m16/{key}.prefab"
            # The M4 part's weight is against the M4's parts; the M16A4's fixed stock and 20-inch barrel are heavier.
            part = part_masses.put(part, f"gunsmith/m16/{key}.gnsmth")
            save(DEST / f"{key}.gnsmth", part)
    sounds = P.m16_reload_sounds()
    for index, (choice, (key, capacity)) in enumerate(MAGAZINES.items()):
        if index == 0:
            continue
        clips = [f"{prefix}_{choice}" for prefix in ("reload", "reload_empty")]
        times = [(len(Smd(W.M16.decompiled / W.M16.cod_anims / f"{clip}.smd").frames) - 1) / 30 for clip in clips]
        save(DEST / f"{key}.gnsmth", part_masses.put({
            "Name": f"{capacity} Round Mag", "Category": "Magazine", "EligibleEquipment": [RESOURCE],
            "RequiredLevel": 0, "Description": f"{capacity}-round 5.56 magazine with its matching reload animations.",
            "ModifyBodygroups": True, "Bodygroups": {"magazine": index}, "MagazineCapacity": capacity,
            "ReloadTimeMultiplier": 1, "ReloadAnimation": index, "ReloadTime": round(times[0], 4),
            "EmptyReloadTime": round(times[1], 4), "ReloadSounds": sounds[clips[0]], "EmptyReloadSounds": sounds[clips[1]],
            "__references": [], "__version": 0,
        }, f"gunsmith/m16/{key}.gnsmth"))


def slots():
    config = P.PREFABS["m16"]
    for prefix in ("vm", "wm"):
        path = W.M16.folder / f"{prefix}_m16.prefab"
        document = json.loads(path.read_text())
        root = document["RootObject"]
        P.component(root, "SkinnedModelRenderer")["BodyGroups"] = config.default_mesh_groups
        for point in P.attachment_points(W.M16, config, prefix):
            category = point["Components"][0]["Category"]
            old = next((obj for obj in root["Children"] if any(c.get("Category") == category and
                        c.get("__type", "").endswith("GunsmithAttachmentPoint") for c in obj.get("Components", []))), None)
            if old is None:
                root["Children"].append(point)
        save(path, document)


def main():
    REPORT.mkdir(parents=True, exist_ok=True)
    before = protect_other_weapons()
    save(REPORT / "other-weapons-before.json", before)
    prepare_magazines()
    magazine_materials_and_sounds()
    if "--skip-meshes" not in sys.argv:
        build_meshes()
    resources()
    slots()
    import kastov_animgraph
    sys.argv = [sys.argv[0], "--weapon", "m16"]
    V.main()
    kastov_animgraph.main()
    after = protect_other_weapons()
    assert before == after, "Another weapon's attachment resource changed"
    save(REPORT / "build-validation.json", {"new_parts": 20, "other_weapon_files_unchanged": len(before)})
    print(f"Built 20 M16 parts; {len(before)} other attachment resources unchanged.", flush=True)


if __name__ == "__main__":
    main()

"""Offline Nano Drone asset checks; run with ordinary Python (numpy and Pillow).

Checks prefab references, rotor frames, all LOD mesh/UV/normal data, the complete
rotating geometry against the flight hull, textures and the looping sound. The
separate ReconChecks project tests the actual C# helpers with s&box math types.
These checks do not launch the game, use MCP, or claim to exercise a live match.
"""
import json
import math
import os
import re
import uuid
import wave
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "Assets"
MODELS = ASSETS / "models/recon_nano"
GEAR = ASSETS / "weapons/recon_nano"
SDK = Path(os.environ.get("NANO_SBOX_DIR", "D:/SteamLibrary/steamapps/common/sbox"))
checks, groups = 0, {}


def check(ok, message, group):
    global checks
    checks += 1
    groups[group] = groups.get(group, 0) + 1
    if not ok:
        raise AssertionError(message)


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def resource_exists(name):
    path = Path(name)
    roots = [ASSETS, SDK / "core", SDK / "addons/citizen/Assets", SDK / "addons/base/Assets"]
    if any((base / path).exists() or (base / (name + "_c")).exists() for base in roots):
        return True
    # Built-in human arms are downloaded s&box assets with a content hash in their cached filename.
    parent = SDK / "download/assets" / path.parent
    return parent.exists() and any(parent.glob(path.stem + ".*" + path.suffix + "_c"))


def values(node):
    if isinstance(node, dict):
        for v in node.values():
            yield from values(v)
    elif isinstance(node, list):
        for v in node:
            yield from values(v)
    elif isinstance(node, str):
        yield node


def nodes(node):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from nodes(v)
    elif isinstance(node, list):
        for v in node:
            yield from nodes(v)


def vector(text):
    return np.array([float(x) for x in text.split(",")])


def rot(q):
    x, y, z, w = q
    return np.array(((1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)),
                     (2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)),
                     (2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y))))


def mesh(path):
    v, uv, n, faces = [], [], [], []
    for line in path.read_text().splitlines():
        s = line.split()
        if not s:
            continue
        if s[0] == "v":
            v.append([float(x) for x in s[1:]])
        elif s[0] == "vt":
            uv.append([float(x) for x in s[1:]])
        elif s[0] == "vn":
            n.append([float(x) for x in s[1:]])
        elif s[0] == "f":
            faces.append([[int(i)-1 for i in x.split("/")] for x in s[1:]])
    v, uv, n, faces = np.asarray(v), np.asarray(uv), np.asarray(n), np.asarray(faces)
    check(all(np.isfinite(x).all() for x in (v, uv, n)), f"non-finite mesh: {path}", "mesh")
    check(faces.shape[1:] == (3, 3), f"invalid triangle/UV/normal indices: {path}", "mesh")
    for i, arr in enumerate((v, uv, n)):
        check((faces[..., i] >= 0).all() and (faces[..., i] < len(arr)).all(), f"bad index: {path}", "mesh")
    check((uv >= -1e-6).all() and (uv <= 1+1e-6).all(), f"UV outside atlas: {path}", "mesh")
    check(np.allclose(np.linalg.norm(n, axis=1), 1, atol=.001), f"invalid normals: {path}", "mesh")
    tris = v[faces[..., 0]]
    area = np.linalg.norm(np.cross(tris[:, 1]-tris[:, 0], tris[:, 2]-tris[:, 0]), axis=1)
    check((area > 1e-9).all(), f"degenerate triangles: {path}", "mesh")
    # The exporter writes OBJ Y-up as (game Y, game Z, game X).
    return v[:, [2, 0, 1]], len(faces)


def main():
    info = load(MODELS / "asset-info.json")
    airborne = load(GEAR / "recon_nano_airborne.prefab")["RootObject"]
    flight = next(c for c in airborne["Components"] if c["__type"] == "Facepunch.ReconOctocopter")
    hull_lo, hull_hi = vector(flight["Hull"]["Mins"]), vector(flight["Hull"]["Maxs"])
    check(np.allclose(hull_lo, info["hull_min"]) and np.allclose(hull_hi, info["hull_max"]),
          "equipment regenerated with current hull", "flight")
    check(flight["HandLaunched"] and flight["RotateCollisionHull"], "hand launch/rotating hull flags", "flight")
    check(0 < flight["SpoolSeconds"] < flight["LinkDelay"] <= 1., "hand release before feed", "flight")
    check(flight["CameraZoomSteps"] == [1, 2, 4], "nano camera zoom", "flight")
    check(flight["BatterySeconds"] == 120 and flight["HoverRpm"] == 4800, "flight battery/RPM", "flight")
    check(0 < flight["CrashSpeed"] < flight["CruiseSpeed"] < flight["SportSpeed"], "usable flight limits", "flight")
    check(flight["ImpactDamageThreshold"] < flight["CrashSpeed"], "crash damages fragile aircraft", "flight")

    for path in GEAR.glob("*.prefab"):
        data = load(path)
        entries = {d["__guid"]: d for d in nodes(data) if "__guid" in d}
        ids = [d["__guid"] for d in nodes(data) if "__guid" in d]
        check(len(ids) == len(entries), f"duplicate IDs in {path}", "prefab")
        for node in nodes(data):
            for key in ("component_id", "go"):
                if key in node:
                    check(node[key] in entries, f"unresolved {key}: {path}: {node[key]}", "prefab")
            if "component_id" in node:
                check(entries[node["component_id"]]["__type"].endswith(node["component_type"]),
                      f"wrong component type in {path}", "prefab")
        for value in values(data):
            if value.startswith(("models/", "weapons/", "sounds/", "ui/", "prefabs/")) and value.endswith(
                    (".vmdl", ".prefab", ".equip", ".sound", ".svg", ".vanmgrph")):
                check(resource_exists(value), f"missing prefab asset: {path}: {value}", "references")

    resource = load(GEAR / "recon_nano.equip")
    check(resource["Slot"] == "Tactical" and resource["IsPurchasable"], "available tactical equipment", "equipment")
    for key in ("MainPrefab", "ViewModelPrefab", "WorldModelPrefab"):
        check((ASSETS / resource[key]["prefab"]).exists(), f"missing {key}", "equipment")
    weapon = load(GEAR / "weapon_recon_nano.prefab")
    launch = next(d for d in nodes(weapon) if d.get("__type") == "Facepunch.ReconTabletLink")
    check(launch["HandLaunch"] and launch["LaunchDistance"] == 32, "hand launch link configuration", "equipment")
    check(launch["Prefab"]["prefab"] == "weapons/recon_nano/recon_nano_airborne.prefab", "correct airborne prefab", "equipment")
    check(flight["StationResourcePath"] == "weapons/recon_nano/recon_nano.equip", "only its own tablet is retired", "equipment")
    for kind in ("vm", "wm"):
        tablet = load(GEAR / f"{kind}_recon_nano.prefab")
        check("models/recon_octocopter/recon_tablet.vmdl" in list(values(tablet)), "shared recon tablet model", "equipment")

    all_vertices = {}
    for name, lods in info.items():
        if not isinstance(lods, dict) or "lod0" not in lods:
            continue
        vmdl = MODELS / f"{name}.vmdl"
        text = vmdl.read_text()
        for reference in re.findall(r'(?:filename|to)\s*=\s*"([^"]+)"', text):
            check((ASSETS / reference).exists(), f"missing model reference {reference}", "references")
        for lod, data in lods.items():
            verts, tris = mesh(MODELS / f"{name}_{lod}.obj")
            all_vertices[f"{name}_{lod}"] = verts
            check(tris == data["triangles"], f"triangle count in {name}/{lod}", "mesh")
            check(np.allclose(verts.min(0), data["bounds_min"], atol=.00003)
                  and np.allclose(verts.max(0), data["bounds_max"], atol=.00003), f"bounds/axis mismatch {name}/{lod}", "mesh")
        if "lod1" in lods:
            check(lods["lod1"]["triangles"] < lods["lod0"]["triangles"], f"no LOD reduction {name}", "mesh")

    assemblies = [all_vertices["recon_nano_lod0"], all_vertices["recon_nano_gimbal_lod0"] + info["gimbal_pivot"]]
    mounts = {c["Name"]: c for c in airborne["Children"]}
    for rotor in info["rotors"]:
        which = rotor["name"]
        mount = mounts[which.title() + " Rotor Mount"]
        component = mount["Children"][0]["Components"][0]
        frame = rot(rotor["rotation"])
        check(np.allclose(vector(mount["Rotation"]), rotor["rotation"]), "fixed rotor mount orientation", "rotors")
        axis = frame @ np.array((0, 0, 1))
        check(np.allclose(axis, (0, 0, 1) if which == "main" else (0, -1, 0)), "tail rotor has vertical plane", "rotors")
        check(component["RpmScale"] == rotor["rpm_scale"] and not component["Yoke"], "rotor speed and hub style", "rotors")
        check(math.isclose(component["ShaderScale"] * rotor["radius"] / 39.37008, .330), "blur matches blade radius", "rotors")
        for kind in ("prop", "hub", "disc"):
            verts = all_vertices[f"recon_nano_{kind}_{which}_lod0"]
            for degrees in range(0, 360, 5):
                a = math.radians(degrees)
                turn = np.array(((math.cos(a), -math.sin(a), 0), (math.sin(a), math.cos(a), 0), (0, 0, 1)))
                assemblies.append(verts @ turn.T @ frame.T + rotor["position"])
    for v in assemblies:
        check((v >= hull_lo - .00003).all() and (v <= hull_hi + .00003).all(),
              f"geometry outside flight hull: {v.min(0)}, {v.max(0)}", "collision")

    for kind in ("color", "rough", "metal", "ao", "normal"):
        image = np.asarray(Image.open(MODELS / f"recon_nano_{kind}.png"))
        check(image.shape[:2] == (1024, 1024), f"texture dimensions {kind}", "textures")
        check(np.any(image > 0), f"blank texture {kind}", "textures")
    materials = "\n".join(q.read_text() for q in MODELS.glob("*.vmat"))
    for path in re.findall(r'"(models/[^"]+\.png)"', materials):
        check((ASSETS / path).exists(), f"missing texture {path}", "references")
    shader = (ASSETS / "shaders/hc1_rotor_blur.shader").read_text()
    check('Attribute( "RotorScale" )' in shader and 'Attribute( "RotorYoke" )' in shader, "shared scaled blur shader", "rotors")

    sound = ASSETS / "sounds/drones/nano_rotors.wav"
    with wave.open(str(sound), "rb") as wav:
        check(wav.getnchannels() == 1 and wav.getsampwidth() == 2, "mono 16-bit rotor loop", "audio")
        check(wav.getnframes() == 8 * wav.getframerate(), "8 second loop", "audio")
        pcm = np.frombuffer(wav.readframes(wav.getnframes()), np.int16).astype(float) / 32768
        rate = wav.getframerate()
    check(np.max(np.abs(pcm)) < .99, "no audio clipping", "audio")
    check(np.max(np.abs(pcm)) < .05, "quiet level retained in source PCM", "audio")
    check(abs(pcm[-1]-pcm[0]) < .12, "no abrupt loop boundary", "audio")
    spectrum, f = np.abs(np.fft.rfft(pcm)), np.fft.rfftfreq(len(pcm), 1/rate)
    for frequency in (160, 672):
        check(spectrum[np.abs(f-frequency) < 4].max() > np.median(spectrum) * 10, f"rotor tone {frequency}", "audio")
    meta, event = load(sound.with_name(sound.name + ".meta")), load(sound.with_suffix(".sound"))
    check(meta["loop"] and not meta["compress"], "loop import metadata", "audio")
    check(event["Sounds"] == ["sounds/drones/nano_rotors.vsnd"] and not event["UI"]
          and event["DistanceAttenuation"] and event["Distance"] < 800, "quiet positional sound event", "audio")
    check(float(event["Volume"]) == 1, "PCM level is not applied twice", "audio")

    guids = []
    for folder in (MODELS, GEAR):
        for path in folder.iterdir():
            if path.suffix in (".vmdl", ".vmat", ".png", ".obj", ".prefab", ".equip"):
                check(path.with_name(path.name + ".meta").exists(), f"missing import ID {path}", "metadata")
        for path in folder.glob("*.meta"):
            guids.append(str(uuid.UUID(load(path)["guid"])))
    check(len(set(guids)) == len(guids), "unique import IDs", "metadata")

    report = {"result": "passed", "checks": checks, "groups": groups,
              "scope": "Offline source/asset and geometry validation; no live game or editor was used."}
    dest = ROOT / "output/recon-nano/asset-checks.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: {checks} Nano Drone asset checks ({', '.join(groups)}).")


if __name__ == "__main__":
    main()

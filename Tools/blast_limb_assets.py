"""Split military clothing at the knees/elbows, retaining its textures and skin weights.

The authored ragdoll bones drive both sides after a blast releases their joint. Opposite
cut surfaces have separate weights, so no sleeve/trouser triangles stretch across the gap.
Uses the installed citizen assets; leaves their sources unchanged.
"""
from pathlib import Path
import argparse
import json
import os
import struct
import subprocess

import numpy as np

from kastov_gltf import GltfModel, CONV, INCH
from kastov_dmx import write_model

ROOT = Path(__file__).resolve().parents[1]
CITIZEN = Path(os.environ.get("SBOX_CITIZEN_ASSETS", "D:/SteamLibrary/steamapps/common/sbox/addons/citizen/Assets"))
CACHE = ROOT / "output/blast-limbs/source"
DEST = ROOT / "Assets/models/dismemberment"
SOURCES = {
    "trousers": "models/citizen_clothes/trousers/cargopants/models/cargo_pants_m_human.vmdl_c",
    "shirt": "models/citizen_clothes/shirt/army_shirt/model/army_shirt_m_human.vmdl_c",
}
MATERIALS = {
    "trousers": "models/citizen_clothes/trousers/cargopants/Textures/cargo_pants_army.vmat",
    "shirt": "models/citizen_clothes/shirt/army_shirt/Textures/army_shirt.vmat",
}
CUT_MATERIAL = "materials/dismemberment/cloth_interior.vmat"


def export(name, resource):
    target = CACHE / (name + ".vmdl_c")
    glb = target.with_suffix("").with_suffix(".glb")
    if glb.exists():
        return glb
    data = bytearray((CITIZEN / resource).read_bytes())
    _, _, _, relative, count = struct.unpack_from("<IHHII", data, 0)
    table = relative + 8
    entries = []
    for i in range(count):
        at = table + i * 12
        rel, length = struct.unpack_from("<II", data, at + 4)
        if data[at:at + 4] != b"GUID":
            entries.append((data[at:at + 4], at + 4 + rel, length))
    for i, (kind, absolute, length) in enumerate(entries):
        at = table + i * 12
        data[at:at + 4] = kind
        struct.pack_into("<II", data, at + 4, absolute - at - 4, length)
    struct.pack_into("<I", data, 12, len(entries))
    CACHE.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    result = subprocess.run(["rtk", "proxy", "dotnet", "run", "--project", str(ROOT / "Tools/BlastLimbExport"), "--", str(target), str(glb)],
                            capture_output=True, text=True, timeout=120)
    if result.returncode or not glb.exists():
        raise RuntimeError(result.stdout + result.stderr)
    return glb


def unit(vector):
    return vector / max(np.linalg.norm(vector), 1e-12)


def interpolate(a, b, amount):
    return [a[i] + (b[i] - a[i]) * amount for i in range(4)]


def clip(vertices, point, normal, positive):
    """Sutherland-Hodgman clipping with interpolated UVs, normals and skin weights."""
    result = []
    for a, b in zip(vertices, vertices[1:] + vertices[:1]):
        da, db = np.dot(a[0] - point, normal), np.dot(b[0] - point, normal)
        inside_a, inside_b = (da >= -1e-8, db >= -1e-8) if positive else (da <= 1e-8, db <= 1e-8)
        if inside_a:
            result.append(a)
        if inside_a != inside_b:
            result.append(interpolate(a, b, da / (da - db)))
    return result


def boundary_loops(segments):
    """Join the cut's triangle-edge segments into closed cloth contours, including pockets."""
    points, graph = {}, {}
    for a, b in segments:
        ka, kb = tuple(np.round(a, 4)), tuple(np.round(b, 4))
        if ka == kb:
            continue
        points[ka], points[kb] = a, b
        graph.setdefault(ka, set()).add(kb)
        graph.setdefault(kb, set()).add(ka)
    remaining = {frozenset((a, b)) for a, neighbours in graph.items() for b in neighbours}
    loops = []
    while remaining:
        first_edge = next(iter(remaining))
        first, current = tuple(first_edge)
        remaining.remove(first_edge)
        loop = [first, current]
        while current != first:
            candidates = [b for b in graph[current] if frozenset((current, b)) in remaining]
            if not candidates:
                break
            nxt = candidates[0]
            remaining.remove(frozenset((current, nxt)))
            loop.append(nxt)
            current = nxt
        if current == first and len(loop) >= 4:
            loops.append([points[k] for k in loop[:-1]])
    return loops


def build(name, gltf):
    pose, hierarchy = gltf.pose(), gltf.hierarchy()
    bone_names = list(hierarchy)
    region = "leg" if name == "trousers" else "arm"
    # Garment skeletons omit the unweighted physics bones. Add those at their matching twist-0 bind poses.
    for side in ("L", "R"):
        for part in ("upper", "lower"):
            bone = f"{region}_{part}_{side}"
            pose[bone] = pose[f"{bone}_twist0"].copy()
            hierarchy[bone] = ("pelvis" if region == "leg" else f"clavicle_{side}") if part == "upper" else f"{region}_upper_{side}"
            bone_names.append(bone)
    indices = {n: i for i, n in enumerate(bone_names)}
    nodes = [(n, indices.get(hierarchy[n], -1)) for n in bone_names]
    locals_ = [np.linalg.inv(pose[hierarchy[n]]) @ pose[n] if hierarchy[n] else pose[n] for n in bone_names]
    cuts = {}
    for side in ("L", "R"):
        bone = f"{region}_lower_{side}"
        point = pose[bone][:3, 3]
        normal = unit(pose[f"{bone}_twist1"][:3, 3] - point)
        cuts[side] = (point, normal)

    triangles, segments = [], {"L": [], "R": []}
    original_regions = {"L": [], "R": [], None: []}
    split_regions = {"L": [], "R": [], None: []}
    source_area = 0.0
    checks = {"source_triangles": 0, "triangles": 0, "cross_cut_influences": 0, "caps": {}}
    for node in gltf.nodes:
        if "mesh" not in node:
            continue
        joints = gltf.json["skins"][node["skin"]]["joints"]
        for primitive in gltf.json["meshes"][node["mesh"]]["primitives"]:
            attr = primitive["attributes"]
            positions = gltf._accessor(attr["POSITION"]).astype(float) @ CONV / INCH
            uvs = gltf._accessor(attr["TEXCOORD_0"]).astype(float)
            faces = gltf._accessor(primitive["indices"]).reshape(-1, 3)
            # Smooth per-position normals preserve smooth clothing across duplicate UV vertices.
            normals = {}
            for face in faces:
                a, b, c = positions[face]
                area = np.cross(b - a, c - a)
                for p in positions[face]:
                    key = tuple(np.round(p, 5))
                    normals[key] = normals.get(key, np.zeros(3)) + area
            weights = np.zeros((len(positions), len(nodes)))
            original_weights = np.zeros_like(weights)
            raw_joints = gltf._accessor(attr["JOINTS_0"])
            raw_weights = gltf._accessor(attr["WEIGHTS_0"]).astype(float)
            for row, (bones, values) in enumerate(zip(raw_joints, raw_weights)):
                for joint, weight in zip(bones, values):
                    n = gltf.nodes[joints[int(joint)]]["name"]
                    original_weights[row, indices[n]] += weight
                    # The split pieces follow the rigid limb bones, rather than procedural twist/helper bones
                    # that would still average transformations across a released joint.
                    if n.startswith(region + "_") and "twist" in n:
                        n = n.split("_twist")[0]
                    if n.startswith(region + ("_knee_helper_" if region == "leg" else "_elbow_helper_")):
                        n = f"{region}_upper_{n[-1]}"
                    weights[row, indices[n]] += weight
            for face in faces:
                checks["source_triangles"] += 1
                a, b, c = positions[face]
                source_area += np.linalg.norm(np.cross(b - a, c - a)) * 0.5
                verts = [[positions[i], unit(normals[tuple(np.round(positions[i], 5))]), uvs[i], weights[i]] for i in face]
                centre = np.mean(positions[face], axis=0)
                side = "L" if centre[1] > 0 else "R"
                if region == "arm" and abs(centre[1]) < 9.0:
                    side = None
                original = (MATERIALS[name], [
                    (positions[i], unit(normals[tuple(np.round(positions[i], 5))]), uvs[i],
                     [(b, float(w)) for b, w in enumerate(original_weights[i]) if w > 1e-6]) for i in face
                ])
                original_regions[side].append(original)
                pieces = [(verts, None)]
                if side:
                    point, normal = cuts[side]
                    distances = [(v[0] - point) @ normal for v in verts]
                    pieces = [(clip(verts, point, normal, positive), positive) for positive in (False, True)]
                    if min(distances) < -1e-6 and max(distances) > 1e-6:
                        edge = []
                        for a, b, da, db in zip(verts, verts[1:] + verts[:1], distances, distances[1:] + distances[:1]):
                            if da * db < 0:
                                edge.append(interpolate(a, b, da / (da - db))[0])
                        if len(edge) == 2:
                            segments[side].append(edge)
                for polygon, lower in pieces:
                    final = []
                    for p, n, uv, w in polygon:
                        w = w.copy()
                        if side:
                            detached = {f"{region}_lower_{side}", f"ankle_{side}"} if region == "leg" else {f"arm_lower_{side}", f"hand_{side}", f"finger_thumb_0_{side}"}
                            for i, bone_name in enumerate(bone_names):
                                if (bone_name in detached) != lower:
                                    w[i] = 0
                            if w.sum() < 1e-8:
                                w[indices[f"{region}_{'lower' if lower else 'upper'}_{side}"]] = 1
                        w /= max(w.sum(), 1e-12)
                        final.append((p, unit(n), uv, [(i, float(v)) for i, v in enumerate(w) if v > 1e-6]))
                    for i in range(1, len(final) - 1):
                        tri = [final[0], final[i], final[i + 1]]
                        if np.linalg.norm(np.cross(tri[1][0] - tri[0][0], tri[2][0] - tri[0][0])) > 1e-8:
                            triangles.append((MATERIALS[name], tri))
                            split_regions[side].append((MATERIALS[name], tri))
    emitted_area = 0.0
    for _, vertices in triangles:
        a, b, c = [v[0] for v in vertices]
        emitted_area += np.linalg.norm(np.cross(b - a, c - a)) * 0.5
        for side in ("L", "R"):
            detached = {f"{region}_lower_{side}", f"ankle_{side}"} if region == "leg" else {f"arm_lower_{side}", f"hand_{side}", f"finger_thumb_0_{side}"}
            # A translated detached subtree must move the whole triangle or none of it, with no stretching.
            portions = [sum(w for i, w in v[3] if bone_names[i] in detached) for v in vertices]
            if not (all(abs(w) < 1e-5 for w in portions) or all(abs(w - 1) < 1e-5 for w in portions)):
                checks["cross_cut_influences"] += 1
    assert checks["cross_cut_influences"] == 0, checks
    assert abs(source_area - emitted_area) < source_area * 1e-6, (source_area, emitted_area)
    checks["surface_area_preserved"] = True
    DEST.mkdir(parents=True, exist_ok=True)
    write_model(DEST / f"{name}.dmx", name, nodes, locals_, triangles)
    mesh_files = [(name, f"models/dismemberment/{name}.dmx")]
    for side, label in (("L", "left"), ("R", "right")):
        other = "R" if side == "L" else "L"
        # Preserve the opposite side's original smooth skinning, rather than putting an invisible cut into its joint.
        variant = original_regions[None] + original_regions[other] + split_regions[side]
        moving_bones = {n for n in bone_names if n.startswith(f"{region}_lower_{side}")}
        moving_bones |= {f"ankle_{side}"} if region == "leg" else {f"hand_{side}", f"finger_thumb_0_{side}"}
        for _, vertices in variant:
            portions = [sum(w for i, w in v[3] if bone_names[i] in moving_bones) for v in vertices]
            assert all(abs(w) < 1e-5 for w in portions) or all(abs(w - 1) < 1e-5 for w in portions), (name, side, portions)
        checks[f"{label}_only_skinning_valid"] = True
        mesh = f"{name}_{label}_only"
        write_model(DEST / f"{mesh}.dmx", mesh, nodes, locals_, variant)
        mesh_files.append((mesh, f"models/dismemberment/{mesh}.dmx"))
    for side in ("L", "R"):
        cap_triangles = []
        point, normal = cuts[side]
        for loop in boundary_loops(segments[side]):
            centre = np.mean(loop, axis=0)
            for lower in (False, True):
                facing = -normal if lower else normal
                inset = normal * (0.025 if lower else -0.025)
                bone = indices[f"{region}_{'lower' if lower else 'upper'}_{side}"]
                for a, b in zip(loop, loop[1:] + loop[:1]):
                    corners = [centre + inset, a + inset, b + inset]
                    if np.dot(np.cross(corners[1] - corners[0], corners[2] - corners[0]), facing) < 0:
                        corners[1], corners[2] = corners[2], corners[1]
                    cap_triangles.append((CUT_MATERIAL, [(p, facing, (0, 0), [(bone, 1.0)]) for p in corners]))
        assert cap_triangles, f"no closed {side} cut contour for {name}"
        checks["caps"][side] = len(cap_triangles)
        mesh = f"{name}_{side.lower()}_cut"
        write_model(DEST / f"{mesh}.dmx", mesh, nodes, locals_, cap_triangles)
        mesh_files.append((mesh, f"models/dismemberment/{mesh}.dmx"))
    from kastov_vmdl import model, render_meshes, list_node
    groups = [f'{{ _class = "BodyGroup" name = "CutPattern" children = [ '
              f'{{ _class = "BodyGroupChoice" name = "left" meshes = [ "{name}_left_only" ] }}, '
              f'{{ _class = "BodyGroupChoice" name = "right" meshes = [ "{name}_right_only" ] }}, '
              f'{{ _class = "BodyGroupChoice" name = "both" meshes = [ "{name}" ] }} ] }},']
    for side, label in (("L", "LeftCut"), ("R", "RightCut")):
        groups.append(f'{{ _class = "BodyGroup" name = "{label}" children = [ {{ _class = "BodyGroupChoice" name = "intact" meshes = [ ] }}, {{ _class = "BodyGroupChoice" name = "cut" meshes = [ "{name}_{side.lower()}_cut" ] }} ] }},')
    (DEST / f"{name}.vmdl").write_text(model([
        '{ _class = "BoneMarkupList" bone_cull_type = "None" },',
        render_meshes(mesh_files), list_node("BodyGroupList", groups)
    ]), encoding="utf-8")
    checks["triangles"] = len(triangles)
    (CACHE.parent / f"{name}.mesh-check.json").write_text(json.dumps(checks, indent=2) + "\n")
    print(name, checks)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--export-only", action="store_true")
    args = parser.parse_args()
    for name, source in SOURCES.items():
        path = export(name, source)
        model = GltfModel(path)
        print(name, [(m.get("name"), len(m["primitives"])) for m in model.json["meshes"]],
              [m.get("name") for m in model.json.get("materials", [])])
        if args.export_only:
            continue
        build(name, model)


if __name__ == "__main__":
    main()

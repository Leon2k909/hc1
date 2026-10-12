"""Split the flip-to-side magnifier optics so T swings the magnifier out of the way.

python Tools/flip_magnifiers.py [--check]

A magnifier behind a red dot or holographic sight sits on a flip-to-side mount: the shooter
swings it off the sight line and aims through the front sight at 1x. Each model's OBJ is cut
into the part that stays on the rail (the front sight, the mount's base and lever) and the part
that swings (the magnifier's body and glass), both in the original model space:

    <stem>_mount.obj/.vmdl       the prefab root's model
    <stem>_magnifier.obj/.vmdl   a "Magnifier" child, turned by GunsmithFlipMagnifier

The original models stay as they were (the eye relief and alternate-sight figures are read
from them). The prefabs (M4 and MP5) get the split models, and the parts their alternate sight:
the front sight at 1x, its glass centre moved onto the scope's axis (as hybrid_optic_sights.py
does for the hybrid optics).

How a model is cut (OBJ axes: +x the gun's left, +y up, +z forward):
  - the front sight's materials stay;
  - the magnifier body's material is welded into pieces (shared positions); a piece no higher
    than `base` stays, and with `cut` set, the body's one welded shell is cut there by face;
  - everything else (the magnifier's glass, its reticle and stencil) swings.
The hinge runs along the bore through (x, y), and the magnifier turns `angle` degrees about it:
positive swings its top to the gun's right, as Rotation.FromAxis( Vector3.Forward, angle ).
"""
import argparse
import json
import math
import re
import uuid
from pathlib import Path

from optic_eyepieces import obj_triangles

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "Assets"
MODELS = "attachments/mw2022/models"
HEADER = "# Original Source units; Y,Z,X file axes counter ModelDoc OBJ conversion."

PARTS = {
    # 2x magnifier behind a mini red dot: the mount's lever is on the right, so it swings right.
    "att_vm_2x_west01": dict(
        front={"m_2e740c15f567", "m_916c79cb4d3d", "m_75147d65bdca"}, body="m_6fd1a6b10947",
        base=0.25, cut=0.25, hinge=(-0.551, 0.25), angle=90.0, lens="m_916c79cb4d3d",
        drop=set(),
    ),
    # 2x magnifier behind a holographic sight.
    "att_vm_2x_west02": dict(
        front={"m_5eddbf80141d", "m_609686a929ab"}, body="m_54768067cdff",
        base=0.53, cut=None, hinge=(-0.78, 0.4), angle=90.0, lens="m_5eddbf80141d",
        drop=set(),
    ),
    # 3x flip magnifier behind a holographic sight, hinged on the left. Its lens bodygroup's
    # "hide" mesh (mesh_01) is a cap for the folded state the gunsmith never shows.
    "att_vm_hybrid_west02": dict(
        front={"m_c7fd9dc28b82", "m_a3ce9e906f69", "m_b9afdf1ca558"}, body="m_62d56b656834",
        base=0.62, cut=None, hinge=(0.75, 0.47), angle=-90.0, lens="m_a3ce9e906f69",
        drop={"mesh_01"},
    ),
}

PREFABS = {
    "gunsmith/m4a1/mw2022/att_vm_2x_west01.prefab": "att_vm_2x_west01",
    "gunsmith/m4a1/mw2022/att_vm_2x_west02.prefab": "att_vm_2x_west02",
    "gunsmith/m4a1/mw2022/att_vm_hybrid_west02.prefab": "att_vm_hybrid_west02",
    "gunsmith/m4a1/mw2022/att_vm_hybrid_west02_thermal.prefab": "att_vm_hybrid_west02",
    "attachments/mpapa5/prefabs/att_vm_2x_west01.prefab": "att_vm_2x_west01",
    "attachments/mpapa5/prefabs/att_vm_2x_west02.prefab": "att_vm_2x_west02",
}

GNSMTH = {
    "gunsmith/m4a1/mw2022/att_vm_2x_west01.gnsmth": "att_vm_2x_west01",
    "gunsmith/m4a1/mw2022/att_vm_2x_west02.gnsmth": "att_vm_2x_west02",
    "gunsmith/m4a1/mw2022/att_vm_hybrid_west02.gnsmth": "att_vm_hybrid_west02",
    "gunsmith/m4a1/mw2022/att_vm_hybrid_west02_thermal.gnsmth": "att_vm_hybrid_west02",
    "gunsmith/mpapa5/optics/att_vm_2x_west01.gnsmth": "att_vm_2x_west01",
    "gunsmith/mpapa5/optics/att_vm_2x_west02.gnsmth": "att_vm_2x_west02",
}


def guid(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"hc1/flip_magnifiers/{name}"))


def read_obj(path):
    """Raw v/vt/vn lines per vertex, and faces as (object, material, (i, j, k)) with 0-based indices."""
    v, vt, vn, faces = [], [], [], []
    obj = mat = None
    for line in path.read_text(encoding="utf-8").splitlines():
        tag = line.split(" ", 1)[0]
        if tag == "v":
            v.append(line)
        elif tag == "vt":
            vt.append(line)
        elif tag == "vn":
            vn.append(line)
        elif tag == "o":
            obj = line[2:]
        elif tag == "usemtl":
            mat = line[7:]
        elif tag == "f":
            ids = []
            for token in line[2:].split():
                a, b, c = token.split("/")
                assert a == b == c, (path, line)
                ids.append(int(a) - 1)
            assert len(ids) == 3, (path, line)
            faces.append((obj, mat, tuple(ids)))
    assert len(v) == len(vt) == len(vn), path
    return v, vt, vn, faces


def position(line):
    return tuple(float(x) for x in line.split()[1:4])


def classify(cfg, v, faces):
    """'mount' or 'magnifier' per face, or None to leave it out."""
    pos = [position(line) for line in v]
    body = [f for f in faces if f[1] == cfg["body"] and f[0] not in cfg["drop"]]
    parent = list(range(len(v)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            parent[a] = b

    welded = {}
    for _, _, ids in body:
        union(ids[0], ids[1])
        union(ids[1], ids[2])
        for i in ids:
            key = tuple(round(x, 4) for x in pos[i])
            union(i, welded.setdefault(key, i))
    top = {}
    for _, _, ids in body:
        for i in ids:
            root = find(i)
            top[root] = max(top.get(root, -math.inf), pos[i][1])

    kinds = []
    for obj, mat, ids in faces:
        if obj in cfg["drop"]:
            kinds.append(None)
        elif mat in cfg["front"]:
            kinds.append("mount")
        elif mat == cfg["body"]:
            if top[find(ids[0])] <= cfg["base"] + 1e-6:
                kinds.append("mount")
            elif cfg["cut"] is not None and max(pos[i][1] for i in ids) <= cfg["cut"] + 1e-6:
                kinds.append("mount")
            else:
                kinds.append("magnifier")
        else:
            kinds.append("magnifier")
    return kinds


def obj_text(stem, v, vt, vn, faces):
    order = sorted({i for _, _, ids in faces for i in ids})
    index = {old: new + 1 for new, old in enumerate(order)}
    lines = [HEADER, f"mtllib {stem}.mtl"]
    for i in order:
        lines += [v[i], vt[i], vn[i]]
    lines.append("o mesh_00")
    materials = list(dict.fromkeys(mat for _, mat, _ in faces))
    for mat in materials:
        lines.append(f"usemtl {mat}")
        lines += ["f " + " ".join(f"{index[i]}/{index[i]}/{index[i]}" for i in ids) for _, m, ids in faces if m == mat]
    return "\r\n".join(lines) + "\r\n", materials


def vmdl_text(folder, stem, remaps, materials):
    remap = ", ".join(f'{{ from = "{m}.vmat" to = "{remaps[m + ".vmat"]}" }}' for m in materials)
    return "\r\n".join([
        "<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->",
        '{ rootNode = { _class = "RootNode" children = [',
        f'{{ _class = "MaterialGroupList" children = [ {{ _class = "DefaultMaterialGroup" remaps = [ {remap} ] use_global_default = false }} ] }},',
        f'{{ _class = "RenderMeshList" children = [ {{ _class = "RenderMeshFile" name = "mesh_00" filename = "{folder}/{stem}.obj" '
        'import_translation = [0,0,0] import_rotation = [0,0,0] import_scale = 1 align_origin_x_type = "None" '
        'align_origin_y_type = "None" align_origin_z_type = "None" import_filter = { exclude_by_default = true '
        'exception_list = [ "mesh_00" ] } } ] },',
        "] } }",
    ]) + "\r\n"


def meta_text(path):
    """Keep an existing asset GUID; a new file gets a stable one."""
    if path.exists():
        return path.read_text(encoding="utf-8-sig")
    return '{\r\n  "guid": "' + guid(path.relative_to(ASSETS).as_posix()) + '"\r\n}'


def model_files(name, cfg):
    """{path: text} for the split models of one optic."""
    folder = f"{MODELS}/{name}"
    source = ASSETS / folder / f"{name}.obj"
    remaps = dict(re.findall(r'from = "([^"]+)" to = "([^"]+)"', (source.with_suffix(".vmdl")).read_text(encoding="utf-8")))
    v, vt, vn, faces = read_obj(source)
    kinds = classify(cfg, v, faces)
    files = {}
    for kind in ("mount", "magnifier"):
        stem = f"{name}_{kind}"
        picked = [f for f, k in zip(faces, kinds) if k == kind]
        assert picked, (name, kind)
        obj, materials = obj_text(stem, v, vt, vn, picked)
        base = ASSETS / folder / stem
        files[base.with_suffix(".obj")] = obj
        files[base.with_suffix(".mtl")] = "".join(f"newmtl {m}\r\nKd 1 1 1\r\n" for m in materials)
        files[base.with_suffix(".vmdl")] = vmdl_text(folder, stem, remaps, materials)
        for suffix in (".obj.meta", ".vmdl.meta"):
            meta = base.with_name(stem + suffix)
            files[meta] = meta_text(meta)
        print(f"  {stem}: {len(picked)} triangles, {', '.join(remaps[m + '.vmat'].rsplit('/', 1)[-1] for m in materials)}")
    return files


def prefab_text(path, name, cfg):
    prefab = json.loads(path.read_text(encoding="utf-8"))
    root = prefab["RootObject"]
    renderer = next(c for c in root["Components"] if c["__type"] == "Sandbox.ModelRenderer")
    renderer["Model"] = f"{MODELS}/{name}/{name}_mount.vmdl"
    for component in root["Components"]:
        if component["__type"].endswith("GunsmithMw22Attachment"):
            # The split models have no lens bodygroup: its "show" choice is baked in.
            component["BodygroupChoices"] = {}
    key = path.relative_to(ASSETS).as_posix()
    child = {
        "__guid": guid(f"{key}/object"),
        "Flags": 0,
        "Name": "Magnifier",
        "Position": "0,0,0",
        "Rotation": "0,0,0,1",
        "Scale": "1,1,1",
        "Enabled": True,
        "NetworkMode": 1,
        "Components": [
            {
                "__type": "Sandbox.ModelRenderer",
                "__guid": guid(f"{key}/renderer"),
                "__enabled": True,
                "Model": f"{MODELS}/{name}/{name}_magnifier.vmdl",
                "Tint": "1,1,1,1",
            },
            {
                "__type": "Facepunch.Gunsmith.GunsmithFlipMagnifier",
                "__guid": guid(f"{key}/flip"),
                "__enabled": True,
                "Hinge": f"0,{cfg['hinge'][0]:g},{cfg['hinge'][1]:g}",
                "FlipAngle": cfg["angle"],
            },
        ],
        "Children": [],
    }
    children = root.setdefault("Children", [])
    children[:] = [c for c in children if c.get("Name") != "Magnifier"] + [child]
    return json.dumps(prefab, indent=2) + "\n"


def sight_values(name, cfg):
    vertices, used = obj_triangles(ASSETS / MODELS / name / f"{name}.obj")

    def box(material):
        return tuple(zip(*(vertices[i] for i in used[material])))

    def centre(axes):
        return tuple((min(a) + max(a)) * 0.5 for a in axes)

    scope, front = centre(box("m_853afc05898f")), box(cfg["lens"])
    reflex = centre(front)
    radius = min(max(a) - min(a) for a in front[1:]) * 0.45
    return {
        "HasAlternateSight": True,
        "AlternateSightAimOffset": ",".join(f"{x:.6f}" for x in (0.0, scope[1] - reflex[1], scope[2] - reflex[2])),
        "AlternateSightAimAngles": "0,0,0",
        "AlternateSightMagnification": 1,
        "AlternateSightEyepiece": ",".join(f"{x:.6f}" for x in reflex),
        "AlternateSightRadius": round(radius, 6),
    }


def gnsmth_text(path, values):
    text = path.read_text(encoding="utf-8")
    new = text
    for key, value in values.items():
        encoded = json.dumps(value)
        line = re.compile(rf'("{key}": )("[^"\n]*"|[^,\n}}]+)')
        if line.search(new):
            new = line.sub(lambda m: m.group(1) + encoded, new, count=1)
        else:
            new = re.sub(r'(\n(\s*)"[^"\n]+": [^\n]*?)(\n\})\s*$',
                         lambda m: f'{m.group(1)},\n{m.group(2)}"{key}": {encoded}{m.group(3)}\n', new, count=1)
    actual = json.loads(new)
    assert all(actual[key] == value for key, value in values.items()), path
    return new


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="report files that would change, write nothing")
    args = parser.parse_args()
    files = {}
    for name, cfg in PARTS.items():
        print(name)
        files.update(model_files(name, cfg))
    for rel, name in PREFABS.items():
        path = ASSETS / rel
        files[path] = prefab_text(path, name, PARTS[name])
    for rel, name in GNSMTH.items():
        path = ASSETS / rel
        values = sight_values(name, PARTS[name])
        files[path] = gnsmth_text(path, values)
        print(f"{rel}: front sight {values['AlternateSightAimOffset']} r {values['AlternateSightRadius']}")
    stale = [p for p, text in files.items() if not p.exists() or p.read_bytes() != text.encode("utf-8")]
    # Metas first, so the editor imports each new model under its own GUID.
    stale.sort(key=lambda p: not p.name.endswith(".meta"))
    for path in stale:
        print(("stale " if args.check else "write ") + path.relative_to(ASSETS).as_posix())
        if not args.check:
            path.write_bytes(files[path].encode("utf-8"))
    print(f"{len(files)} files, {len(stale)} {'out of date' if args.check else 'written'}")
    return 1 if args.check and stale else 0


if __name__ == "__main__":
    raise SystemExit(main())

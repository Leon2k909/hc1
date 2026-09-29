"""Convert MP5 stock, grip, and laser meshes absent from the shared asset set.

Requires the extracted Garry's Mod Modern Wokefare Base (2459720887),
CrowbarCommandLineDecomp.exe, and SourceIO in D:/tmp/hc1-mw22-tools.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import part_names
from audit_mw19_mp5 import BASE, SMG, active_choices, attachment_source
from convert_mpapa5_smd import parse_triangles, write_obj_mesh


PROJECT = Path(__file__).resolve().parents[1]
ASSETS = PROJECT / "Assets"
TOOLS = Path(r"D:\tmp\hc1-mw22-tools")
CROWBAR = TOOLS / "CrowbarCommandLineDecomp.exe"
DECOMPILED = TOOLS / "decompiled/mpapa5_shared"
SOURCEIO = TOOLS.parent
DEST_MODELS = ASSETS / "attachments/mpapa5/shared"
DEST_MATERIALS = ASSETS / "attachments/mpapa5/materials/shared"
PREFABS = ASSETS / "attachments/mpapa5/prefabs"
RESOURCES = ASSETS / "gunsmith/mpapa5"
EXISTING_MATS = ASSETS / "attachments/mw2022/materials"
NAMESPACE = uuid.UUID("4288e939-b9e9-4b84-910f-696d49b15dc7")
MP5 = "weapons/mp5/mp5.equip"

ALIASES = {
    "attachment_vm_sm_mpapa5_laser01": "att_vm_laser01",
    "attachment_vm_sm_mpapa5_laser02": "att_vm_laser02",
    "attachment_vm_sm_mpapa5_laser03": "att_vm_laser03",
    "attachment_vm_sm_mpapa5_bipodgrip": "att_vm_bipodgrip",
    "attachment_vm_sm_mpapa5_angledgrip01": "att_vm_angledgrip01_smg",
    "attachment_vm_sm_mpapa5_angledgrip02": "att_vm_angledgrip02",
    "attachment_vm_sm_mpapa5_stubbygrip01": "att_vm_stubbygrip01",
    "attachment_vm_sm_mpapa5_stubbygrip02": "att_vm_stubbygrip02",
    "attachment_vm_sm_mpapa5_vertgrip01": "att_vm_vertgrip01",
    "attachment_vm_sm_mpapa5_vertgrip02": "att_vm_vertgrip02",
    "attachment_vm_sm_mpapa5_vertgrip03": "att_vm_vertgrip03",
}


def guid(key: str) -> str:
    return str(uuid.uuid5(NAMESPACE, key))


def choices() -> list[tuple[str, str, str]]:
    rows = {row[0]: row[1:] for row in active_choices()}
    result = [(key, key, "Stock") for key in rows["attachment_vm_sm_mpapa5_stock"]
              if key.startswith("att_vm_")]
    result += [(key, ALIASES[key], "Laser") for key in rows["att_laser"]]
    result += [(key, ALIASES[key], "Underbarrel") for key in rows["att_grip"]]
    return result


def source_model(key: str) -> tuple[str, Path]:
    _, name, model = attachment_source(key)
    if not model:
        raise RuntimeError(f"Missing Workshop model definition: {key}")
    for root in (SMG, BASE):
        path = root / model
        if path.is_file():
            return name or key.replace("att_vm_", "").replace("_", " ").title(), path
    raise FileNotFoundError(model)


def decompile(key: str, source: Path) -> list[Path]:
    output = DECOMPILED / key
    if not output.is_dir() or not list(output.glob("*.smd")):
        output.mkdir(parents=True, exist_ok=True)
        completed = subprocess.run([str(CROWBAR), "-p", str(source), "-o", str(output)],
                                   capture_output=True, text=True, check=False)
        if completed.returncode:
            raise RuntimeError(f"Crowbar failed on {source}: {completed.stdout[-1500:]} {completed.stderr[-500:]}")
    meshes = [p for p in output.glob("*.smd") if p.name != "reference.smd"]
    if not meshes:
        raise RuntimeError(f"Crowbar did not extract a render SMD for {source}")
    return meshes


def material_index() -> dict[str, Path]:
    result = {p.stem.lower(): p for p in EXISTING_MATS.rglob("*.vmat")}
    result.update({p.stem.lower(): p for p in DEST_MATERIALS.rglob("*.vmat")})
    return result


def vmt_path(material: str) -> Path | None:
    for root in (BASE, SMG):
        paths = list((root / "materials").rglob(material + ".vmt"))
        if paths:
            return paths[0]
    return None


def inspect() -> None:
    existing = material_index()
    for original, base_key, category in choices():
        name, source = source_model(base_key)
        meshes = decompile(original, source)
        materials = sorted({mat for mesh in meshes for mat, _ in parse_triangles(mesh)})
        missing = [mat for mat in materials if mat.lower() not in existing]
        print(f"{category:11s} {original:49s} {name:30s} meshes={len(meshes)} missing={missing}")


def save_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")


def convert_texture(reference: str, destination: Path) -> bool:
    source_name = reference.replace("\\", "/").lstrip("/") + ".vtf"
    source = next((root / "materials" / source_name for root in (BASE, SMG)
                   if (root / "materials" / source_name).is_file()), None)
    if source is None:
        return False
    if destination.is_file():
        return True
    sys.path.insert(0, str(TOOLS))
    from SourceIO.library.utils.pylib.vtf import load_vtf_texture
    from PIL import Image

    pixels, width, height, floating = load_vtf_texture(source.read_bytes())
    if floating:
        raise RuntimeError(f"Unexpected HDR texture: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    Image.frombytes("RGBA", (width, height), pixels).save(destination)
    return True


def ensure_material(material: str, available: dict[str, Path]) -> Path:
    existing = available.get(material.lower())
    if existing:
        return existing
    source = vmt_path(material)
    if source is None:
        raise FileNotFoundError(f"Missing VMT for {material}")
    vmt = source.read_text(encoding="utf-8-sig", errors="replace")
    color = re.search(r'"?\$basetexture"?\s+"([^\"]+)"', vmt, re.IGNORECASE)
    normal = re.search(r'"?\$bumpmap"?\s+"([^\"]+)"', vmt, re.IGNORECASE)
    if color is None:
        raise RuntimeError(f"Missing $basetexture in {source}")
    color_path = DEST_MATERIALS / f"{material}_color.png"
    normal_path = DEST_MATERIALS / f"{material}_normal.png"
    if not convert_texture(color.group(1), color_path):
        raise FileNotFoundError(color.group(1))
    has_normal = normal is not None and convert_texture(normal.group(1), normal_path)
    relative = lambda path: path.relative_to(ASSETS).as_posix()
    vmat = DEST_MATERIALS / f"{material}.vmat"
    contents = [
        '"Layer0"', '{',
        '    shader "shaders/complex.shader"',
        '    F_SPECULAR "1"',
        '    F_METALNESS_TEXTURE "0"',
        '    g_flMetalness "0.32"',
        '    g_flRoughnessScaleFactor "1.0"',
        f'    TextureColor "{relative(color_path)}"',
    ]
    if has_normal:
        contents.append(f'    TextureNormal "{relative(normal_path)}"')
    contents.extend([
        '    TextureRoughness "[0.42 0.42 0.42 1.0]"',
        '    TextureAmbientOcclusion "materials/default/default_ao.tga"',
        '}',
    ])
    vmat.parent.mkdir(parents=True, exist_ok=True)
    vmat.write_text("\n".join(contents) + "\n", encoding="utf-8", newline="\n")
    available[material.lower()] = vmat
    return vmat


def modeldoc(key: str, meshes: list[Path], available: dict[str, Path]) -> str:
    materials = sorted({mat for mesh in meshes for mat, _ in parse_triangles(mesh)})
    remaps = ", ".join(
        f'{{ from = "{mat}.vmat" to = "{ensure_material(mat, available).relative_to(ASSETS).as_posix()}" }}'
        for mat in materials
    )
    mesh_rows = ", ".join(
        f'{{ _class = "RenderMeshFile" name = "mesh_{i:02d}" filename = '
        f'"{(DEST_MODELS / key / (mesh.stem + ".obj")).relative_to(ASSETS).as_posix()}" '
        'import_translation = [0,0,0] import_rotation = [0,0,0] import_scale = 1 '
        'align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" }'
        for i, mesh in enumerate(meshes)
    )
    return (
        '<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} '
        'format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->\n'
        '{ rootNode = { _class = "RootNode" children = [\n'
        f'{{ _class = "MaterialGroupList" children = [ {{ _class = "DefaultMaterialGroup" remaps = [ {remaps} ] use_global_default = false }} ] }},\n'
        f'{{ _class = "RenderMeshList" children = [ {mesh_rows} ] }}\n'
        '] } }\n'
    )


def convert_choice(original: str, base_key: str, category: str, available: dict[str, Path]) -> None:
    name, source = source_model(base_key)
    # Our name (part_names.py), never the workshop's CoD one.
    name = part_names.name(original, name)
    meshes = decompile(original, source)
    output = DEST_MODELS / original
    output.mkdir(parents=True, exist_ok=True)
    for mesh in meshes:
        copy = output / mesh.name
        shutil.copy2(mesh, copy)
        write_obj_mesh(copy.with_suffix(".obj"), parse_triangles(copy))
    vmdl = output / (original + ".vmdl")
    vmdl.write_text(modeldoc(original, meshes, available), encoding="utf-8", newline="\n")

    if category == "Stock":
        position, scale, hidden, folder = "0,0,7.5", 1.3, "stock", "stocks"
    elif category == "Laser":
        position, scale, hidden, folder = "6,2.35,8.6", 1.0, "", "lasers"
    else:
        position, scale, hidden, folder = "7.5,0,6.8", 1.0, "", "underbarrel"
    mount = {
        "__type": "Facepunch.Gunsmith.GunsmithBoneAttachment",
        "__guid": guid(original + ":mount"),
        "__enabled": True,
        "BoneName": "weapon_root",
        "UseWeaponOrigin": True,
        "WeaponSpaceOffset": position,
        "WeaponSpaceScale": scale,
        "MountAtBone": False,
        "BoneOffset": "0,0,0",
        "BoneAngles": "0,0,0",
        "ModelScaleMultiplier": "1,1,1",
    }
    if hidden:
        mount["HiddenBone"] = hidden
    prefab = PREFABS / (original + ".prefab")
    part = RESOURCES / folder / (original + ".gnsmth")
    save_json(prefab, {
        "RootObject": {
            "__guid": guid(original + ":object"),
            "Flags": 0,
            "Name": "MP5 " + name,
            "Position": "0,0,0",
            "Rotation": "0,0,0,1",
            "Scale": "1,1,1",
            "Enabled": True,
            "NetworkMode": 1,
            "Components": [
                {"__type": "Sandbox.ModelRenderer", "__guid": guid(original + ":mesh"),
                 "__enabled": True, "Model": f"attachments/mpapa5/shared/{original}/{original}.vmdl",
                 "Tint": "1,1,1,1"},
                mount,
            ],
            "Children": [],
        },
        "ResourceVersion": 2,
        "__version": 2,
    })
    save_json(part, {
        "Name": name,
        "Category": category,
        "MainPrefab": {"_type": "gameobject", "prefab": f"attachments/mpapa5/prefabs/{original}.prefab"},
        "EligibleEquipment": [MP5],
        "RequiredLevel": 0,
        "Description": "",
        "__references": [],
        "__version": 0,
    })
    print(f"imported {category}: {name}")


def main() -> None:
    available = material_index()
    for original, base_key, category in choices():
        convert_choice(original, base_key, category, available)


if __name__ == "__main__":
    main()

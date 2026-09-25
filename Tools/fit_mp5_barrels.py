"""Fit the Workshop (MW2019) MP5 barrels and handguards to the existing S&box MP5.

The Workshop parts only replace the front of the gun. The MP5 keeps its own
receiver, rear sight, bolt and cocking lever, cut from the stock v_mp5 mesh.
Each piece follows the same v_mp5 bone as the stock gun, so the ejection port,
reloads and iron sights still work. Every part uses the same Workshop-to-MP5
transform, fitted so the rail grip spans the stock handguard.

- FSS Light Handguard (rail grip) replaces only the polymer handguard. It
  hides v_mp5_b and shows `native_front` (v_mp5_b without the handguard) and
  `native_bolt`.
- Integral and Monolithic Suppressor Barrels use the same native pieces. The
  stock barrel sits inside the can and the stock front sight on top of it. The
  Workshop front sights sit in the same place but are taller, which would throw
  the iron sights off, so they are left out.
- Short Barrel is an MP5K-style shroud without a barrel of its own. It hides
  v_mp5_a and v_mp5_b and shows `native_receiver`. That piece has the stock
  receiver with the cocking tube cut at the shroud's sight notch, the stock
  front sight moved back into that notch, and the stock muzzle moved back to
  stick out of the shroud. It also shows `native_lever`, `native_latch` and
  `native_bolt`.

Muzzle devices sit against the front face of the barrel part.
GunsmithBoneAttachment.RefreshMount holds those shifts, which this script prints.

Input is a Source2Viewer GLB export of the local v_mp5.vmdl_c. Positions are
glTF (Y, Z, X) in metres, and JOINTS_0 holds the v_mp5 bone index with a single
weight. Primitive 0 is v_mp5_a, 1 is v_mp5_c and 2 is v_mp5_b.
"""

from __future__ import annotations

import argparse
import json
import struct
import uuid
from pathlib import Path

import numpy as np


ASSETS = Path(__file__).resolve().parents[1] / "Assets"
MPAPA5 = ASSETS / "attachments/mpapa5"
NATIVE = MPAPA5 / "native_receiver"
PREFABS = MPAPA5 / "prefabs"
PARTS = ASSETS / "gunsmith/mpapa5"
NAMESPACE = uuid.UUID("9d74dfa8-0933-4e67-9b8d-67fae3c9aa4c")
INCHES_PER_METER = 39.37007874

V_MP5_A = "models/weapons/sbox_smg_mp5/v_mp5_a.vmat"
V_MP5_B = "models/weapons/sbox_smg_mp5/v_mp5_b.vmat"
PRIMITIVE_A, PRIMITIVE_B = 0, 2
BONES = {"weapon_root": 0, "forearm": 2, "cocking_lever": 3, "bolt": 4, "reload_latch": 7}

# Native MP5 layout (model space, inches).
BORE_Z = 8.128
HANDGUARD_REAR = 4.1
FRONT_SIGHT = 10.86
# Handguard mount at the front of the handguard, clamped around the cocking
# tube. Only the collar above the handguard stays.
HANDGUARD_MOUNT_X = 10.1
TUBE_COLLAR_MIN_Z = 8.95
# Barrel triangles all lie within this radius of the bore; the front sight housing reaches past it.
BARREL_RADIUS = 0.46
# The barrel's shoulder at the back of the front sight, and the front of the sight's barrel ring.
BARREL_FLANGE = 10.8
SIGHT_RING_FRONT = 11.58
# Muzzle devices start this far behind the stock muzzle, just past the barrel lugs.
NATIVE_DEVICE_REAR = 12.0
# Stock pieces behind this x belong with the receiver (rear sight, spring rod, barrel trunnion).
RECEIVER_FRONT = 5.0

MODELDOC = '''<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
{{ rootNode = {{ _class = "RootNode" children = [
  {{ _class = "MaterialGroupList" children = [ {{ _class = "DefaultMaterialGroup" remaps = [
    {remaps}
  ] use_global_default = false }} ] }},
  {{ _class = "RenderMeshList" children = [
    {meshes}
  ] }}
] }} }}
'''
MESH = ('{{ _class = "RenderMeshFile" name = "{name}" filename = "{filename}" import_translation = [0,0,0] '
        'import_rotation = [0,0,0] import_scale = 1 align_origin_x_type = "None" align_origin_y_type = "None" '
        'align_origin_z_type = "None" }}')


# ---- Stock MP5 mesh ----------------------------------------------------------

def read_glb(path: Path):
    raw = path.read_bytes()
    if raw[:4] != b"glTF":
        raise ValueError(f"Not a GLB: {path}")
    json_size, _ = struct.unpack_from("<II", raw, 12)
    document = json.loads(raw[20:20 + json_size])
    binary_start = 20 + json_size
    binary_size, _ = struct.unpack_from("<II", raw, binary_start)
    return document, raw[binary_start + 8:binary_start + 8 + binary_size]


def accessor(document, binary, index) -> np.ndarray:
    item = document["accessors"][index]
    view = document["bufferViews"][item["bufferView"]]
    dtype = np.dtype({5121: "<u1", 5123: "<u2", 5125: "<u4", 5126: "<f4"}[item["componentType"]])
    width = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[item["type"]]
    stride = view.get("byteStride", dtype.itemsize * width)
    start = view.get("byteOffset", 0) + item.get("byteOffset", 0)
    rows = np.lib.stride_tricks.as_strided(
        np.frombuffer(binary, dtype=np.uint8, offset=start),
        shape=(item["count"], dtype.itemsize * width), strides=(stride, 1))
    return np.frombuffer(rows.tobytes(), dtype=dtype).reshape(item["count"], width)


class Primitive:
    """One v_mp5 material: triangles as (n, 3, 8) rows of position, normal, uv in model space."""

    def __init__(self, document, binary, index: int):
        primitive = document["meshes"][0]["primitives"][index]
        attributes = primitive["attributes"]
        # glTF (Y, Z, X) to model (X, Y, Z).
        position = accessor(document, binary, attributes["POSITION"]).astype(np.float64)[:, [2, 0, 1]] * INCHES_PER_METER
        normal = accessor(document, binary, attributes["NORMAL"]).astype(np.float64)[:, [2, 0, 1]]
        uv = accessor(document, binary, attributes["TEXCOORD_0"]).astype(np.float64)
        bones = accessor(document, binary, attributes["JOINTS_0"])[:, 0]
        indices = accessor(document, binary, primitive["indices"]).reshape(-1, 3).astype(np.int64)
        self.vertices = np.hstack([position, normal, uv])
        self.indices = indices
        self.bones = bones[indices[:, 0]]

    def bone(self, name: str) -> np.ndarray:
        return self.indices[self.bones == BONES[name]]

    def triangles(self, indices: np.ndarray) -> np.ndarray:
        return self.vertices[indices]


def components(vertices: np.ndarray, indices: np.ndarray) -> np.ndarray:
    """Connected-component id per triangle, welding split vertices by position."""
    _, welded = np.unique(np.round(vertices[:, :3], 3), axis=0, return_inverse=True)
    welded = welded.ravel()
    parent = np.arange(welded.max() + 1)

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b, c in welded[indices]:
        for u, v in ((a, b), (b, c)):
            ru, rv = find(u), find(v)
            if ru != rv:
                parent[ru] = rv
    return np.array([find(welded[t[0]]) for t in indices])


def clip(triangles: np.ndarray, low: float = -np.inf, high: float = np.inf) -> np.ndarray:
    """Clip triangles to low <= x <= high, interpolating normals and uvs."""
    def plane(polygon, bound, sign):
        output = []
        for previous, current in zip(polygon[-1:] + polygon[:-1], polygon):
            previous_in = sign * (previous[0] - bound) >= 0
            current_in = sign * (current[0] - bound) >= 0
            if previous_in != current_in:
                amount = (bound - previous[0]) / (current[0] - previous[0])
                output.append(previous + (current - previous) * amount)
            if current_in:
                output.append(current)
        return output

    result = []
    for triangle in triangles:
        if triangle[:, 0].min() >= low and triangle[:, 0].max() <= high:
            result.append(triangle)
            continue
        polygon = list(triangle)
        if low > -np.inf:
            polygon = plane(polygon, low, 1)
        if high < np.inf and polygon:
            polygon = plane(polygon, high, -1)
        for n in range(1, len(polygon) - 1):
            result.append(np.array([polygon[0], polygon[n], polygon[n + 1]]))
    if not result:
        return np.zeros((0, 3, 8))
    result = np.array(result)
    result[:, :, 3:6] /= np.linalg.norm(result[:, :, 3:6], axis=2, keepdims=True)
    return result


def moved(triangles: np.ndarray, dx: float) -> np.ndarray:
    triangles = triangles.copy()
    triangles[:, :, 0] += dx
    return triangles


# ---- Output ------------------------------------------------------------------

def write_obj(path: Path, groups: dict[str, np.ndarray]):
    """Model-space triangles to an OBJ. S&box's importer maps OBJ (X, Y, Z) to model (Y, Z, X)."""
    lines = [f"mtllib {path.stem}.mtl", f"o {path.stem}"]
    faces = []
    count = 0
    for material, triangles in groups.items():
        faces.append(f"usemtl {material}")
        for triangle in triangles:
            for p in triangle:
                lines.append(f"v {p[1]:.9g} {p[2]:.9g} {p[0]:.9g}")
                lines.append(f"vt {p[6]:.9g} {p[7]:.9g}")
                lines.append(f"vn {p[4]:.9g} {p[5]:.9g} {p[3]:.9g}")
            first = count + 1
            count += 3
            faces.append("f " + " ".join(f"{i}/{i}/{i}" for i in range(first, first + 3)))
    path.write_text("\n".join(lines + faces) + "\n", encoding="utf-8")
    path.with_suffix(".mtl").write_text(
        "".join(f"newmtl {material}\nKa 1 1 1\nKd 1 1 1\nd 1\n" for material in groups), encoding="utf-8")


def write_vmdl(path: Path, remaps: dict[str, str], meshes: list[tuple[str, Path]]):
    remap_text = ",\n    ".join(f'{{ from = "{source}.vmat" to = "{target}" }}' for source, target in remaps.items())
    mesh_text = ",\n    ".join(MESH.format(name=name, filename=asset_path(obj)) for name, obj in meshes)
    path.write_text(MODELDOC.format(remaps=remap_text, meshes=mesh_text), encoding="utf-8")


def asset_path(path: Path) -> str:
    return path.relative_to(ASSETS).as_posix()


def write_native(name: str, groups: dict[str, np.ndarray]):
    obj = NATIVE / f"{name}.obj"
    write_obj(obj, groups)
    targets = {"v_mp5_a": V_MP5_A, "v_mp5_b": V_MP5_B}
    write_vmdl(NATIVE / f"{name}.vmdl", {m: targets[m] for m in groups}, [(name, obj)])
    print(f"{name}: {sum(len(t) for t in groups.values())} triangles")


# ---- Workshop parts ------------------------------------------------------------

def read_obj(path: Path):
    """Crowbar OBJ faces grouped by material, as (n, 3, 8) model-space rows."""
    positions, uvs, normals, groups = [], [], [], {}
    material = None
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "v":
            x, y, z = (float(v) for v in parts[1:4])
            positions.append((z, x, y))
        elif parts[0] == "vt":
            uvs.append(tuple(float(v) for v in parts[1:3]))
        elif parts[0] == "vn":
            x, y, z = (float(v) for v in parts[1:4])
            normals.append((z, x, y))
        elif parts[0] == "usemtl":
            material = parts[1]
        elif parts[0] == "f":
            corners = [[int(i) - 1 for i in corner.split("/")] for corner in parts[1:]]
            rows = [positions[p] + normals[n] + uvs[t] for p, t, n in corners]
            for k in range(1, len(rows) - 1):
                groups.setdefault(material, []).append([rows[0], rows[k], rows[k + 1]])
    return {material: np.array(triangles) for material, triangles in groups.items()}


def workshop_transform():
    """Offset and scale that fit the rail grip over the stock handguard, on the stock bore."""
    groups = read_obj(MPAPA5 / "underbarrel/rail_grip/rail_grip.obj")
    rail = groups["weapon_vm_sm_mpapa5_railgrip"]
    # The Workshop "upper" is the MW19 barrel; its bore is the Workshop origin line.
    upper = groups["weapon_vm_sm_mpapa5_upper"].reshape(-1, 8)
    mw_y = (upper[:, 1].min() + upper[:, 1].max()) / 2
    mw_z = (upper[:, 2].min() + upper[:, 2].max()) / 2
    scale = (FRONT_SIGHT - HANDGUARD_REAR) / (rail[:, :, 0].max() - rail[:, :, 0].min())
    offset = np.array([HANDGUARD_REAR - rail[:, :, 0].min() * scale, -mw_y * scale, BORE_Z - mw_z * scale])
    return offset, scale, rail


def workshop_front(files: list[Path], offset, scale) -> float:
    points = np.vstack([t.reshape(-1, 8)[:, :3] for f in files for t in read_obj(f).values()])
    return float(points[:, 0].max() * scale + offset[0])


# ---- Pieces --------------------------------------------------------------------

def native_pieces(a: Primitive, b: Primitive, short_sight_x: float, short_front: float):
    root_b = b.bone("weapon_root")
    component = components(b.vertices, root_b)
    ids = np.unique(component)
    box = {c: b.vertices[root_b[component == c]].reshape(-1, 8)[:, :3] for c in ids}
    mount = [c for c in ids if box[c][:, 0].min() >= HANDGUARD_MOUNT_X and box[c][:, 0].max() < FRONT_SIGHT]
    rear = [c for c in ids if box[c][:, 0].max() < RECEIVER_FRONT]
    barrel_id = max(ids, key=lambda c: box[c][:, 0].max())  # barrel, front sight and muzzle
    sight_parts = [c for c in ids if box[c][:, 0].min() > FRONT_SIGHT and c != barrel_id]

    # FSS and the integral cans: everything but the handguard mount, which keeps its tube collar.
    front = b.triangles(root_b[~np.isin(component, mount)])
    mount_tris = b.triangles(root_b[np.isin(component, mount)])
    collar = mount_tris[mount_tris[:, :, 2].min(axis=1) >= TUBE_COLLAR_MIN_Z]
    write_native("native_front", {"v_mp5_b": np.concatenate([front, collar])})
    write_native("native_bolt", {"v_mp5_b": b.triangles(b.bone("bolt"))})

    # Short barrel: the front sight moves back into the shroud's notch, and the
    # muzzle (barrel lugs onwards) moves back to stick out of the shroud as far
    # as a muzzle device covers it. A plain barrel section joins the two.
    barrel_tris = b.triangles(root_b[component == barrel_id])
    radius = np.hypot(barrel_tris[:, :, 1], barrel_tris[:, :, 2] - BORE_Z).max(axis=1)
    housing = barrel_tris[(radius >= BARREL_RADIUS) & (barrel_tris[:, :, 0].min(axis=1) > FRONT_SIGHT - 0.1)]
    barrel = barrel_tris[radius < BARREL_RADIUS]
    sight = np.concatenate([housing] + [b.triangles(root_b[component == c]) for c in sight_parts])
    sight_shift = short_sight_x - housing[:, :, 0].min()
    muzzle_shift = short_front - NATIVE_DEVICE_REAR
    muzzle = moved(clip(barrel, low=SIGHT_RING_FRONT), muzzle_shift)
    # Plain barrel from inside the moved sight's ring up to the muzzle section.
    plain_shift = SIGHT_RING_FRONT + muzzle_shift - BARREL_FLANGE
    plain = moved(clip(barrel, low=short_sight_x - 0.1 - plain_shift, high=BARREL_FLANGE), plain_shift)
    cut = short_sight_x + 0.02  # the stock tube reaches just inside the sight housing
    write_native("native_receiver", {
        "v_mp5_a": clip(a.triangles(a.bone("weapon_root")), high=cut),
        "v_mp5_b": np.concatenate([
            b.triangles(root_b[np.isin(component, rear)]),
            moved(sight, sight_shift),
            muzzle,
            plain,
        ]),
    })
    write_native("native_lever", {"v_mp5_a": clip(a.triangles(a.bone("cocking_lever")), high=cut)})
    write_native("native_latch", {"v_mp5_a": a.triangles(a.bone("reload_latch"))})
    print(f"short barrel: front sight moved {sight_shift:+.3f}, muzzle moved {muzzle_shift:+.3f}")


# ---- Parts ---------------------------------------------------------------------

FRONT_PIECES = (
    ("Existing MP5 barrel and sights", "native_front", "weapon_root"),
    ("Existing MP5 bolt", "native_bolt", "bolt"),
)
SHORT_PIECES = (
    ("Existing MP5 receiver and sights", "native_receiver", "weapon_root"),
    ("Existing MP5 bolt", "native_bolt", "bolt"),
    ("Existing MP5 cocking lever", "native_lever", "cocking_lever"),
    ("Existing MP5 magazine latch", "native_latch", "reload_latch"),
)
# (part resource, prefab, model, [(mesh name, Workshop OBJ)], hidden v_mp5 materials, native pieces)
BARRELS = (
    ("underbarrel/rail_grip.gnsmth", "rail_grip.prefab", "underbarrel/rail_grip/rail_grip.vmdl",
     [("handguard", "underbarrel/rail_grip/rail_grip_handguard.obj")], [V_MP5_B], FRONT_PIECES),
    # The hand stop is the Workshop default (tag_grip_hide choice 0).
    ("barrels/barrel_short.gnsmth", "barrel_short.prefab", "barrels/barrel_short/barrel_short.vmdl",
     [("handguard", "barrels/barrel_short/barrel_short.obj"),
      ("hand_stop", "barrels/barrel_short/barrel_short_grip_show.obj")], [V_MP5_A, V_MP5_B], SHORT_PIECES),
    # The smooth underside is the Workshop default (tag_grip_hide choice 0).
    ("barrels/barrel_integral_suppressor.gnsmth", "barrel_integral_suppressor.prefab",
     "barrels/barrel_integral_suppressor/barrel_integral_suppressor.vmdl",
     [("barrel", "barrels/barrel_integral_suppressor/barrel_integral_suppressor.obj"),
      ("underside", "barrels/barrel_integral_suppressor/barrel_integral_suppressor_grip_hide.obj")],
     [V_MP5_B], FRONT_PIECES),
    ("barrels/barrel_monolithic_suppressor.gnsmth", "barrel_monolithic_suppressor.prefab",
     "barrels/barrel_monolithic_suppressor/barrel_monolithic_suppressor.vmdl",
     [("barrel", "barrels/barrel_monolithic_suppressor/barrel_monolithic_suppressor.obj")],
     [V_MP5_B], FRONT_PIECES),
)
SHORT_SIGHT = "barrels/barrel_short/barrel_short_sight_on.obj"


def identifier(key: str) -> str:
    return str(uuid.uuid5(NAMESPACE, key))


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")


def update_part(resource: str, prefab: str, hidden: list[str], pieces, offset, scale):
    part_path = PARTS / resource
    part = json.loads(part_path.read_text(encoding="utf-8"))
    part["HiddenWeaponMaterials"] = hidden
    write_json(part_path, part)

    prefab_path = PREFABS / prefab
    data = json.loads(prefab_path.read_text(encoding="utf-8"))
    root = data["RootObject"]
    for component in root["Components"]:
        if component["__type"] == "Facepunch.Gunsmith.GunsmithSocketAttachment":
            component["WeaponSpaceOffset"] = ",".join(f"{v:.3f}" for v in offset)
            component["WeaponSpaceScale"] = round(float(scale), 3)
    children = [c for c in root.get("Children", []) if not c.get("Name", "").startswith("Existing MP5")]
    for name, model, bone in pieces:
        key = f"{prefab}:{model}"
        children.append({
            "__guid": identifier(key),
            "Flags": 0,
            "Name": name,
            "Position": "0,0,0",
            "Rotation": "0,0,0,1",
            "Scale": "1,1,1",
            "Enabled": True,
            "NetworkMode": 1,
            "Components": [
                {
                    "__type": "Sandbox.ModelRenderer",
                    "__guid": identifier(key + ":model"),
                    "__enabled": True,
                    "Model": asset_path(NATIVE / f"{model}.vmdl"),
                    "Tint": "1,1,1,1",
                },
                {
                    "__type": "Facepunch.Gunsmith.GunsmithMp5NativeReceiver",
                    "__guid": identifier(key + ":mount"),
                    "__enabled": True,
                    "BoneName": bone,
                },
            ],
            "Children": [],
        })
    root["Children"] = children
    write_json(prefab_path, data)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("glb", type=Path, help="Source2Viewer export of the local v_mp5.vmdl_c")
    options = parser.parse_args()

    offset, scale, rail = workshop_transform()
    write_obj(MPAPA5 / "underbarrel/rail_grip/rail_grip_handguard.obj", {"weapon_vm_sm_mpapa5_railgrip": rail})
    print(f"Workshop parts: WeaponSpaceOffset {offset.round(3).tolist()} WeaponSpaceScale {scale:.3f}")

    fronts = {}
    for resource, prefab, model, meshes, hidden, pieces in BARRELS:
        files = [MPAPA5 / obj for _, obj in meshes]
        materials = sorted({m for f in files for m in read_obj(f)})
        write_vmdl(MPAPA5 / model, {m: f"attachments/mpapa5/materials/{m}.vmat" for m in materials},
                   [(name, f) for (name, _), f in zip(meshes, files)])
        update_part(resource, prefab, hidden, pieces, offset, scale)
        fronts[resource] = workshop_front(files, offset, scale)

    short_sight = read_obj(MPAPA5 / SHORT_SIGHT)
    short_sight_x = min(t[:, :, 0].min() for t in short_sight.values()) * scale + offset[0]
    document, binary = read_glb(options.glb)
    native_pieces(Primitive(document, binary, PRIMITIVE_A), Primitive(document, binary, PRIMITIVE_B),
                  short_sight_x, fronts["barrels/barrel_short.gnsmth"])

    print("Muzzle device shifts for GunsmithBoneAttachment.RefreshMount:")
    for resource, front in fronts.items():
        if resource.startswith("barrels/"):
            print(f"  {Path(resource).stem}: front {front:.3f}, shift {front - NATIVE_DEVICE_REAR:+.2f}")


if __name__ == "__main__":
    main()

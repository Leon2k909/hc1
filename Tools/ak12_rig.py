"""Put Escape from Tarkov's AK-12 (ARC9 EFT Assault Rifles, Workshop 2962829818, decompiled to decompiled/ak12) onto the
AK-105's CoD rig, as SMDs the Kastov pipeline reads like the AK-105's own receiver (decompiled/ak12/rig), and draw its
HUD icon from the model's side.

The gun is assembled as ARC9 draws it in the idle pose, in the c_ak12 "weapon" bone's frame: the c_ak12 bodygroup meshes
posed by the ak_anims idle, and the separate attachment models (magazine, pistol grip, stock tube, stock, rear sight)
placed by ARC9's GetAttachmentPos and BuildSubAttachmentTree.

Each SMD carries the AK-105 receiver's whole node list. Its frame 0 puts every bone where the AK-105's idle clip has it
relative to tag_sling (bones the idle doesn't move: the receiver's reference pose), so tag_sling is the identity and a
vertex written in tag_sling space lands at tag_sling's bind on whatever bone it's skinned to. Tarkov's moving parts go
on the rig bones the AK-105's clips move (BONES).

The icon (Assets/ui/weapons/guns/ak12_01.png) is the model's left side, muzzle to the left, as a white silhouette framed
like the other gun icons (kastov_prefabs.icon): the pack's own icon is a small three-quarter render.

Run (after the pack is decompiled, before port_kastov.py --weapon ak12): python Tools/ak12_rig.py
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from kastov_smd import Smd, write_smd
from kastov_weapons import ASSETS, DECOMPILED

SOURCE = DECOMPILED / "ak12"
AK105 = DECOMPILED / "akilo105"
RIG = SOURCE / "rig"
ICON = ASSETS / "ui" / "weapons" / "guns" / "ak12_01.png"


# --- Source angle maths ------------------------------------------------------------------------------------------

def angle_matrix(p: float, y: float, r: float) -> np.ndarray:
    """Source AngleMatrix: columns forward, left, up."""
    sp, cp = math.sin(math.radians(p)), math.cos(math.radians(p))
    sy, cy = math.sin(math.radians(y)), math.cos(math.radians(y))
    sr, cr = math.sin(math.radians(r)), math.cos(math.radians(r))
    forward = np.array([cp * cy, cp * sy, -sp])
    left = np.array([sr * sp * cy - cr * sy, sr * sp * sy + cr * cy, sr * cp])
    up = np.array([cr * sp * cy + sr * sy, cr * sp * sy - sr * cy, cr * cp])
    return np.stack([forward, left, up], 1)


def axis_rotation(axis: np.ndarray, degrees: float) -> np.ndarray:
    a = axis / np.linalg.norm(axis)
    t = math.radians(degrees)
    k = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + math.sin(t) * k + (1 - math.cos(t)) * (k @ k)


def attachment_pose(bone: np.ndarray, pos, ang, model_offset=(0, 0, 0), model_angle=(0, 0, 0)) -> np.ndarray:
    """ARC9 SWEP:GetAttachmentPos for a slot on a bone (4x4 bone matrix: columns x forward, y left, z up)."""
    rot = bone[:3, :3]
    apos = bone[:3, 3] + rot @ np.array([pos[0], -pos[1], pos[2]])
    p, y, r = (ang[i] + model_angle[i] for i in range(3))
    forward, right, up = rot[:, 0], -rot[:, 1], rot[:, 2]
    aang = axis_rotation(up, y) @ axis_rotation(right, p) @ axis_rotation(forward, r) @ rot
    mo = np.array(model_offset, float)
    apos = apos + aang[:, 0] * mo[0] - aang[:, 1] * mo[1] + aang[:, 2] * mo[2]
    out = np.eye(4)
    out[:3, :3], out[:3, 3] = aang, apos
    return out


def sub_slot(parent_pos, parent_ang, sub_pos, sub_ang):
    """ARC9 BuildSubAttachmentTree: a sub-slot's Pos/Ang on its parent slot's bone."""
    rot = angle_matrix(-parent_ang[0], -parent_ang[1], -parent_ang[2])
    forward, left, up = rot[:, 0], rot[:, 1], rot[:, 2]
    right = -left
    pos = np.array(parent_pos, float) + forward * -sub_pos[0] + right * -sub_pos[1] + up * -sub_pos[2]
    ang = tuple(parent_ang[i] + sub_ang[i] for i in range(3))
    return pos, ang


# --- the gun as ARC9 draws it ------------------------------------------------------------------------------------

# Piece -> list of (Tarkov bone, material, positions (3, 3), normals (3, 3), uvs (3, 2)), in the weapon bone's frame.
Pieces = dict[str, list[tuple[str, str, np.ndarray, np.ndarray, np.ndarray]]]


def assemble() -> Pieces:
    idle = Smd(SOURCE / "anims/ak_anims_anims/idle.smd")
    idle_world = idle.world(idle.dense_frames()[0])
    idle_named = {idle.name(i): idle_world[i] for i in range(len(idle.nodes))}
    to_weapon = np.linalg.inv(idle_named["weapon"])
    bones = {name: to_weapon @ m for name, m in idle_named.items()}
    # Bones the idle clip doesn't animate (the stock's hinge) stay where the model's reference pose has them.
    ref_smd = Smd(SOURCE / "body8_model0.smd")
    ref_world = ref_smd.world(ref_smd.dense_frames()[0])
    ref_weapon = np.linalg.inv(ref_world[ref_smd.index("weapon")])
    for i, (name, _) in enumerate(ref_smd.nodes):
        bones.setdefault(name, ref_weapon @ ref_world[i])

    pieces: Pieces = {}

    def add_mesh(piece: str, path: str, skip=()):
        smd = Smd(SOURCE / path)
        ref = smd.world(smd.dense_frames()[0])
        out = pieces.setdefault(piece, [])
        for material, verts in smd.triangles:
            main = [max(links, key=lambda link: link[1])[0] for *_, links in verts]
            bone = smd.name(main[0])
            if bone in skip:
                continue
            ps, ns, uvs = [], [], []
            for (position, normal, uv, _links), b in zip(verts, main):
                m = bones[smd.name(b)] @ np.linalg.inv(ref[b])
                ps.append((m @ np.append(position, 1.0))[:3])
                ns.append(m[:3, :3] @ normal)
                uvs.append(uv)
            out.append((bone, material, np.array(ps), np.array(ns), np.array(uvs)))

    for path in ("ak12.smd", "ak122.smd", "body8_model0.smd", "reciever_ak12_izhmash_ak12_std_LOD0_0.smd",
                 "gas_block_ak12_izhmash_ak12_std_LOD0_0.smd", "handguard_ak12_izhmash_ak12_std_LOD0_0.smd",
                 "sight_rear_all_izhmash_ak12_rear_sight_base_LOD0_0.smd",
                 "muzzle_ak12_izhmash_ak12_muzzle_brake_std_545x39_LOD0_0.smd"):
        add_mesh(Path(path).stem, path)
    add_mesh("rounds", "545.smd", skip=("patron_in_weapon", "shellport"))

    # The attachment models (each has one root bone at the origin), placed as ARC9 places them (the pack's AK-12
    # attachment slots and the AK-12 stock tube's sub-slot).
    mag = attachment_pose(bones["mod_magazine"], (0, 0, -0.2), (0, 0, 0))
    grip = attachment_pose(bones["mod_pistol_grip"], (0, 0, 0), (0, 0, 0))
    tube_pos, tube_ang = (0.06, -0.03, 0.12), (0, 0, 1)
    tube = attachment_pose(bones["weapon_stock_lock_16"], tube_pos, tube_ang, (0, 0, 0.05), (0, 0, -2.5))
    stock_pos, stock_ang = sub_slot(tube_pos, tube_ang, (0.67, -3.5, 0.75), (-3, -90, 0))
    stock = attachment_pose(bones["weapon_stock_lock_16"], stock_pos, stock_ang)
    rsb_pos, rsb_ang = sub_slot((0, 0, 0), (0, 0, 0), (0, -7.4, -0.5), (0, -90, 0))
    rs_pos, rs_ang = sub_slot(rsb_pos, rsb_ang, (-1.27, 0, 0.1), (0, 90, 0))
    rear_sight = attachment_pose(bones["mod_reciever"], rs_pos, rs_ang)
    # The stock's SMD is in studiomdl's pre-rotation space: its QC's $bbox is the SMD's extents turned +90 degrees about
    # z (x' = -y, y' = x). The other attachment models' $bboxes match their SMDs.
    stock = stock @ np.array([[0, -1, 0, 0], [1, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], float)
    for name, place, path in (("magazine", mag, "mag_ak_izhmash_ak12_std_545x39_30_LOD0_0_new.smd"),
                              ("pistol_grip", grip, "pistolgrip_ak_izhmash_ak12_std_LOD0_0_new.smd"),
                              ("stock_tube", tube, "stock_ak12_izhmash_ak12_stock_tube_std_LOD0_0.smd"),
                              ("stock", stock, "stock_ar15_izhmash_ak12_std_LOD0_0new.smd"),
                              ("rear_sight", rear_sight, "sight_rear_ak_izhmash_ak12_rear_sight_std_LOD0_0.smd")):
        smd = Smd(SOURCE / path)
        out = pieces.setdefault(name, [])
        for material, verts in smd.triangles:
            ps = np.array([(place @ np.append(v[0], 1.0))[:3] for v in verts])
            ns = np.array([place[:3, :3] @ v[1] for v in verts])
            uvs = np.array([v[2] for v in verts])
            out.append((name, material, ps, ns, uvs))
    return pieces


# --- onto the AK-105's rig -----------------------------------------------------------------------------------------

# Tarkov's weapon frame (forward -y, left +x, up +z) to the AK-105's tag_sling space, and where it goes there: the bore
# on the AK-105's bore, the receiver where the AK-105's sits on the clips' hands.
FIT = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]], float)
SHIFT = np.array([-8.15, 0.573, 1.03])

# Tarkov bone -> rig bone. Checked against what the AK-105's clips move: j_boltcarrier goes 5 back in fire and the empty
# reload, j_trigger turns 31 degrees in fire, j_magrelease 49 in the reload; j_bolt and j_magrel never move.
BONES = {
    "weapon_bolt": "j_boltcarrier",
    "weapon_selector": "j_fireselect",
    "weapon_trigger": "j_trigger",
    "weapon_release": "j_magrelease",
    "weapon_stock_lock_16": "tag_stock_attach",
    "stock": "tag_stock_attach",
    "stock_tube": "tag_stock_attach",
    "pistol_grip": "tag_pistolgrip_attach",
    "magazine": "j_mag1",
    "patron_in_mag0": "j_mag1",
    "patron_in_mag1": "j_mag1",
    "patron_in_mag2": "j_mag1",
}
DROP = {"weapon_izhmash_ak12_recoil_spring_LOD0"}  # inside the receiver under the dust cover, never seen

# SMD name -> its pieces.
SMDS = {
    "ak12_receiver": ("ak12", "ak122", "body8_model0", "reciever_ak12_izhmash_ak12_std_LOD0_0",
                      "gas_block_ak12_izhmash_ak12_std_LOD0_0", "handguard_ak12_izhmash_ak12_std_LOD0_0", "stock_tube",
                      "stock"),
    "ak12_brake": ("muzzle_ak12_izhmash_ak12_muzzle_brake_std_545x39_LOD0_0",),
    "ak12_rear_sight": ("sight_rear_all_izhmash_ak12_rear_sight_base_LOD0_0", "rear_sight"),
    "ak12_pgrip": ("pistol_grip",),
}


def rig(pieces: Pieces) -> dict[str, list]:
    """The SMDs' skeleton and triangles (tag_sling space). Returns each SMD's triangles."""
    rec = Smd(AK105 / "att_vm_p04_ar_akilo105_rec_v0_LOD0_edited.smd")
    idle = Smd(AK105 / "vm_iw9_akilo105_anims/idle.smd")
    idle_world = idle.world(idle.dense_frames()[0])
    idle_named = {idle.name(i): idle_world[i] for i in range(len(idle.nodes))}
    ts_inv = np.linalg.inv(idle_named["tag_sling"])
    rec_world = rec.world(rec.dense_frames()[0])
    rec_ts_inv = np.linalg.inv(rec_world[rec.index("tag_sling")])
    world = [ts_inv @ idle_named[name] if name in idle_named else rec_ts_inv @ rec_world[i]
             for i, (name, _) in enumerate(rec.nodes)]
    for m in world:  # unit axes: the clips' matrices carry rounding
        u, _, vt = np.linalg.svd(m[:3, :3])
        m[:3, :3] = u @ vt
    locals_ = [np.linalg.inv(world[parent]) @ world[i] if parent >= 0 else world[i]
               for i, (_, parent) in enumerate(rec.nodes)]
    index = {name: i for i, (name, _) in enumerate(rec.nodes)}

    def triangles(piece: str, extra: np.ndarray | None = None, bone_override: str | None = None):
        result = []
        for bone, material, pos, nrm, uv in pieces[piece]:
            if material in DROP:
                continue
            b = index[bone_override or BONES.get(bone, "tag_sling")]
            verts = []
            for k in range(3):
                p, n = FIT @ pos[k] + SHIFT, FIT @ nrm[k]
                if extra is not None:
                    p, n = (extra @ np.append(p, 1.0))[:3], extra[:3, :3] @ n
                length = np.linalg.norm(n)
                verts.append((p, n / length if length > 0 else np.array([0.0, 0.0, 1.0]),
                              (float(uv[k, 0]), float(uv[k, 1])), [(b, 1.0)]))
            result.append((material, verts))
        return result

    out = {name: [tri for piece in names for tri in triangles(piece)] for name, names in SMDS.items()}
    # The magazine and its top rounds on j_mag1, and the same again on j_mag2 (the reload's fresh one), placed as the
    # idle has j_mag2 from j_mag1.
    spare = world[index["j_mag2"]] @ np.linalg.inv(world[index["j_mag1"]])
    out["ak12_mag"] = (triangles("magazine") + triangles("rounds") + triangles("magazine", spare, "j_mag2")
                       + triangles("rounds", spare, "j_mag2"))
    RIG.mkdir(parents=True, exist_ok=True)
    for name, tris in out.items():
        write_smd(RIG / f"{name}.smd", rec.nodes, [locals_], tris)
        p = np.array([v[0] for _, vs in tris for v in vs])
        print(f"{name:18s} {len(tris):6d} tris  {np.round(p.min(0), 3)}..{np.round(p.max(0), 3)}")
    # The icon leaves out the reload's spare magazine.
    out["ak12_mag"] = triangles("magazine") + triangles("rounds")
    return out


# --- the icon --------------------------------------------------------------------------------------------------------

def icon(smds: dict[str, list], width: float = 0.9, supersample: int = 4) -> None:
    """The gun's left side as a white silhouette, `width` of the 1024px icon wide and centred (the other icons' 0.9)."""
    tris = np.array([[v[0] for v in verts] for name in SMDS.keys() | {"ak12_mag"} for _, verts in smds[name]])
    # Seen from its left: the muzzle (+x) to the left, up (+z) up.
    flat = np.stack([-tris[:, :, 0], -tris[:, :, 2]], -1)
    lo, hi = flat.reshape(-1, 2).min(0), flat.reshape(-1, 2).max(0)
    scale = width * 1024 * supersample / (hi[0] - lo[0])
    size = (int(np.ceil((hi[0] - lo[0]) * scale)) + 2, int(np.ceil((hi[1] - lo[1]) * scale)) + 2)
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    for tri in (flat - lo) * scale + 1:
        draw.polygon([tuple(p) for p in tri], fill=255)
    small = mask.resize((round(size[0] / supersample), round(size[1] / supersample)), Image.LANCZOS)
    out = Image.new("RGBA", (1024, 1024), (255, 255, 255, 0))
    white = Image.new("RGBA", small.size, (255, 255, 255, 255))
    white.putalpha(small)
    out.alpha_composite(white, ((1024 - small.size[0]) // 2, (1024 - small.size[1]) // 2))
    ICON.parent.mkdir(parents=True, exist_ok=True)
    out.save(ICON, optimize=True)
    print(f"icon {ICON.relative_to(ASSETS)}: {small.size[0]}x{small.size[1]}")


def main() -> None:
    icon(rig(assemble()))


if __name__ == "__main__":
    main()

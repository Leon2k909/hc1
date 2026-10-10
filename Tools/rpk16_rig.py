"""Put Escape from Tarkov's RPK-16 (ARC9 EFT Assault Rifles, Workshop 2962829818: the c_rpk16 viewmodel, decompiled to
decompiled/rpk16, and its default attachments, decompiled to decompiled/rpk16_atts) onto the RPK's CoD rig, as SMDs
the Kastov pipeline reads like the RPK's own receiver (decompiled/rpk16/rig), and draw its HUD icon from the
model's side.

It's built like the AK-12 (Tools/ak12_rig.py, whose maths it uses): the gun as ARC9 draws it in the idle pose, in the
"weapon" bone's frame, then onto the CoD rig's tag_sling space with the AK-12's FIT and SHIFT. The RPK-16 is an
AK-12-family LMG, so it goes on the RPK's rig (MWII's mg_iw9_rkilo) and plays the RPK's clips: an RPK's receiver bones
(the bolt carrier, selector, trigger, mag catch and both magazine bones) sit where the AK-105's do relative to
tag_sling, so the AK-12's fit holds on it. c_rpk16 plays the same ak_anims as c_ak12 and c_ak100, so the AK-12's
idle poses it.

Its own skeleton is posed here (weapon_bones), as the AK-74M's is: a bone the ak_anims idle animates takes the idle, and
any other bone keeps its reference offset from its posed parent. That also puts the bolt, selector, trigger and mag
catch (skinned to weapon_bolt, weapon_selector, weapon_trigger and weapon_release, which the reference pose leaves far
in front of the muzzle) back in the receiver.

The pieces, from the pack's arc9_eft_rpk16.lua and eft_rpk16_bulk.lua:
- c_rpk16's bodygroups: the receiver with its gas block, front sight and the moving parts, the long barrel (the pack's
  550.smd, ~550 mm in the model; the real long barrel is 580 mm, and the short one 415 mm. The pack's default 370 mm is
  no real RPK-16's), the railed dust cover (eft_rpk16_rec), the rear sight's base clamped on its rail
  (eft_rpk16_rs_base) and the 5.45 rounds;
- the default attachments on their slots: the RPK-16 muzzle brake on the long barrel's muzzle slot, the rear sight's
  leaf (eft_rpk16_rs) on its base, the handguard with its two side rail sections (eft_rpk16_mount_side), the folding
  stock tube (eft_rpk16_stock_tube) with the AK-12's telescoping stock on it (eft_ar_stock_ak12), the AK-12's pistol
  grip, and the 95-round drum (eft_mag_ak_rpk16_545_95).

The stock, grip and magazine are meshes of their own, so parts can take their places, and so are the brake (muzzle_tip)
and the rear sight, its base and leaf together (iron_sights: an optic takes it off, as on the real gun, where the sight
clamps to the dust cover's rail and an optic goes on the same rail, which runs on under it).

Run (after the decompile, before port_kastov.py --weapon rpk16): python Tools/rpk16_rig.py
"""
from __future__ import annotations

import numpy as np

from ak12_rig import ROUND_SKIP, Pieces, Rig, add_mesh, attachment_pose, icon, place_model, sub_slot
from kastov_smd import Smd
from kastov_weapons import ASSETS, DECOMPILED

VIEWMODEL = DECOMPILED / "rpk16"
SOURCE = DECOMPILED / "rpk16_atts"
RPK = DECOMPILED / "rkilo" / "vm_iw9_rkilo"
IDLE = DECOMPILED / "ak12" / "anims" / "ak_anims_anims" / "idle.smd"
ICON = ASSETS / "ui" / "weapons" / "guns" / "rpk16_01.png"

# A model whose QC $bbox is its SMD's extents turned +90 degrees about z (x' = -y, y' = x) is in studiomdl's
# pre-rotation space, so it's turned before it's placed: the brake, the side rails and the AK-12 stock.
TURN = np.array([[0, -1, 0, 0], [1, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], float)


def weapon_bones() -> dict[str, np.ndarray]:
    """Every c_rpk16 bone in the idle pose, in the weapon bone's frame."""
    ref = Smd(VIEWMODEL / "rpk16.smd")
    ref_world = ref.world(ref.dense_frames()[0])
    idle = Smd(IDLE)
    idle_world = idle.world(idle.dense_frames()[0])
    animated = {idle.name(i): idle_world[i] for i in range(len(idle.nodes))}
    posed: dict[str, np.ndarray] = {}
    for i, (name, parent) in enumerate(ref.nodes):
        if name in animated:
            posed[name] = animated[name]
        elif parent >= 0:
            posed[name] = posed[ref.name(parent)] @ np.linalg.inv(ref_world[parent]) @ ref_world[i]
        else:
            posed[name] = ref_world[i]
    to_weapon = np.linalg.inv(posed["weapon"])
    return {name: to_weapon @ m for name, m in posed.items()}


def assemble() -> Pieces:
    bones = weapon_bones()
    pieces: Pieces = {}
    for path in ("rpk16.smd", "550.smd", "reciever.smd", "sight rear.smd"):
        add_mesh(pieces, bones, path.removesuffix(".smd").replace(" ", "_"), VIEWMODEL / path)
    add_mesh(pieces, bones, "rounds", VIEWMODEL / "545.smd", skip=ROUND_SKIP)

    # The attachment models (one root bone at the origin), where the RPK-16's slots put them.
    tube_pos, tube_ang = (0.06, -0.03, 0.12), (0, 0, 1)
    stock_pos, stock_ang = sub_slot(tube_pos, tube_ang, (0.6, -3.5, 0.75), (-5, -90, 0))
    base_pos, base_ang = sub_slot((0, 0, 0), (0, 0, 0), (0, -7, -0.5), (0, -90, 0))
    leaf_pos, leaf_ang = sub_slot(base_pos, base_ang, (-1.27, 0, 0.1), (0, 90, 0))
    right_pos, right_ang = sub_slot((0, 0, 0), (0, 0, 0), (1, 7.6, -0.35), (180, 90, 0))
    left_pos, left_ang = sub_slot((0, 0, 0), (0, 0, 0), (-1, 7.6, -0.35), (0, -90, 0))
    for name, place, path in (
            ("brake", attachment_pose(bones["mod_barrel"], (0, 22.65, 0), (0, -90, 0)) @ TURN,
             "muzzle_rpk16_izhmash_rpk16_std_545x39_LOD0_0.smd"),
            ("rear_sight", attachment_pose(bones["mod_reciever"], leaf_pos, leaf_ang),
             "sight_rear_ak_izhmash_rpk16_rear_sight_std_LOD0_0.smd"),
            ("handguard", attachment_pose(bones["mod_handguard"], (0, 0, 0), (0, 0, 0)),
             "handguard_rpk16_izhmash_rpk16_std_LOD0.smd"),
            ("rail_right", attachment_pose(bones["mod_handguard"], right_pos, right_ang) @ TURN,
             "mount_rpk16_izhmash_rpk16_side_rail_LOD0_0.smd"),
            ("rail_left", attachment_pose(bones["mod_handguard"], left_pos, left_ang) @ TURN,
             "mount_rpk16_izhmash_rpk16_side_rail_LOD0_0.smd"),
            ("stock_tube", attachment_pose(bones["weapon_stock_lock_16"], tube_pos, tube_ang),
             "stock_rpk16_izhmash_rpk_stock_tube_LOD0_0.smd"),
            ("stock", attachment_pose(bones["weapon_stock_lock_16"], stock_pos, stock_ang) @ TURN,
             "stock_ar15_izhmash_ak12_std_LOD0_0new.smd"),
            ("pistol_grip", attachment_pose(bones["mod_pistol_grip"], (0, 0, 0), (0, 0, 0)),
             "pistolgrip_ak_izhmash_ak12_std_LOD0_0_new.smd"),
            ("magazine", attachment_pose(bones["mod_magazine"], (0, 0, 0), (0, 0, 0)),
             "mag_ak_izhmash_rpk16_drum_545x39_95_LOD0_0.smd")):
        place_model(pieces, name, place, SOURCE / path)
    return pieces


# SMD name -> its pieces. The brake and the rear sight (its base and leaf) are bodygroups (muzzle_tip, iron_sights), the
# stock, grip and magazine parts.
SMDS = {
    "rpk16_receiver": ("rpk16", "550", "reciever", "handguard", "rail_right", "rail_left"),
    "rpk16_brake": ("brake",),
    "rpk16_rear_sight": ("sight_rear", "rear_sight"),
    "rpk16_stock": ("stock_tube", "stock"),
    "rpk16_pgrip": ("pistol_grip",),
}


def main() -> None:
    pieces = assemble()
    for name, tris in pieces.items():
        p = np.concatenate([t[2] for t in tris])
        print(f"  {name:16s} {np.round(p.min(0), 2)}..{np.round(p.max(0), 2)}")
    rig = Rig(VIEWMODEL / "rig", RPK / "att_vm_p04_lm_rkilo_rec_v0_LOD0.smd",
              RPK / "vm_iw9_rkilo_anims" / "idle.smd")
    smds = {name: [tri for piece in names for tri in rig.triangles(pieces, piece)] for name, names in SMDS.items()}
    for name, tris in smds.items():
        rig.write(name, tris)
    rig.write("rpk16_mag", rig.magazine(pieces))
    smds["rpk16_mag"] = rig.magazine(pieces, spare=False)
    icon(smds, ICON)


if __name__ == "__main__":
    main()

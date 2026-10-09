"""Put Escape from Tarkov's Colt M16A2 (ARC9 EFT Assault Rifles, Workshop 2962829818: the c_m16 viewmodel, decompiled
to decompiled/m16a2, and its default attachments, decompiled to decompiled/m16a2_atts) onto the M16A4's CoD rig (MWII's
M16, decompiled/mike16), as SMDs the Kastov pipeline reads like the M16A4's own receiver (decompiled/m16a2/rig), and
draw its HUD icon from the model's side.

It's built like the AK-12 (Tools/ak12_rig.py, whose maths and Rig it uses): the gun as ARC9 draws it in the idle pose, in
the "weapon" bone's frame, then onto the M16A4's tag_sling space with the AK-12's FIT and the M16A2's own SHIFT. Both
are Colt's M16 on the same lower, so the fire control group, the magazine well and the bore sit where the M16A4's do:
SHIFT puts the M16A2's trigger pivot (weapon_trigger) on the M16A4's j_trigger.

The pieces, all from the pack's arc9_eft_m16a2.lua and its attachments' bulk files:
- c_m16's bodygroups: the shared parts and the bolt (m16.smd), the M16A2's lower with its burst trigger group
  (m16a2.smd: c_m16's "m4a1" group, whose other choice is the M16A1's), and the 5.56x45 rounds in the magazine's lips;
- the default attachments on their slots (eft_reciever_ar15_bulk.lua and the barrel, muzzle, handguard, pistol grip,
  charging handle, stock and magazine bulk files, the grip and tube from EFT SHARED, Workshop 2917343547): the A2 upper
  with its fixed carry handle and rear sight, the 20-inch (508 mm) barrel, the front sight base on its gas block, the
  A2 birdcage flash hider, the round ribbed A2 handguard (upper and lower halves), the A2 pistol grip, the early charging
  handle, the A2 buffer tube and fixed stock, and Colt's 30-round aluminium USGI magazine.

The m16a2_atts models are in studiomdl's pre-rotation space (their QC $bboxes are the SMDs turned +90 degrees about z),
so each is turned (TURN) before it's placed. The handguard's two halves aren't: they carry the left arm's bones for
ARC9's hand IK, their $bboxes match their SMDs, and their slot on the upper turns them 90 degrees itself.

Run (after the pack is decompiled, before port_kastov.py --weapon m16a2): python Tools/m16a2_rig.py
"""
from __future__ import annotations

import numpy as np

from ak12_rig import FIT, ROUND_SKIP, Pieces, Rig, add_mesh, attachment_pose, icon, place_model, sub_slot
from kastov_smd import Smd
from kastov_weapons import ASSETS, DECOMPILED

SOURCE = DECOMPILED / "m16a2"
ATTS = DECOMPILED / "m16a2_atts"
MIKE16 = DECOMPILED / "mike16"
ICON = ASSETS / "ui" / "weapons" / "guns" / "m16a2_01.png"

TURN = np.array([[0, -1, 0, 0], [1, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], float)

# Onto the M16A4's tag_sling space: the M16A2's trigger pivot on the M16A4's j_trigger (3.197, 0.701, -1.258).
SHIFT = np.array([-8.819, 0.694, 0.397])

# Tarkov bone -> rig bone. Checked against what the M16A4's clips move: j_bolt goes 3.07 back in fire, j_trigger turns
# 21.9 degrees, the ejection port cover 12.6, the bolt release (j_boltrel) 14 in the empty reload and the magazine
# release (j_magrel) moves in the reload. j_firesel and j_charginghandle never move.
BONES = {
    "weapon_bolt": "j_bolt",
    "weapon_trigger": "j_trigger",
    "weapon_selector": "j_firesel",
    "weapon_release": "j_magrel",
    "weapon_bolt_catch": "j_boltrel",
    "charge": "j_charginghandle",
    "tube": "tag_stock_attach",
    "stock": "tag_stock_attach",
    "magazine": "j_mag1",
    "patron_in_mag0": "j_mag1",
    "patron_in_mag1": "j_mag1",
    "patron_in_mag2": "j_mag1",
    "patron_in_mag3": "j_mag1",
}

# Compiled with their bones as they are (see the docstring).
UNTURNED = {"handguard", "handguard_lower"}

# The rounds' card for see-through magazines: in the steel USGI magazine it lies just inside the left wall (y 1.02-1.07
# against the wall's 1.07-1.17), never seen.
DROP = {"556fakebullets"}


def weapon_bones() -> dict[str, np.ndarray]:
    """Every c_m16 bone in the idle pose, in the weapon bone's frame. A bone the idle doesn't animate keeps its reference
    offset from its posed parent."""
    ref = Smd(SOURCE / "m16.smd")
    ref_world = ref.world(ref.dense_frames()[0])
    idle = Smd(SOURCE / "anims" / "ar15_anims_anims" / "idle.smd")
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
    add_mesh(pieces, bones, "shared", SOURCE / "m16.smd")
    add_mesh(pieces, bones, "lower", SOURCE / "m16a2.smd")
    add_mesh(pieces, bones, "rounds", SOURCE / "patrons.smd", skip=ROUND_SKIP)

    reciever = bones["mod_reciever"]
    # The upper's slot (mod_reciever, Ang 0 -90 0), and its barrel and handguard sub-slots.
    upper_pos, upper_ang = (0, 0, 0), (0, -90, 0)
    barrel_pos, barrel_ang = sub_slot(upper_pos, upper_ang, (-0.175, 0, -0.9), (0, 0, 0))
    gas_pos, gas_ang = sub_slot(barrel_pos, barrel_ang, (-13.17, 0, 0.25), (0, 0, 0))
    muzzle_pos, muzzle_ang = sub_slot(barrel_pos, barrel_ang, (-19.82, 0, 0), (0, 0, 0))
    hg_pos, hg_ang = sub_slot(upper_pos, upper_ang, (-0.22, 0, -0.99), (0, 90, 0))
    lower_hg_pos, lower_hg_ang = sub_slot(hg_pos, hg_ang, (0, 0.828, 0.1), (0, 0, 0))
    # The buffer tube's slot (mod_reciever 0 -7.7 0.9), and the stock on its sub-slot.
    tube_pos, tube_ang = (0, -7.7, 0.9), (0, -90, 0)
    stock_pos, stock_ang = sub_slot(tube_pos, tube_ang, (3, 0, 0.9), (0, 0, 0))
    for piece, place, path in (
            ("upper", attachment_pose(reciever, upper_pos, upper_ang), "reciever_ar15_colt_m16a2_std_LOD0.smd"),
            ("barrel", attachment_pose(reciever, barrel_pos, barrel_ang), "barrel_ar15_colt_m16_std_508mm_LOD0.smd"),
            ("gas_block", attachment_pose(reciever, gas_pos, gas_ang),
             "gas_block_ar15_colt_m4_front_sight_gas_block_std_LOD0_0.smd"),
            ("flash_hider", attachment_pose(reciever, muzzle_pos, muzzle_ang),
             "muzzle_ar15_colt_usgi_a2_556x45_LOD0_0.smd"),
            ("handguard", attachment_pose(reciever, hg_pos, hg_ang), "handguard_ar15_colt_m16a2_std_LOD0.smd"),
            ("handguard_lower", attachment_pose(reciever, lower_hg_pos, lower_hg_ang),
             "handguard_ar15_colt_m16a2_std_lower_LOD0.smd"),
            ("tube", attachment_pose(reciever, tube_pos, tube_ang), "stock_ar15_colt_stock_tube_A2_LOD0_0.smd"),
            ("stock", attachment_pose(reciever, stock_pos, stock_ang), "stock_ar15_colt_a2_std_LOD0.smd"),
            ("pistol_grip", attachment_pose(bones["mod_pistol_grip"], (0, 0, 0), (0, -90, 0)),
             "pistolgrip_ar15_colt_a2_LOD0_0.smd"),
            ("charge", attachment_pose(bones["mod_charge"], (0, 0, 0), (0, -90, 0)),
             "charge_ar15_colt_charging_handle_early_LOD0.smd"),
            ("magazine", attachment_pose(bones["mod_magazine"], (0, 0, 0), (0, -90, 0)),
             "mag_stanag_colt_ar15_std_556x45_30_LOD0_0.smd")):
        place_model(pieces, piece, place if piece in UNTURNED else place @ TURN, ATTS / path)
    return pieces


# SMD name -> its pieces. The flash hider is a bodygroup (muzzle_tip).
SMDS = {
    "m16a2_receiver": ("shared", "lower", "upper", "barrel", "gas_block", "handguard", "handguard_lower", "tube",
                       "stock", "pistol_grip", "charge"),
    "m16a2_flash_hider": ("flash_hider",),
}


def main() -> None:
    pieces = assemble()
    for name, tris in pieces.items():
        p = np.concatenate([t[2] for t in tris])
        print(f"  {name:16s} {len(tris):6d} {np.round(p.min(0), 2)}..{np.round(p.max(0), 2)}")
    rig = Rig(SOURCE / "rig", MIKE16 / "att_vm_p01_ar_mike16_rec_v0_LOD0.smd", MIKE16 / "vm_iw9_mike16_anims" / "idle.smd",
              FIT, SHIFT, BONES, drop=DROP)
    smds = {name: [tri for piece in names for tri in rig.triangles(pieces, piece)] for name, names in SMDS.items()}
    for name, tris in smds.items():
        rig.write(name, tris)
    rig.write("m16a2_mag", rig.magazine(pieces))
    smds["m16a2_mag"] = rig.magazine(pieces, spare=False)
    icon(smds, ICON)


if __name__ == "__main__":
    main()

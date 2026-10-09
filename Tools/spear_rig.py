"""Put Escape from Tarkov's SIG MCX-SPEAR (ARC9 EFT Assault Rifles, Workshop 2962829818: the c_spear viewmodel,
decompiled to decompiled/spear, and its default attachments, decompiled to decompiled/spear_atts) onto the MCX's CoD rig
(MW2019's M13, decompiled/mcharlie), as SMDs the Kastov pipeline reads like the MCX's own receiver
(decompiled/spear/rig), and draw its HUD icon from the model's side.

It's built like the AK-12 (Tools/ak12_rig.py, whose maths and Rig it uses): the gun as ARC9 draws it in the idle pose, in
the "weapon" bone's frame, then onto the MCX's tag_sling space with the AK-12's FIT and SPEAR's own SHIFT. Both guns are
SIG's short-stroke piston MCX family with AR-15-pattern lowers, so the SPEAR's fire control and magazine well sit where
the MCX's do: SHIFT puts the SPEAR's trigger pivot (mod_trigger) on the MCX's j_trigger, which leaves the bore 0.32
under the MCX's.

The pieces, all from the pack's arc9_eft_spear.lua and eft_spear_bulk.lua:
- c_spear's bodygroups: the lower and the internals (spear.smd), the upper, the 330 mm (13-inch) barrel, the adjustable
  gas piston, the side charging handle, the M-LOK handguard, the Clutch-LOK QD flash hider, the op rod (body9_model0),
  and the 6.8x51 FMJ rounds in the magazine's lips;
- the default attachments on their slots: SIG's reduced-angle pistol grip, the Lancer L7 AWM 20-round magazine, and the
  stock: SIG's locking hinge, the low-profile tube and a Magpul MOE SL-K.
- SIG's flip-up sights, which the pack's default build leaves off for its scope: the rear on the upper's rear sight
  slot, the front on the handguard's front sight slot (eft_rearsight_mcx and eft_frontsight_mcx, EFT SHARED, Workshop
  2917343547). Each is a base with its leaf raised or folded (spear_sights_on, spear_sights_off).
Left out: the pack's suppressor, scope and mount.

All the spear_atts models are in studiomdl's pre-rotation space (their QC $bboxes are the SMDs turned +90 degrees about
z), so each is turned (TURN) before it's placed.

The skin is the pack's first, the coyote tan the US Army's XM7 and SIG's own MCX-SPEAR come in.

Run (after the pack is decompiled, before port_kastov.py --weapon spear): python Tools/spear_rig.py
"""
from __future__ import annotations

import numpy as np

from ak12_rig import FIT, ROUND_SKIP, Pieces, Rig, add_mesh, attachment_pose, icon, place_model, sub_slot
from kastov_smd import Smd
from kastov_weapons import ASSETS, DECOMPILED

SOURCE = DECOMPILED / "spear"
ATTS = DECOMPILED / "spear_atts"
MCX = DECOMPILED / "mcharlie" / "v_mcharlie"
ICON = ASSETS / "ui" / "weapons" / "guns" / "spear_01.png"

TURN = np.array([[0, -1, 0, 0], [1, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], float)

# Onto the MCX's tag_sling space: the SPEAR's trigger pivot on the MCX's j_trigger (3.323, 0, -1.765).
SHIFT = np.array([-8.564, 0.0, -0.106])

# Tarkov bone -> rig bone. Checked against what the MCX's clips move: j_bolt goes 3.3 back in fire and is locked back
# at the empty reload's start, j_trigger turns 16.8 degrees in fire, the bolt release (j_bump_rel) 19 in the empty
# reload and the magazine release (j_magrel_right) moves in the reload. j_charginghandle and j_firesel never move.
BONES = {
    "weapon_bolt": "j_bolt",
    "weapon_bolt_assembly": "j_bolt",
    "mod_trigger": "j_trigger",
    "weapon_trigger": "j_trigger",
    "mod_selector": "j_firesel",
    "weapon_selector": "j_firesel",
    "mod_catch": "j_bump_rel",
    "mod_release": "j_magrel_right",
    "weapon_release": "j_magrel_right",
    "mod_charge": "j_charginghandle",
    "hinge": "tag_stock_attach",
    "tube": "tag_stock_attach",
    "stock": "tag_stock_attach",
    "magazine": "j_mag1",
    "patron_in_mag0": "j_mag1",
    "patron_in_mag1": "j_mag1",
    "patron_in_mag2": "j_mag1",
}


def weapon_bones() -> dict[str, np.ndarray]:
    """Every c_spear bone in the idle pose, in the weapon bone's frame. A bone the idle doesn't animate keeps its
    reference offset from its posed parent."""
    ref = Smd(SOURCE / "spear.smd")
    ref_world = ref.world(ref.dense_frames()[0])
    idle = Smd(SOURCE / "c_spear_anims" / "idle.smd")
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
    for piece, path in (("lower", "spear.smd"),
                        ("upper", "reciever_mcx_sig_spear_upper_LOD0.smd"),
                        ("barrel", "barrel_mcx_sig_spear_330mm_68x51_LOD0.smd"),
                        ("gas_block", "gas_block_mcx_sig_adjustable_gas_piston_LOD0.smd"),
                        ("charge", "charge_spear_sig_spear_std_LOD0.smd"),
                        ("handguard", "handguard_mcx_sig_spear_m_lok_LOD0.smd"),
                        ("op_rod", "body9_model0.smd"),
                        ("flash_hider", "muzzle_ar10_sig_clutch_lok_qd_flash_hider_68x51_LOD0.smd")):
        add_mesh(pieces, bones, piece, SOURCE / path)
    add_mesh(pieces, bones, "rounds", SOURCE / "patron_68x51_fmj_full_LOD0.smd", skip=ROUND_SKIP)

    reciever = bones["mod_reciever"]
    # The upper's slot (mod_reciever, Ang 0 -90 0), and its rear sight sub-slot.
    upper_pos, upper_ang = (0, 0, 0), (0, -90, 0)
    rear_pos, rear_ang = sub_slot(upper_pos, upper_ang, (6.5, 0, -2.9), (0, 0, 0))
    # The handguard's sub-slot on the upper, and its front sight sub-slot (eft_frontsight_mcx's ModelOffset 0 -0.03 0).
    hg_pos, hg_ang = sub_slot(upper_pos, upper_ang, (-0.69, 0, -0.01), (0, 90, 0))
    front_pos, front_ang = sub_slot(hg_pos, hg_ang, (0, 11.0, -2.9), (0, -90, 0))
    # The stock slot (mod_reciever 0 -10.07 1.34, Ang 0 -90 0): the hinge, the tube on it, and the stock on the tube's
    # sub-slot (eft_ar_stock_magpul_slk's ModelOffset -0.5 0 0).
    stock_pos, stock_ang = (0, -10.07, 1.34), (0, -90, 0)
    slk_pos, slk_ang = sub_slot(stock_pos, stock_ang, (3.5, 0, 0.7), (0, 0, 0))
    for piece, place, path in (
            ("pistol_grip", attachment_pose(bones["mod_pistol_grip"], (0, 0, 0), (0, -90, 0)),
             "pistolgrip_ar15_sig_reduced_angle_pistol_grip_LOD0.smd"),
            ("magazine", attachment_pose(bones["mod_magazine"], (0, 0, 0), (0, -90, 0)),
             "mag_ar10_lancer_l7_awm_762x51_20_LOD0.smd"),
            ("magazine25", attachment_pose(bones["mod_magazine"], (0, 0, 0), (0, -90, 0)),
             "mag_ar10_lancer_l7_awm_762x51_25_LOD0.smd"),
            ("hinge", attachment_pose(reciever, stock_pos, stock_ang),
             "stock_all_sig_stock_locking_hinge_assembly_LOD0.smd"),
            ("tube", attachment_pose(reciever, stock_pos, stock_ang), "stock_base_sig_low_profile_tube_LOD0.smd"),
            ("stock", attachment_pose(reciever, slk_pos, slk_ang, (-0.5, 0, 0)),
             "stock_ar15_magpul_moe_sl_k_carbine_LOD0.smd")):
        place_model(pieces, piece, place @ TURN, ATTS / path)
    rear = attachment_pose(reciever, rear_pos, rear_ang) @ TURN
    front = attachment_pose(reciever, front_pos, front_ang, (0, -0.03, 0)) @ TURN
    for state in ("base", "unfolded", "folded"):
        place_model(pieces, f"rear_{state}", rear, ATTS / f"sight_rear_all_sig_flip_up_{state}_LOD0_0.smd")
        place_model(pieces, f"front_{state}", front, ATTS / f"sight_front_all_sig_flip_up_{state}_LOD0_0.smd")
    # The magazine models carry a stray untextured shell.
    for name in ("magazine", "magazine25"):
        pieces[name] = [tri for tri in pieces[name] if tri[1] != "no_material"]
    return pieces


# SMD name -> its pieces. The flash hider and the sights are bodygroups (muzzle_tip, iron_sights, sight_folded), the
# grip and magazines parts.
SMDS = {
    "spear_receiver": ("lower", "upper", "barrel", "gas_block", "charge", "handguard", "op_rod", "hinge", "tube",
                       "stock"),
    "spear_flash_hider": ("flash_hider",),
    "spear_sights_on": ("rear_base", "rear_unfolded", "front_base", "front_unfolded"),
    "spear_sights_off": ("rear_base", "rear_folded", "front_base", "front_folded"),
    "spear_pgrip": ("pistol_grip",),
}


def main() -> None:
    pieces = assemble()
    for name, tris in pieces.items():
        p = np.concatenate([t[2] for t in tris])
        print(f"  {name:16s} {len(tris):6d} {np.round(p.min(0), 2)}..{np.round(p.max(0), 2)}")
    rig = Rig(SOURCE / "rig", MCX / "attachment_vm_ar_mcharlie_receiver.smd", MCX / "v_mcharlie_anims" / "idle.smd",
              FIT, SHIFT, BONES, drop=set())
    smds = {name: [tri for piece in names for tri in rig.triangles(pieces, piece)] for name, names in SMDS.items()}
    for name, tris in smds.items():
        rig.write(name, tris)
    rig.write("spear_mag", rig.magazine(pieces))
    mag25 = {**pieces, "magazine": pieces["magazine25"]}
    rig.write("spear_mag25", rig.magazine(mag25))
    smds["spear_mag"] = rig.magazine(pieces, spare=False)
    # The icon is the factory gun with its sights folded.
    icon({name: tris for name, tris in smds.items() if name != "spear_sights_on"}, ICON)


if __name__ == "__main__":
    main()

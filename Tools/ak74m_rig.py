"""Put Escape from Tarkov's AK-74M (ARC9 EFT Assault Rifles, Workshop 2962829818: the c_ak100 viewmodel, decompiled to
decompiled/ak15, and its default attachments, decompiled to decompiled/ak74m) onto the AK-105's CoD rig, as SMDs the
Kastov pipeline reads like the AK-105's own receiver (decompiled/ak74m/rig), and draw its HUD icon from the model's side.

It's built like the AK-12 (Tools/ak12_rig.py, whose maths and rig it uses): the gun as ARC9 draws it in the idle pose, in
the "weapon" bone's frame, then onto the AK-105's tag_sling space with the AK-12's FIT and SHIFT. c_ak100 and c_ak12
share their clips (both include ak_anims.mdl) and the bones those clips move, so the AK-12's fit holds: the AK-74M's
magazine slot and dust cover bone are within 0.3 of the AK-12's.

c_ak100 has slot bones c_ak12 lacks, so its own skeleton is posed here (weapon_bones): a bone the ak_anims idle
animates takes the idle, and any other bone keeps its reference offset from its posed parent.

The pieces, all from the pack's arc9_eft_ak74m.lua (DefaultBodygroups "12000000000000": the AK-74M base and barrel):
- c_ak100's bodygroups: the AK-74M receiver and barrel, the parts the AK-100s share (bolt, selector, trigger, mag
  catch), the side rail (planka), the stock's release button and the front sight block (kolodka), and the 5.45 rounds;
- the default attachments on their slots: the 6P20 0-20 muzzle brake (eft_muzzle_ak_ak74m_std), the 6P34 0-1 dust
  cover, the 6P34 Sb.15 side-folding polymer stock, the 6P1 Sb.8 polymer pistol grip, the 6L23 polymer magazine, the
  6P20 Sb.1-2 gas tube, and the 6P20 Sb.2 rear sight.

The handguard: the pack's default (eft_handguard_ak_vityaz_std_plastic) is the Vityaz's, whose material it doesn't ship,
so it would draw untextured. The AK-74M's own black polymer handguard (the 6P20 Sb.9 lower and the gas tube's cover) is in
the pack in the AK-74M's handguard material (handguard_ak_izhmash_ak74m_std_plastic: its vmt in the Assault Rifles pack,
its textures in EFT SHARED), as the stock pieces two aftermarket models keep:
- the lower handguard, from the UltiMAK M1-B gas tube (ak_gb_m1b), which replaces only the upper. ARC9 draws it on the
  gas block slot with no offset, so it's placed there, as the gas tube is;
- the upper handguard, from the CNC Guns OV GP lower handguard (ak_hg_cncguns), which keeps the stock upper. It goes on
  the handguard sub-slot, where it lines up with the Vityaz's upper to 0.04.
Only their AK-74M handguard triangles are taken (HANDGUARD). The lower's front tongue reaches 0.45 past the barrel's
ferrule (kolodka), where the M1-B's own collar covers it, so it's pressed back to the ferrule's middle (FERRULE_Y), where
the Vityaz's lower ends.

The stock is a mesh of its own (ak74m_stock), so the AK-105's stocks can take its place, and so is the release
button on the receiver's rear (ak74m_stock_hinge): it belongs to the folding stock's latch, and the fixed stocks hide it,
as the AK-105's hinge block does.

The optic mount (ak74m_mount, shown only under an optic): the real AK-74M has no top rail. An optic goes on a bracket
clamped to the dovetail on the receiver's left side (the planka), and Zenit's B-13 "Klassika" is the common one: a
Picatinny rail over the dust cover, held by an arm from the dovetail. It's the pack's eft_mount_dovetail_b13 on the
AK-74M's dovetail slot (mod_mount_000).

Run (after the decompile, with ak_gb_m1b, ak_hg_cncguns and mount_dovetail_zenit_b13 decompiled into decompiled/ak74m
too, before
port_kastov.py --weapon ak74m): python Tools/ak74m_rig.py
"""
from __future__ import annotations

import numpy as np

from ak12_rig import ROUND_SKIP, Pieces, Rig, add_mesh, attachment_pose, icon, place_model, sub_slot
from kastov_smd import Smd
from kastov_weapons import ASSETS, DECOMPILED

VIEWMODEL = DECOMPILED / "ak15"  # c_ak100, decompiled for the AK-15's rounds
SOURCE = DECOMPILED / "ak74m"
IDLE = DECOMPILED / "ak12" / "anims" / "ak_anims_anims" / "idle.smd"
ICON = ASSETS / "ui" / "weapons" / "guns" / "ak74m_01.png"

# A model whose QC $bbox is its SMD's extents turned +90 degrees about z (x' = -y, y' = x) is in studiomdl's
# pre-rotation space, so it's turned before it's placed. Of the AK-74M's attachments only the brake is.
TURN = np.array([[0, -1, 0, 0], [1, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], float)

# The AK-74M's own polymer handguard material; see the docstring.
HANDGUARD = ("handguard_ak_izhmash_ak74m_std_plastic_LOD0",)
# The ferrule's middle along the weapon bone's y (forward is -y): the lower handguard's tongue ends there.
FERRULE_Y = -25.96


def weapon_bones() -> dict[str, np.ndarray]:
    """Every c_ak100 bone in the idle pose, in the weapon bone's frame."""
    ref = Smd(VIEWMODEL / "ak74m.smd")
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
    for path in ("ak74m.smd", "ak74m barrel.smd", "ak shared parts.smd", "ak100_planka.smd", "stock_release.smd",
                 "kolodka.smd"):
        add_mesh(pieces, bones, path.removesuffix(".smd").replace(" ", "_"), VIEWMODEL / path)
    add_mesh(pieces, bones, "rounds", VIEWMODEL / "545.smd", skip=ROUND_SKIP)

    # The attachment models (one root bone at the origin), where the AK-74M's slots put them.
    handguard_pos, handguard_ang = sub_slot((0, 0, 0), (0, 0, 0), (0, -1.8, 0.5), (0, 0, 0))
    for name, place, path in (
            ("brake", attachment_pose(bones["mod_muzzle"], (0, 0.1, 0), (0, -90, 0)) @ TURN,
             "muzzle_ak74_izhmash_ak74m_std_545x39_LOD0_0.smd"),
            ("dust_cover", attachment_pose(bones["mod_reciever"], (0, 0, 0), (0, 0, 0)),
             "reciever_ak74_izhmash_ak74m_std_LOD0_0.smd"),
            ("stock", attachment_pose(bones["mod_stock"], (0, 0, 0), (0, 0, 3)),
             "stock_ak74m_izhmash_ak74m_std_LOD0_0.smd"),
            ("pistol_grip", attachment_pose(bones["mod_pistol_grip"], (0, 0, -0.05), (0, 0, 0)),
             "pistolgrip_ak_izhmash_ak74_plastic_LOD0_0.smd"),
            ("magazine", attachment_pose(bones["mod_magazine"], (0, 0.07, -0.2), (0, 0, 0)),
             "mag_ak74_izhmash_6L23_545x39_30_LOD0_0.smd"),
            ("gas_tube", attachment_pose(bones["mod_gas_block"], (0, 0, 0), (0, 0, 0)),
             "gas_block_ak_izhmash_akm_std_LOD0_0.smd"),
            ("rear_sight", attachment_pose(bones["mod_sight_rear"], (0, 0, 0), (0, 0, 0)),
             "sight_rear_ak_izhmash_ak74m_std_LOD0_0.smd")):
        place_model(pieces, name, place, SOURCE / path)
    place_model(pieces, "handguard_lower", attachment_pose(bones["mod_gas_block"], (0, 0, 0), (0, 0, 0)),
                SOURCE / "handguard_ak_ultimak_m1b_std_plastic_LOD0_0.smd", HANDGUARD)
    for _, _, ps, _, _ in pieces["handguard_lower"]:
        ps[:, 1] = np.maximum(ps[:, 1], FERRULE_Y)
    place_model(pieces, "handguard_upper", attachment_pose(bones["mod_gas_block"], handguard_pos, handguard_ang),
                SOURCE / "handguard_ak_cnc_guns_ov_gp_LOD0.smd", HANDGUARD)
    # The Zenit B-13 on the dovetail slot, as the pack's eft_mount_dovetail_b13 draws it (its ModelAngleOffset turns
    # the slot's -90 back).
    place_model(pieces, "mount", attachment_pose(bones["mod_mount_000"], (0.05, 1.05, 0.49), (0, -90, 0),
                                                 model_angle=(0, 90, 0)),
                SOURCE / "mount_dovetail_zenit_b13_LOD0_0.smd")
    return pieces


# SMD name -> its pieces. The brake, the mount and the release button are bodygroups (muzzle_tip, optic_rail,
# stock_hinge), the stock, grip and magazine parts. The rear sight is a mesh of its own but always shown: it stays under
# an optic, as on the real gun.
SMDS = {
    "ak74m_receiver": ("ak74m", "ak74m_barrel", "ak_shared_parts", "ak100_planka", "kolodka", "dust_cover", "gas_tube",
                       "handguard_lower", "handguard_upper"),
    "ak74m_stock": ("stock",),
    "ak74m_stock_hinge": ("stock_release",),
    "ak74m_brake": ("brake",),
    "ak74m_rear_sight": ("rear_sight",),
    "ak74m_pgrip": ("pistol_grip",),
    "ak74m_mount": ("mount",),
}


def main() -> None:
    pieces = assemble()
    for name, tris in pieces.items():
        p = np.concatenate([t[2] for t in tris])
        print(f"  {name:16s} {np.round(p.min(0), 2)}..{np.round(p.max(0), 2)}")
    rig = Rig(SOURCE / "rig")
    smds = {name: [tri for piece in names for tri in rig.triangles(pieces, piece)] for name, names in SMDS.items()}
    for name, tris in smds.items():
        rig.write(name, tris)
    rig.write("ak74m_mag", rig.magazine(pieces))
    smds["ak74m_mag"] = rig.magazine(pieces, spare=False)
    # The icon is the factory gun, with no optic, so no mount.
    icon({name: tris for name, tris in smds.items() if name != "ak74m_mount"}, ICON)


if __name__ == "__main__":
    main()

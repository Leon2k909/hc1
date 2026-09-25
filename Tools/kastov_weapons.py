#!/usr/bin/env python3
"""The guns the Kastov pipeline ports (port_kastov.py, kastov_vmdl.py, kastov_animgraph.py, kastov_prefabs.py).

Each script takes --weapon (default kastov762). The guns are CoD MWII viewmodels decompiled with Crowbar whose rigs
share the v_akm skeleton and clip names, so only their meshes, parts and HC1 asset names differ.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np

from kastov_smd import euler_to_mat, matrix

PROJECT = Path(__file__).resolve().parents[1]
ASSETS = PROJECT / "Assets"
DECOMPILED = Path(r"D:\tmp\hc1-mw22-tools\decompiled")


def view_offset(pos=(0.0, 0.0, 0.0), angles=(0.0, 0.0, 0.0)) -> np.ndarray:
    """One of the MW base's SWEP.ViewModelOffsets: Pos (right, forward, up) and Angles (pitch, yaw, roll, degrees)
    from the camera, as a transform in viewmodel space (X forward, Y left, Z up)."""
    right, forward, up = pos
    pitch, yaw, roll = np.radians(angles)
    return matrix(np.array([forward, -right, up], float), euler_to_mat(roll, pitch, yaw))


@dataclass(frozen=True)
class Weapon:
    name: str  # the equipment resource and prefab names: <name>.equip, weapon_<name>.prefab, ...
    folder: Path  # the gun's asset folder
    asset: str  # the same folder as an asset path
    model: str  # the models are v_<model>.vmdl and w_<model>.vmdl
    decompiled: Path  # Crowbar output: the viewmodel and its attachment models
    cod_anims: str  # the viewmodel's animation SMDs, under decompiled
    # Meshes on the CoD viewmodel itself, and attachment models bone-merged onto it (mesh, the part's reference pose).
    vm_meshes: list[str]
    part_meshes: list[tuple[str, str]]
    # Bodygroup pieces, each written as its own mesh for a bodygroup (kastov_vmdl.py): name -> (mesh, the reference
    # pose of the part it belongs to, or None for pieces on the viewmodel itself). The gunsmith switches them with
    # the attachment slots: the rails appear under a fitted optic, grip or laser, the muzzle tip gives way to a muzzle
    # device.
    optional_meshes: dict[str, tuple[str, str | None]]
    # Extra bones: name -> (parent, local offset). The muzzle sits at the default barrel's tag_flash.
    extra_bones: dict[str, tuple[str, np.ndarray]]
    # SMD material -> the HC1 material it becomes.
    materials: Callable[[], dict[str, str]]
    # The addon's SWEP.ViewModelOffsets Idle, Aim and Sprint (view_offset): where the MW base draws the viewmodel
    # relative to the camera.
    hip: np.ndarray
    aim: np.ndarray
    sprint: np.ndarray
    # The frame of the ADS clip (ads_in / ads_out) that puts the sights on the camera together with aim.
    ads_pose: tuple[str, slice]
    # Optional independent lowered pose; sprint changes should not pull this pose along with them.
    lowered: np.ndarray | None = None
    # Run with HC1's M4 sprint (port_kastov.Kastov.m4_sprint) instead of CoD's a_sprint and the sprint offset, so the
    # gun turns toward the chest like the M4's. CoD's a_sprint alone runs the gun pointing straight ahead with a large
    # sideways bob, and it moves the camera bone, which HC1 adds to the view (ViewModel.ApplyAnimationTransform).
    m4_sprint: bool = False
    # The reload's fresh magazine: parked out of view when unused, so the world model leaves it out.
    spare_mag: str = "j_mag2"
    # More bones whose world model positions port_kastov.py prints, for placing the gunsmith slots.
    report_bones: list[str] = field(default_factory=list)
    # Swappable parts, each a bodygroup with one choice per attachment model (kastov_vmdl.py): group -> [(choice,
    # mesh)]. Choice 0 is the factory part; the gun's own gunsmith parts pick the others (kastov_prefabs.py). Every
    # model has a single root bone or only bones the viewmodel has, so its own skeleton places it (bone-merge).
    part_choices: dict[str, list[tuple[str, str]]] = field(default_factory=dict)
    # More muzzle_tip choices, between "on" and "off": the tips of part_choices barrels of other lengths, which the
    # barrel's gunsmith slot shows (kastov_prefabs.Prefabs.part_slot_bodygroups). name -> (mesh, reference pose).
    tip_choices: dict[str, tuple[str, str]] = field(default_factory=dict)
    # Reloads for magazines of another kind than the factory one (the RPK's box magazines): each is a suffix of the CoD
    # clips reload<suffix> and reload_empty<suffix>, exported under the same names. The animgraph's reload_variant picks
    # one (0 = the factory reload, then these in order), set from the fitted magazine (GunsmithPart.ReloadAnimation).
    reload_variants: list[str] = field(default_factory=list)


def kastov762_materials() -> dict[str, str]:
    from kastov_materials import MATERIALS, OUT_ASSET
    return {name: f"{OUT_ASSET}/{name}.vmat" for name in MATERIALS}


def kastov74u_materials() -> dict[str, str]:
    # Converted by the session that added the 74u's world model: SMD material -> vmat.
    assets = json.loads((ASSETS / "Weapons" / "Kastov74u" / "ks74u_assets.json").read_text(encoding="utf-8"))
    return assets["materials"]


KASTOV_762 = Weapon(
    name="kastov762",
    folder=ASSETS / "Weapons" / "Kastov",
    asset="weapons/kastov",
    model="kastov",
    decompiled=DECOMPILED / "kastov",
    cod_anims="v_akm/v_akm_anims",
    vm_meshes=["v_akm/att_rex_vm_ar_akilo_rec_v0_LOD0.smd", "v_akm/rec_upp.smd", "v_akm/ammo.smd"],
    part_meshes=[
        ("ak47_b_d/att_rex_vm_ar_akilo_barrel_v0_LOD0.smd", "ak47_b_d/ak47_b_d_anims/reference.smd"),
        ("ak47_b_d/iro.smd", "ak47_b_d/ak47_b_d_anims/reference.smd"),
        ("ak47_m_d/att_rex_vm_ar_akilo_mag_v0_LOD0.smd", "ak47_m_d/ak47_m_d_anims/reference.smd"),
        ("ak47_m_d/76239.smd", "ak47_m_d/ak47_m_d_anims/reference.smd"),
        ("ak47_s_d/att_rex_vm_ar_akilo_stock_v0_LOD0.smd", "ak47_s_d/ak47_s_d_anims/reference.smd"),
        ("ak47_p_d/att_rex_vm_ar_akilo_pgrip_v0_LOD0.smd", "ak47_p_d/ak47_p_d_anims/reference.smd"),
    ],
    optional_meshes={
        "muzzle_tip": ("ak47_b_d/tip.smd", "ak47_b_d/ak47_b_d_anims/reference.smd"),
        "optic_rail": ("ak47_b_d/rail.smd", "ak47_b_d/ak47_b_d_anims/reference.smd"),
        "grip_rail": ("ak47_b_d/grip.smd", "ak47_b_d/ak47_b_d_anims/reference.smd"),
        "laser_rail": ("ak47_b_d/laser.smd", "ak47_b_d/ak47_b_d_anims/reference.smd"),
    },
    extra_bones={"muzzle": ("tag_barrel_attach", np.array([15.828125, 0.0, 0.0]))},
    materials=kastov762_materials,
    hip=view_offset((0.0, 2.0, 0.0)),
    aim=view_offset(),
    # With m4_sprint this only places the lowered pose.
    sprint=view_offset((0.0, 0.0, -1.5)),
    m4_sprint=True,
    # ads_in's last frame is slightly off; ads_out starts exactly on the sights.
    ads_pose=("ads_out", slice(0, 1)),
)

_74U_BARREL = "att_vm_p04_ar_akilo74_barrel_v0/att_vm_p04_ar_akilo74_barrel_v0"
_74U_BARREL_REFERENCE = "att_vm_p04_ar_akilo74_barrel_v0/att_vm_p04_ar_akilo74_barrel_v0_anims/reference.smd"


def _attachment(model: str) -> tuple[str, str]:
    """A part_choices entry for a Crowbar decompile of att_vm_p04_<model>.mdl."""
    folder = f"att_vm_p04_{model}"
    return model, f"{folder}/{folder}_LOD0.smd"



KASTOV_74U = Weapon(
    name="kastov74u",
    folder=ASSETS / "Weapons" / "Kastov74u",
    asset="weapons/kastov74u",
    model="kastov74u",
    decompiled=DECOMPILED / "akilo74",
    cod_anims="v_akilo74/v_akilo74_anims",
    # body5_model0 is the fire selector.
    vm_meshes=["v_akilo74/att_vm_p04_ar_akilo74_rec_v0_LOD0.smd", "v_akilo74/body5_model0.smd"],
    part_meshes=[(f"{_74U_BARREL}_LOD0.smd", _74U_BARREL_REFERENCE)],
    optional_meshes={
        "muzzle_tip": (f"{_74U_BARREL}_tip.smd", _74U_BARREL_REFERENCE),  # the 74u's muzzle booster
        "optic_rail": ("v_akilo74/att_vm_p04_ar_akilo74_rec_v0_rail.smd", None),  # side mount on the receiver
        "grip_rail": (f"{_74U_BARREL}_grip.smd", _74U_BARREL_REFERENCE),
        "laser_rail": (f"{_74U_BARREL}_laser.smd", _74U_BARREL_REFERENCE),
    },
    # tag_flash_attachment on the barrel.
    extra_bones={"muzzle": ("tag_barrel_attach", np.array([8.378, 0.0, -1.398]))},
    materials=kastov74u_materials,
    # From the addon's lua/weapons/mg_iw9_akilo74/shared.lua (workshop item 3499492742).
    hip=view_offset((0.02, 0.0, 0.0), (0.0, -0.22, 0.0)),
    aim=view_offset((0.02, 0.0, -0.178), (0.0, -0.22, 0.0)),
    # HC1's M4 sprint brings the weapon root about 1.2 units toward the camera.
    # Positive forward pushed this gun away from the player during the run.
    sprint=view_offset((0.0, -1.2, -0.4)),
    m4_sprint=True,
    lowered=view_offset((0.0, 2.4, -0.4)),
    # With aim, ads_in's end centres the front post in the rear notch; ads_out's start is ~0.4 low.
    ads_pose=("ads_in", slice(-1, None)),
    report_bones=["tag_rail", "tag_tip", "tag_grip_attach", "tag_laser_attach"],
    # The stocks, pistol grips and magazines the addon offers the 74u (lua/weapons/mg_iw9_akilo74/customization.lua).
    # Its barrels are left out: each moves the left hand (SWEP.GripPoseParameters), which the ported clips can't.
    part_choices={
        "stock": [_attachment(model) for model in (
            "ar_akilo74_stock_v0", "ar_akilo74_stockno_v0", "ar_akilo74_stockskel_v0", "ar_akilo_stock_v0",
            "ar_akilo_stockh_v0", "ar_akilo_stocktac_v0", "ar_akilo_stocktac02_v0", "ar_akilo_stockwire_v0",
            "sh_vecho_stock_v0", "sh_vecho_stocktac_v0", "lm_rkilo_stock_v0", "lm_rkilo_stockh_v0")],
        "pistol_grip": [_attachment(model) for model in (
            "ar_akilo_pstlgrp_v0", "ar_akilo_griptac_v0", "ar_akilo_gripstdy_v0", "ar_akilo_gripass_v0",
            "sh_vecho_pgrip_v0", "sh_vecho_gripsnp_v0")],
        # Each holds the fitted magazine (j_mag1) and the reload's fresh one (j_mag2).
        "magazine": [_attachment(model) for model in (
            "ar_akilo74_mag_v0", "ar_akilo105_smag_v0", "ar_akilo105_xmag_v0")],
    },
)


def vityaz_materials() -> dict[str, str]:
    # Built by vityaz_assets.py; the stocks and grips reuse the 74u's materials.
    assets = json.loads((ASSETS / "Weapons" / "Vityaz" / "vityaz_assets.json").read_text(encoding="utf-8"))
    return assets["materials"]


_VITYAZ_BARREL = "att_vm_p04_sm_aviktor_barrel_v0_lod0"
_VITYAZ_BARREL_REFERENCE = f"{_VITYAZ_BARREL}/{_VITYAZ_BARREL}_anims/reference.smd"
_VITYAZ_LONG_BARREL = "att_vm_p04_sm_aviktor_barlightlong_v0_lod0"


def _kastovia(model: str) -> tuple[str, str]:
    """A part_choices entry for one of the Kastovia platform parts in the 74u's decompile."""
    choice, path = _attachment(model)
    return choice, f"../akilo74/{path}"


# The PP-19-01 Vityaz 9mm SMG: the MWII "Vaznev-9K" (mg_iw9_aviktor) from the same addon as the 74u.
VITYAZ = Weapon(
    name="vityaz",
    folder=ASSETS / "Weapons" / "Vityaz",
    asset="weapons/vityaz",
    model="vityaz",
    decompiled=DECOMPILED / "aviktor",
    cod_anims="v_aviktor/v_aviktor_anims",
    # body2_model0 holds the moving parts (bolt carrier, fire selector, trigger) and the top rail.
    vm_meshes=["v_aviktor/att_vm_p04_sm_aviktor_rec_v0_LOD0.smd", "v_aviktor/body2_model0.smd"],
    part_meshes=[],
    # No separate rail pieces: the top rail is part of the receiver, and grips and lasers fit the handguard directly.
    optional_meshes={"muzzle_tip": (f"{_VITYAZ_BARREL}/bartip.smd", _VITYAZ_BARREL_REFERENCE)},
    # tag_flash on the barrel.
    extra_bones={"muzzle": ("tag_barrel_attach", np.array([6.943, 0.0, -1.398]))},
    materials=vityaz_materials,
    # From the addon's lua/weapons/mg_iw9_aviktor/shared.lua.
    hip=view_offset(),
    aim=view_offset((0.0, 2.0, 0.0)),
    sprint=view_offset((-0.2, 0.5, 0.4)),
    m4_sprint=True,
    ads_pose=("ads_in", slice(-1, None)),
    report_bones=["tag_tip", "tag_grip_attach", "tag_laser_attach"],
    # The parts the addon offers the Vityaz (lua/weapons/mg_iw9_aviktor/customization.lua). The stocks and pistol
    # grips are Kastovia platform parts; the factory ones are the AK-74M-style polymer folding stock and AK pistol
    # grip the real PP-19-01 Vityaz uses (the addon's factory stock is the 74u's K-Bloc). The barrels are the factory
    # one and the SA Response III, a longer barrel under the same handguard with the same muzzle brake; the KAS-1 is
    # left out because it moves the left hand (grip_barlight_edited_offset), which the ported clips can't.
    part_choices={
        "stock": [_kastovia(model) for model in (
            "ar_akilo_stock_v0", "ar_akilo74_stock_v0", "sh_vecho_stocktac_v0", "ar_akilo_stockh_v0",
            "ar_akilo_stocktac_v0", "ar_akilo_stocktac02_v0", "ar_akilo_stockwire_v0", "ar_akilo74_stockno_v0",
            "ar_akilo74_stockskel_v0", "lm_rkilo_stock_v0", "lm_rkilo_stockh_v0")],
        "pistol_grip": [_kastovia(model) for model in (
            "ar_akilo_pstlgrp_v0", "sh_vecho_pgrip_v0", "ar_akilo_griptac_v0", "ar_akilo_gripstdy_v0",
            "ar_akilo_gripass_v0", "sh_vecho_gripsnp_v0")],
        # Each holds the fitted magazine (j_mag1) and the reload's fresh one (j_mag2).
        "magazine": [
            ("sm_aviktor_mag_v0",
             "att_wm_p04_sm_aviktor_mag_v0_lod0/att_wm_p04_sm_aviktor_mag_v0_LOD0_SEModelMesh.smd"),
            ("sm_aviktor_xmag_v0", "att_wm_p04_sm_aviktor_xmag_v0_lod0/att_wm_p04_sm_aviktor_xmag_v0_LOD0_zr.smd")],
        "barrel": [
            ("sm_aviktor_barrel_v0", f"{_VITYAZ_BARREL}/att_vm_p04_sm_aviktor_barrel_v0_LOD0.smd"),
            ("sm_aviktor_barlightlong_v0", f"{_VITYAZ_LONG_BARREL}/att_vm_p04_sm_aviktor_barlightlong_v0_LOD0.smd")],
    },
    tip_choices={"long": (f"{_VITYAZ_LONG_BARREL}/barlong_tip.smd",
                          f"{_VITYAZ_LONG_BARREL}/{_VITYAZ_LONG_BARREL}_anims/reference.smd")},
)

def rpk_materials() -> dict[str, str]:
    # Built by rpk_assets.py; the stocks and grips reuse the 74u's materials.
    assets = json.loads((ASSETS / "Weapons" / "RPK" / "rpk_assets.json").read_text(encoding="utf-8"))
    return assets["materials"]


_RPK_BARREL = "att_vm_p04_lm_rkilo_barrel_v0_lod0/att_vm_p04_lm_rkilo_barrel_v0_LOD0"


def _rkilo(model: str, folder: str | None = None) -> tuple[str, str]:
    """A part_choices entry for an RPK attachment model in the RPK's decompile (folder: the decompile's folder)."""
    folder = folder or f"att_vm_p04_{model}"
    return model, f"{folder}/att_vm_p04_{model}_LOD0.smd"


# The RPK light machine gun (7.62x39mm): MWII's RPK (mg_iw9_rkilo) from the same addon as the 74u, on the same rig.
RPK = Weapon(
    name="rpk",
    folder=ASSETS / "Weapons" / "RPK",
    asset="weapons/rpk",
    model="rpk",
    decompiled=DECOMPILED / "rkilo",
    cod_anims="vm_iw9_rkilo/vm_iw9_rkilo_anims",
    vm_meshes=["vm_iw9_rkilo/att_vm_p04_lm_rkilo_rec_v0_LOD0.smd"],
    # The long, heavy barrel with its folding bipod.
    part_meshes=[(f"{_RPK_BARREL}.smd", f"{_RPK_BARREL}.smd"), (f"{_RPK_BARREL}_bipod.smd", f"{_RPK_BARREL}.smd")],
    optional_meshes={
        "muzzle_tip": (f"{_RPK_BARREL}_tip.smd", f"{_RPK_BARREL}.smd"),  # the slant brake
        "optic_rail": ("vm_iw9_rkilo/att_vm_p04_lm_rkilo_rec_v0_mount_LOD0.smd", None),  # side mount on the receiver
        "grip_rail": (f"{_RPK_BARREL}_mount.smd", f"{_RPK_BARREL}.smd"),  # rail under the handguard
    },
    # tag_flash on the barrel.
    extra_bones={"muzzle": ("tag_barrel_attach", np.array([20.063, 0.0, -1.494]))},
    materials=rpk_materials,
    # From the addon's lua/weapons/mg_iw9_rkilo/shared.lua.
    hip=view_offset(),
    aim=view_offset((-0.01, -0.2, 0.003)),
    sprint=view_offset((-0.4, 0.0, -0.1)),
    m4_sprint=True,
    ads_pose=("ads_in", slice(-1, None)),
    report_bones=["tag_tip", "tag_silencer", "tag_grip_attach", "tag_laser_attach", "tag_rail"],
    # The parts the addon offers the RPK (lua/weapons/mg_iw9_rkilo/customization.lua) that a real RPK takes. The
    # factory ones are the RPK's wooden club-foot stock, the AK pistol grip and the 75-round drum; the box magazines are
    # the RPK's own 40-rounder and the AKM's 30. Left out: the 100-round drum and the other barrels (AK barrels, or
    # CoD's heavy barrel, which moves the left hand).
    part_choices={
        "stock": [_kastovia("lm_rkilo_stock_v0"), _kastovia("ar_akilo_stockh_v0"), _rkilo("lm_rkilo_stocktac_v0"),
                  _kastovia("ar_akilo_stockwire_v0"), _kastovia("lm_rkilo_stockh_v0"), _rkilo("lm_rkilo_stockar_v0")],
        "pistol_grip": [_kastovia(model) for model in (
            "ar_akilo_pstlgrp_v0", "sh_vecho_pgrip_v0", "ar_akilo_griptac_v0", "ar_akilo_gripstdy_v0",
            "ar_akilo_gripass_v0", "sh_vecho_gripsnp_v0")],
        # Each holds the fitted magazine (j_mag1) and the reload's fresh one (j_mag2).
        "magazine": [_rkilo("lm_rkilo_mag_v0", "att_vm_p04_lm_rkilo_mag_v0_lod0"),
                     _rkilo("ar_akilo_mag_v0", "easy_att_vm_p04_ar_akilo_mag_v0"),
                     _rkilo("ar_akilo_xmag_v0", "easy_att_vm_p04_ar_akilo_xmag_v0")],
    },
    # The box magazines' reloads: the 30-rounder's (reload_mag) and the 40-rounder's (reload_xmag).
    reload_variants=["_mag", "_xmag"],
)

WEAPONS = {weapon.name: weapon for weapon in (KASTOV_762, KASTOV_74U, VITYAZ, RPK)}


def add_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--weapon", choices=sorted(WEAPONS), default=KASTOV_762.name, help="the gun to build")


def from_command_line(description: str | None = None) -> Weapon:
    """The --weapon of a script with no other arguments."""
    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_argument(parser)
    return WEAPONS[parser.parse_args().weapon]

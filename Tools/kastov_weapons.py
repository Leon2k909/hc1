#!/usr/bin/env python3
"""The guns the Kastov pipeline ports (port_kastov.py, kastov_vmdl.py, kastov_animgraph.py, kastov_prefabs.py).

Each script takes --weapon (default kastov762). The guns are CoD MWII viewmodels decompiled with Crowbar whose rigs
share the v_akm skeleton and clip names (the M16's has the same names on MWII's AR rig, and the P90's and MP7's on
MW2019's), so only their meshes, parts and HC1 asset names differ.
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
class GripFit:
    """Fits HC1's left hand to a handguard CoD's thinner hand grips closer: while the hand holds its idle grip, the
    whole left arm moves by shift (gun axes: forward, left, up, along tag_sling) and each finger joint loses a
    fraction of its bend (fingers, thumb), so the thicker palm and longer fingers don't sink into the handguard."""
    shift: tuple[float, float, float]
    fingers: float = 0.0
    thumb: float = 0.0


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
    # Seconds to bring the sights up (or down): a rifle's, unless the gun is heavier. kastov_prefabs.py writes it to the
    # viewmodel prefab's ViewModel.AimTime, which drives the animgraph's ironsights_weight.
    ads_time: float = 0.25
    # The clip CoD fires with while aiming: the QC's fire sequence blends fire and this one by aim_offset, the MW base's
    # ADS fraction. The port exports it as fire_ads, and the animgraph blends the two by ironsights_weight. None fires
    # with the hip clip while aiming too, which rocks the sights on a gun whose hip clip rolls it (the P90's, 2 degrees
    # about the bore every shot).
    ads_fire: str | None = None
    # Frames of the fire clip to export with the gun and arms held in the idle pose (port_kastov.Kastov.steady_fire):
    # only the gun's moving parts (bolt, trigger, dust cover) and the right hand's fingers play, as in the Kastovs' own
    # clips, which leave the kick to HC1's recoil. None plays the clip as it is, kick and all.
    steady_fire: int | None = None
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
    # Additional choices on an optional group (e.g. a replacement rail's raised/folded iron sights).
    optional_variants: dict[str, list[tuple[str, str, str | None]]] = field(default_factory=dict)
    # Reloads for magazines of another kind than the factory one (the RPK's box magazines): each is a suffix of the CoD
    # clips reload<suffix> and reload_empty<suffix> (or reload<suffix>_empty, as the AK-105's 60-rounder's is named),
    # exported as reload<suffix> and reload_empty<suffix>. The animgraph's reload_variant picks
    # one (0 = the factory reload, then these in order), set from the fitted magazine (GunsmithPart.ReloadAnimation).
    reload_variants: list[str] = field(default_factory=list)
    reload_clip_overrides: dict[str, str] = field(default_factory=dict)
    # The factory magazine's reloads, when they aren't CoD's reload and reload_empty: the suffix of its clips (the AUG's
    # 5.56 magazine reloads with reload_armag and reload_empty_armag; MW2019's AUG is a 9mm gun by default).
    factory_reload: str = ""
    # Moves and opens the left hand where HC1's hand would sink into the handguard (GripFit); None keeps CoD's grip.
    left_grip: GripFit | None = None
    # The left hand's grip on the gun's barrel, when the MW base gives it one (the barrel attachment's
    # SetGripPoseParameter): a delta clip, minus its _corrective_animation, that CoD layers on every clip while the hand
    # holds the handguard. The port adds it with the hand on its idle grip and fades it out like left_grip (GRIP_FADE).
    grip_pose: str | None = None
    # Attachment-model bones the viewmodel rig also has, in another place: the part's own reference pose places them
    # instead, where bone-merge would move them onto the rig's (the M16 barrel's tag_grip_hide, under its rail cover).
    unmerged_bones: frozenset[str] = frozenset()
    # How much bigger CoD's gun is than the real one. MW2019's AUG is 1.1 times the size: its top rail's slots are
    # 0.433 apart and the rail 0.918 wide, where a Picatinny rail's are 0.394 and 0.835 (the P90's and MP7's rails
    # measure that), while its arms are the P90's size. The port shrinks the whole pose about the camera (gun, arms'
    # targets and meshes), so the gun is its real size and the sight picture stays CoD's.
    model_scale: float = 1.0
    # Rig bones read under another name (kastov_smd.BONE_RENAMES): a pistol rig hangs the gun off tag_pistol_offset,
    # which becomes tag_sling, the gun root the pipeline and the prefabs' bone objects go by.
    bone_renames: dict[str, str] = field(default_factory=dict)
    # A pistol's slide lock: CoD's delta clip that holds the slide back while the magazine is empty (the QC's
    # empty_offset layer). The port exports it as empty_delta, and fire_empty (the fire clip with the slide staying
    # back), and the animgraph adds it while b_empty holds.
    slide_lock: str | None = None
    # Rig bones the addon leaves where the real gun has nothing: name -> (parent, local offset), the bone keeping its
    # own turn. MW2019's L86 rig has tag_brass in the handguard, under the bore, where no case could come out.
    moved_bones: dict[str, tuple[str, np.ndarray]] = field(default_factory=dict)
    # Attachment models the MW base draws as a VElement instead of bone-merging them: the model's origin on a rig bone,
    # moved by an offset along the bone's own axes (forward, left, up). path (as written in part_meshes or
    # part_choices) -> (bone, offset). RoN's HK416 fits its Tarkov stocks that way: their vertices sit in the model's
    # own space on an unnamed bone with no parent, which bone-merge has nothing to put on.
    part_mounts: dict[str, tuple[str, np.ndarray]] = field(default_factory=dict)


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
        ("ak47_b_d/iro.smd", "ak47_b_d/ak47_b_d_anims/reference.smd"),
        ("ak47_m_d/76239.smd", "ak47_m_d/ak47_m_d_anims/reference.smd"),
    ],
    optional_meshes={
        "muzzle_tip": ("ak47_b_d/tip.smd", "ak47_b_d/ak47_b_d_anims/reference.smd"),
        "optic_rail": ("ak47_b_d/rail.smd", "ak47_b_d/ak47_b_d_anims/reference.smd"),
        "grip_rail": ("ak47_b_d/grip.smd", "ak47_b_d/ak47_b_d_anims/reference.smd"),
        "laser_rail": ("ak47_b_d/laser.smd", "ak47_b_d/ak47_b_d_anims/reference.smd"),
        "stock_adapter": ("v_akm/st_ada.smd", None),
    },
    part_choices={
        "stock": [
            ("ak47_stock_default", "ak47_s_d/att_rex_vm_ar_akilo_stock_v0_LOD0.smd"),
            ("ak47_stock_adjustable", "ak47_s_ass/att_rex_vm_ar_akilo_stock_ass_v0_LOD0.smd"),
            ("ak47_stock_heavy", "ak47_s_h/att_rex_vm_ar_akilo_stock_hvy_v0_LOD0.smd"),
            ("ak47_stock_padded", "ak47_s_ha/att_rex_wm_ar_akilo_stock_hvy_ass_v0_LOD0.smd"),
            ("ak47_stock_light", "ak47_s_l/att_rex_vm_ar_akilo_stock_lgt_v0_LOD0.smd"),
            ("ak47_stock_delete", "ak47_s_no/att_rex_vm_ar_akilo_stock_no_v0_LOD0.smd"),
            ("ak47_stock_tactical", "ak47_s_t/att_rex_vm_ar_akilo_stock_tac_v0_LOD0.smd"),
        ],
        "pistol_grip": [
            ("ak47_grip_default", "ak47_p_d/att_rex_vm_ar_akilo_pgrip_v0_LOD0.smd"),
            ("ak47_grip_contoured", "ak47_p_a/att_rex_vm_ar_akilo_pgrip_aim_v0_LOD0.smd"),
            ("ak47_grip_textured", "ak47_p_ass/att_rex_vm_ar_akilo_pgrip_ass_v0_LOD0.smd"),
            ("ak47_grip_skeleton", "ak47_p_s/att_rex_vm_ar_akilo_pgrip_skel_v0_LOD0.smd"),
        ],
        "magazine": [
            ("ak47_mag_default", "ak47_m_d/att_rex_vm_ar_akilo_mag_v0_LOD0.smd"),
            ("ak47_mag_polymer", "ak47_m_d1/att_rex_vm_ar_akilo_mag_v04_LOD0.smd"),
            ("ak47_mag_extended", "ak47_m_e1/att_rex_vm_ar_akilo_mag_lrg762s_v0_LOD0.smd"),
            ("ak47_mag_drum", "ak47_m_e2/att_rex_wm_ar_akilo_drum_762s_v0_LOD0.smd"),
        ],
        "barrel": [
            ("ak47_barrel_default", "ak47_b_d/att_rex_vm_ar_akilo_barrel_v0_LOD0.smd"),
            ("ak47_barrel_compact", "ak47_b_s1/att_rex_vm_ar_akilo_bar_lgt_short_v5.smd"),
        ],
    },
    tip_choices={"short": ("ak47_b_s1/tip.smd", "ak47_b_s1/ak47_b_s1_anims/reference.smd")},
    reload_variants=["_xmag", "_dmag"],
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
    # From the addon's lua/weapons/mg_iw9_rkilo/shared.lua, except aim: CoD's ads_in leaves the RPK's camera pitched
    # 0.9 deg up, rolled 2.3 deg and 0.12 left of the bore, which puts the front post 0.8 deg under the aim point. This
    # levels the camera on the front post's top (z 6.31 in the world model; the 762's sits the same way on its post).
    hip=view_offset(),
    aim=view_offset((-0.134, -0.2, -0.037), (-0.887, -0.046, -2.336)),
    sprint=view_offset((-0.4, 0.0, -0.1)),
    m4_sprint=True,
    ads_pose=("ads_in", slice(-1, None)),
    # 6.8 kg with a loaded drum against the AKM's 3.75 kg, much of it out front. There's no measured figure for how long
    # a heavier gun takes to shoulder, so this scales the rifles' 0.25 s by the square root of the moving mass (the gun
    # plus ~4 kg of arms): sqrt(10.8 / 7.75) = 1.18.
    ads_time=0.3,
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
    # The wooden lower handguard's flared sides: where CoD's hand sits, HC1's palm heel and thumb sank 0.39 into it and
    # the fingertips into the far side. Measured by skinning the arms against the gun mesh (visible overlap 108
    # vertices, 0.39 deep -> 22, 0.11; the verified Kastov 762 has 52, 0.10).
    left_grip=GripFit(shift=(0.0, 0.38, -0.1), fingers=0.25, thumb=0.1),
)

def bizon_materials() -> dict[str, str]:
    # Built by bizon_assets.py; the stocks, grips and side rail reuse the 74u's materials.
    assets = json.loads((ASSETS / "Weapons" / "Bizon" / "bizon_assets.json").read_text(encoding="utf-8"))
    return assets["materials"]


_BIZON_BARREL = "att_vm_p04_sm_beta_barrel_v0_lod0/att_vm_p04_sm_beta_barrel_v0_LOD0.smd"
_BIZON_MAG = "att_wm_p04_sm_beta_mag_v0_lod0/att_wm_p04_sm_beta_mag_v0_LOD0.smd"

# The PP-19 Bizon 9x18mm SMG: MWII's "Minibak" (mg_iw9_beta) from the same addon as the 74u, by the Vityaz's author and
# on the same rig. Its 64-round helical magazine runs under the barrel and is the handguard.
BIZON = Weapon(
    name="bizon",
    folder=ASSETS / "Weapons" / "Bizon",
    asset="weapons/bizon",
    model="bizon",
    decompiled=DECOMPILED / "beta",
    cod_anims="v_iw9_beta/v_iw9_beta_anims",
    vm_meshes=["v_iw9_beta/att_vm_p04_sm_beta_rec_v0_LOD0.smd"],
    # The factory barrel and the helical magazine (the fitted one on j_mag1, the reload's fresh one on j_mag2). The
    # addon's other magazines are CoD inventions (a magazine with a grip, joke cans) and its long barrel is CoD's.
    part_meshes=[(_BIZON_BARREL, _BIZON_BARREL), (_BIZON_MAG, _BIZON_MAG)],
    optional_meshes={
        "muzzle_tip": ("att_vm_p04_sm_beta_barrel_v0_lod0/bartip.smd", _BIZON_BARREL),  # the muzzle nut
        # The side-mount rail on the left of the receiver, which the Bizon-2 has for optics.
        "optic_rail": ("v_iw9_beta/att_vm_p04_sm_beta_rec_v0_LOD0_siderail.smd", None),
    },
    # tag_flash on the barrel.
    extra_bones={"muzzle": ("tag_barrel_attach", np.array([7.212, 0.0, -1.397]))},
    materials=bizon_materials,
    # From the addon's lua/weapons/mg_iw9_beta/shared.lua.
    hip=view_offset(),
    aim=view_offset((-0.484, 0.0, -0.187), (0.12, 0.07, -1.0)),
    sprint=view_offset((-0.2, 0.5, 1.7)),
    m4_sprint=True,
    ads_pose=("ads_in", slice(-1, None)),
    report_bones=["tag_tip", "tag_laser_attach", "tag_silencer"],
    # The stocks and pistol grips the addon offers the Bizon (lua/weapons/mg_iw9_beta/customization.lua): Kastovia
    # platform parts, the factory ones the AKS-74U's side-folding stock (the real Bizon's) and the AK pistol grip.
    part_choices={
        "stock": [_kastovia(model) for model in (
            "ar_akilo74_stock_v0", "ar_akilo_stock_v0", "sh_vecho_stocktac_v0", "ar_akilo_stockh_v0",
            "ar_akilo_stocktac_v0", "ar_akilo_stocktac02_v0", "ar_akilo_stockwire_v0", "ar_akilo74_stockno_v0",
            "ar_akilo74_stockskel_v0", "lm_rkilo_stock_v0", "lm_rkilo_stockh_v0")],
        "pistol_grip": [_kastovia(model) for model in (
            "ar_akilo_pstlgrp_v0", "sh_vecho_pgrip_v0", "ar_akilo_griptac_v0", "ar_akilo_gripstdy_v0",
            "ar_akilo_gripass_v0", "sh_vecho_gripsnp_v0")],
    },
)

def ak105_materials() -> dict[str, str]:
    # Built by ak105_assets.py; the muzzle booster, rounds, 20- and 45-round magazines, stocks and grips reuse the 74u's.
    assets = json.loads((ASSETS / "Weapons" / "AK105" / "ak105_assets.json").read_text(encoding="utf-8"))
    return assets["materials"]


_AK105_BARREL = "att_vm_p04_ar_akilo105_barrel_v0/att_vm_p04_ar_akilo105_barrel_v0"
_AK105_BARREL_REFERENCE = "att_vm_p04_ar_akilo105_barrel_v0/att_vm_p04_ar_akilo105_barrel_v0_anims/reference.smd"

# The AK-105 (5.45x39mm): MWII's "Kastov 545" (mg_iw9_akilo105) from the same addon as the 74u, on the same rig. The
# AK-74M's shortened carbine: its receiver, side rail and folding polymer stock, a 314 mm barrel with the AKS-74U's
# muzzle booster.
AK105 = Weapon(
    name="ak105",
    folder=ASSETS / "Weapons" / "AK105",
    asset="weapons/ak105",
    model="ak105",
    decompiled=DECOMPILED / "akilo105",
    cod_anims="vm_iw9_akilo105_anims",
    vm_meshes=["att_vm_p04_ar_akilo105_rec_v0_LOD0_edited.smd"],
    part_meshes=[(f"{_AK105_BARREL}_LOD0.smd", _AK105_BARREL_REFERENCE)],
    optional_meshes={
        "muzzle_tip": (f"{_AK105_BARREL}_tip.smd", _AK105_BARREL_REFERENCE),  # the muzzle booster
        "optic_rail": ("att_vm_p04_ar_akilo105_rec_v0_mount.smd", None),  # the optic mount on the side rail
        # The folding stock's hinge, which the fixed wooden stocks replace (their lua sets tag_stock_hinge = 1).
        "stock_hinge": ("att_vm_p04_ar_akilo105_rec_v0_LOD0_stock_hinge.smd", None),
    },
    # 0.2 inside the front of the muzzle booster, like the 74u's (the barrel's tag_flash_attachment is 1.7 inside it).
    extra_bones={"muzzle": ("tag_barrel_attach", np.array([12.477, 0.0, -1.497]))},
    materials=ak105_materials,
    # From the addon's lua/weapons/mg_iw9_akilo105/shared.lua.
    hip=view_offset(),
    aim=view_offset((-0.008, 0.0, -0.005)),
    sprint=view_offset(),
    m4_sprint=True,
    ads_pose=("ads_in", slice(-1, None)),
    report_bones=["tag_rail", "tag_tip", "tag_silencer", "tag_grip_attach", "tag_laser_attach"],
    # The parts the addon offers the AK-105 (lua/weapons/mg_iw9_akilo105/customization.lua): its own AK-74M-style
    # folding stock, pistol grip and 30-round magazine, the Kastovia stocks and grips, and the 20-, 45- (RPK-74) and
    # 60-round (quad-stack casket) magazines. Left out: the akilo74 magazine (the 30-rounder's look, CoD cosmetic) and the
    # other barrels, which are CoD's own.
    part_choices={
        "stock": [_attachment("ar_akilo105_stock_v0")] + [_kastovia(model) for model in (
            "sh_vecho_stock_v0", "sh_vecho_stocktac_v0", "ar_akilo_stockh_v0", "ar_akilo_stocktac_v0",
            "ar_akilo_stocktac02_v0", "ar_akilo_stockwire_v0", "ar_akilo74_stockskel_v0", "lm_rkilo_stock_v0",
            "lm_rkilo_stockh_v0", "ar_akilo_stock_v0")],
        "pistol_grip": [_attachment("ar_akilo105_pgrip_v0")] + [_kastovia(model) for model in (
            "sh_vecho_pgrip_v0", "ar_akilo_griptac_v0", "ar_akilo_gripstdy_v0", "ar_akilo_gripass_v0",
            "sh_vecho_gripsnp_v0", "ar_akilo_pstlgrp_v0")],
        # Each holds the fitted magazine (j_mag1) and the reload's fresh one (j_mag2).
        "magazine": [_attachment("ar_akilo105_mag_v0"), _kastovia("ar_akilo105_smag_v0"),
                     _kastovia("ar_akilo105_xmag_v0"), _attachment("ar_akilo105_xmaglrg_v0")],
    },
    # Each other magazine reloads with its own animation (the addon's magazines swap Reload for these).
    reload_variants=["_smag", "_xmag", "_xmaglrg"],
    # The factory barrel's (att_vm_p04_ar_akilo105_barrel_v0.lua: grip_pose_l_offset).
    grip_pose="a_delta_barhvyshort_additive_for_offset",
)

def vepr12_materials() -> dict[str, str]:
    # Built by vepr12_assets.py; the stocks and grips reuse the 74u's materials.
    assets = json.loads((ASSETS / "Weapons" / "Vepr12" / "vepr12_assets.json").read_text(encoding="utf-8"))
    return assets["materials"]


_VEPR12_BARREL = "att_vm_p04_sh_vecho_barrel_v0/att_vm_p04_sh_vecho_barrel_v0"
_VEPR12_BARREL_REFERENCE = "att_vm_p04_sh_vecho_barrel_v0/att_vm_p04_sh_vecho_barrel_v0_anims/reference.smd"
_VEPR12_COVER = "att_vm_p04_sh_vecho_bolt_v0/att_vm_p04_sh_vecho_bolt_v0"


def _vecho_mag(model: str) -> tuple[str, str]:
    """A magazine part_choices entry: the Vepr's magazines are world models (att_wm_p04_<model>)."""
    folder = f"att_wm_p04_{model}"
    return model, f"{folder}/{folder}_LOD0.smd"


# The Vepr-12 (12 gauge): MWII's "KV Broadside" (mg_iw9_vecho) from the same addon as the 74u, on the same rig. Molot's
# semi-automatic shotgun on the RPK receiver, here the short VPO-205-03 (its barrel measures ~305 mm in the model).
VEPR12 = Weapon(
    name="vepr12",
    folder=ASSETS / "Weapons" / "Vepr12",
    asset="weapons/vepr12",
    model="vepr12",
    decompiled=DECOMPILED / "vecho",
    cod_anims="v_vecho_anims",
    vm_meshes=["att_vm_p04_sh_vecho_rec_v0_LOD0.smd"],
    # The barrel with its handguard, gas block and front sight, and the railed dust cover (the addon's "bolt").
    part_meshes=[(f"{_VEPR12_BARREL}_LOD0.smd", _VEPR12_BARREL_REFERENCE),
                 (f"{_VEPR12_COVER}_LOD0.smd", f"att_vm_p04_sh_vecho_bolt_v0/att_vm_p04_sh_vecho_bolt_v0_anims/reference.smd")],
    optional_meshes={
        "muzzle_tip": (f"{_VEPR12_BARREL}_tip.smd", _VEPR12_BARREL_REFERENCE),  # the muzzle brake
        "laser_rail": (f"{_VEPR12_BARREL}_laser.smd", _VEPR12_BARREL_REFERENCE),  # side rail on the handguard
    },
    # 0.2 inside the front of the muzzle brake, like the AK-105's (the barrel's tag_flash is 0.8 inside it).
    extra_bones={"muzzle": ("tag_barrel_attach", np.array([10.877, 0.0, -1.489]))},
    materials=vepr12_materials,
    # From the addon's lua/weapons/mg_iw9_vecho/shared.lua.
    hip=view_offset(),
    aim=view_offset(angles=(0.0, 0.03, 0.0)),
    sprint=view_offset((3.0, -0.7, -0.8)),
    m4_sprint=True,
    ads_pose=("ads_in", slice(-1, None)),
    # 4.8 kg loaded (4.2 kg, the 8-round magazine and eight shells) against the AKM's 3.75 kg: the RPK's scaling,
    # sqrt(8.8 / 7.75) = 1.07.
    ads_time=0.27,
    report_bones=["tag_tip", "tag_laser_attach", "tag_grip_attach", "tag_rail_attach"],
    # The parts the addon offers the Vepr (lua/weapons/mg_iw9_vecho/customization.lua) that a real Vepr-12 takes: the
    # Kastovia stocks and grips (the factory ones are the addon's, the Vepr's own), and its 8-, 12- and 25-round
    # magazines. Left out: CoD's barrels, bolts and conversions, and the grips and launcher that move the left hand.
    part_choices={
        "stock": [_kastovia(model) for model in (
            "sh_vecho_stock_v0", "sh_vecho_stocktac_v0", "ar_akilo_stock_v0", "ar_akilo_stockh_v0",
            "ar_akilo_stocktac_v0", "ar_akilo_stocktac02_v0", "ar_akilo_stockwire_v0", "ar_akilo74_stock_v0",
            "ar_akilo74_stockno_v0", "ar_akilo74_stockskel_v0", "lm_rkilo_stock_v0", "lm_rkilo_stockh_v0")],
        "pistol_grip": [_kastovia(model) for model in (
            "sh_vecho_pgrip_v0", "ar_akilo_pstlgrp_v0", "ar_akilo_griptac_v0", "ar_akilo_gripstdy_v0",
            "ar_akilo_gripass_v0", "sh_vecho_gripsnp_v0")],
        # Each holds the fitted magazine (j_mag1) and the reload's fresh one (j_mag2).
        "magazine": [_vecho_mag(model) for model in ("sh_vecho_mag_v0", "sh_vecho_xmag_v0", "sh_vecho_drummag_v0")],
    },
    # The 12-round magazine's and the drum's own reloads.
    reload_variants=["_xmag", "_drummag"],
)

def m16_materials() -> dict[str, str]:
    # Built by m16_assets.py.
    assets = json.loads((ASSETS / "Weapons" / "M16" / "m16_assets.json").read_text(encoding="utf-8"))
    return assets["materials"]


_M16_BARREL = "att_vm_p01_ar_mike16_barrel_v0"
_M16_BARREL_REFERENCE = f"{_M16_BARREL}/{_M16_BARREL}_anims/reference.smd"
_M16_MAG = "att_vm_p01_ar_mike4_mag_v0"

# The M16A4 (5.56x45mm): MWII's M16 (mg_iw9_mike16) from easy4115's addon (Workshop 2962304029). MWII's AR rig has the
# same bone and clip names as the Kastovia ones, except that j_gun hangs off tag_sling. A flat-top upper under the
# detachable carry handle (with the A2 rear sight), the 20" barrel with its fixed front sight base, the handguard and
# the birdcage flash hider, the fixed A2 stock, and MWII's M4 pistol grip and 30-round magazine, which the addon fits.
M16 = Weapon(
    name="m16",
    folder=ASSETS / "Weapons" / "M16",
    asset="weapons/m16",
    model="m16",
    decompiled=DECOMPILED / "mike16",
    cod_anims="vm_iw9_mike16_anims",
    vm_meshes=["att_vm_p01_ar_mike16_rec_v0_LOD0.smd"],
    # The barrel's handguard (a four-rail one, as the real M16A4's) and front sight are its "handguard" and "sight"
    # bodygroups; the addon's other handguard (a grenade launcher's heat shield) and its second laser rail (the same
    # mesh) are left out. The magazine has a see-through window, so both magazines (the fitted one and the reload's
    # fresh one) keep all their rounds; j_ammo_31 is a loose round the clips move, parked inside the receiver.
    part_meshes=[],
    optional_meshes={
        "muzzle_tip": (f"{_M16_BARREL}/tip.smd", _M16_BARREL_REFERENCE),  # the birdcage flash hider
        "laser_rail": (f"{_M16_BARREL}/laser.smd", _M16_BARREL_REFERENCE),  # rail section on the handguard's side
        # The ladder cover on the front of the bottom rail (the barrel's tag_grip_hide), which comes off for a grip.
        "grip_cover": (f"{_M16_BARREL}/guard.smd#tag_grip_hide", _M16_BARREL_REFERENCE),
        # The carry handle, with the rear sight: it comes off for an optic, as the real flat-top's does.
        "carry_handle": ("carryhandle.smd", None),
        "factory_barrel": (f"{_M16_BARREL}/{_M16_BARREL}_LOD0.smd", _M16_BARREL_REFERENCE),
        "factory_handguard": (f"{_M16_BARREL}/guard.smd#!tag_grip_hide", _M16_BARREL_REFERENCE),
        "factory_front_sight": (f"{_M16_BARREL}/sighton.smd", _M16_BARREL_REFERENCE),
        "factory_stock": ("att_vm_p01_ar_mike16_stock_v0/att_vm_p01_ar_mike16_stock_v0_LOD0.smd",
                          "att_vm_p01_ar_mike16_stock_v0/att_vm_p01_ar_mike16_stock_v0_anims/reference.smd"),
        "factory_grip": ("att_vm_p01_ar_mike4_pistolgrip_v0/att_vm_p01_ar_mike4_pistolgrip_v0_LOD0.smd",
                         "att_vm_p01_ar_mike4_pistolgrip_v0/att_vm_p01_ar_mike4_pistolgrip_v0_anims/reference.smd"),
    },
    optional_variants={"laser_rail": [("replaced", "", None)]},
    # m16_gunsmith.py assembles the shells and rounds on both animated magazine bones.
    part_choices={"magazine": [(name, f"derived/mag_{name}.smd") for name in ("standard", "smag", "xmag", "xmaglrg")]},
    reload_variants=["_smag", "_xmag", "_xmaglrg"],
    # 0.2 inside the front of the flash hider, like the AK-105's (the barrel's tag_flash_attachment is 0.57 inside it).
    extra_bones={"muzzle": ("tag_barrel_attach", np.array([21.35, 0.0, -1.202]))},
    materials=m16_materials,
    # From the addon's lua/weapons/mg_iw9_mike16/shared.lua, except aim. The addon's iron-sight aim (0.005, 0.5, 0.135)
    # leaves the sight line 0.113 above the camera, with the front post 0.32 deg over the aim point, low in the rear
    # aperture. This drops the gun onto the line through the aperture's centre and the post's top, and turns out the
    # line's 0.058 deg up and 0.032 deg left, which puts both on the aim point (measured on ads_in's last frame).
    hip=view_offset(),
    aim=view_offset((0.004, 0.5, 0.022), (0.058, -0.032, 0.0)),
    sprint=view_offset(),
    m4_sprint=True,
    ads_pose=("ads_in", slice(-1, None)),
    report_bones=["tag_rail", "tag_tip", "tag_silencer", "tag_grip_attach", "tag_laser_attach", "tag_sight_on",
                  "tag_sight_on2"],
    # The mid-length heavy barrel's grip (the QC's grip_barmidhvy_offset), which wraps the thick four-rail handguard: at
    # idle 121 left-hand vertices are inside it, at most 0.09 deep, and 553 are within 0.25 of it. The factory barrel's
    # own, with no grip fitted (att_vm_p01_ar_mike16_barrel_v0.lua: grip_vertpro_offset, which plays the vertshort
    # clip), holds a short vertical grip: the hand closed on air 2.3 under the handguard, and only 117 vertices came
    # within 0.25 of it. With no grip clip the fingertips rise to the front sight when aiming.
    grip_pose="a_delta_grip_barmidhvy_additive_for_offset",
    # The addon's fire clip rocks the whole gun 0.2 sideways each way and 2.5 deg about the bore, settling over 1.4 s,
    # and every shot starts it again. The bolt, dust cover, trigger and trigger finger are still by frame 12.
    steady_fire=15,
    # The rig's tag_grip_hide is 5.7 further back and 1.7 higher than the barrel's, which would lift the rail cover off
    # the bottom rail into the handguard.
    unmerged_bones=frozenset({"tag_grip_hide"}),
)

def p90_materials() -> dict[str, str]:
    # Built by p90_assets.py.
    assets = json.loads((ASSETS / "Weapons" / "P90" / "p90_assets.json").read_text(encoding="utf-8"))
    return assets["materials"]


_P90 = "v_papa90"
_P90_BARREL = "attachment_vm_sm_papa90_barrel/attachment_vm_sm_papa90_barrel"
_P90_MAG = "attachment_vm_sm_papa90_mag/attachment_vm_sm_papa90_mag.smd"

# The FN P90 (5.7x28mm): MW2019's P90 (mg_papa90) from Viper's MW2019 SMG pack (Workshop 2802430252). MW2019's rig has
# the same bone and clip names as MWII's, but the P90 has no pistol grip part, so tag_pistolgrip_attach (which places
# the world model) is an extra bone. The P90 TR: the top rail with its flip-up iron sights, the barrel with its flash
# hider, and the 50-round magazine along the top, see-through like the real one.
P90 = Weapon(
    name="p90",
    folder=ASSETS / "Weapons" / "P90",
    asset="weapons/p90",
    model="p90",
    decompiled=DECOMPILED / "papa90",
    cod_anims=f"{_P90}/{_P90}_anims",
    # The viewmodel's own bodygroup meshes, in its bind pose: the receiver (with the side rails) and the top rail.
    vm_meshes=[f"{_P90}/attachment_vm_sm_papa90_receiver.smd", f"{_P90}/attachment_vm_sm_papa90_rail_hide.smd"],
    # The barrel, and the magazine: the fitted one (j_mag1) and the reload's fresh one (j_mag2), then their see-through
    # shells.
    part_meshes=[(f"{_P90_BARREL}.smd", f"{_P90_BARREL}.smd"), (_P90_MAG, _P90_MAG),
                 ("attachment_vm_sm_papa90_mag/body1_model0.smd", _P90_MAG)],
    optional_meshes={
        "muzzle_tip": (f"{_P90_BARREL}_tip.smd", f"{_P90_BARREL}.smd"),  # the flash hider
        # The flip-up sights on the top rail, which an optic takes the place of.
        "iron_sights": (f"{_P90}/attachment_vm_sm_papa90_tag_sight.smd", None),
    },
    extra_bones={
        # 0.2 inside the front of the flash hider, on the bore (the barrel's tag_flash_attachment is 1.0 inside it and
        # 0.155 under the bore).
        "muzzle": ("tag_barrel_attach", np.array([2.0, 0.0, 0.155])),
        # Where the rifles' pistol grip mounts sit from the right wrist: 4.2 in front of it and 2.3 above, on the
        # centreline.
        "tag_pistolgrip_attach": ("tag_sling", np.array([8.59, 0.0, 0.93])),
    },
    materials=p90_materials,
    # From the addon's lua/weapons/mg_papa90/shared.lua. With aim, ads_in's end puts the front post's tip on the aim
    # point, centred between the rear sight's shoulders.
    hip=view_offset(),
    aim=view_offset((0.0, -4.0, 0.0)),
    sprint=view_offset(),
    m4_sprint=True,
    ads_pose=("ads_in", slice(-1, None)),
    ads_fire="fire_2",
    report_bones=["tag_tip", "tag_silencer", "tag_laser_attach", "tag_rail_attach", "tag_sight_on"],
)

def mp7_materials() -> dict[str, str]:
    # Built by mp7_assets.py.
    assets = json.loads((ASSETS / "Weapons" / "MP7" / "mp7_assets.json").read_text(encoding="utf-8"))
    return assets["materials"]


_MP7 = "v_mpapa7"
_MP7_BARREL = "attachment_vm_sm_mpapa7_barrel/attachment_vm_sm_mpapa7_barrel"
_MP7_MAG = "attachment_vm_sm_mpapa7_mag/attachment_vm_sm_mpapa7_mag.smd"
_MP7_STOCK = "attachment_vm_sm_mpapa7_stock/attachment_vm_sm_mpapa7_stock.smd"

# The H&K MP7A1 (4.6x30mm): MW2019's MP7 (mg_mpapa7) from Viper's MW2019 SMG pack (Workshop 2802430252). Like the
# P90, it has no pistol grip part (the grip is the receiver's), so tag_pistolgrip_attach is an extra bone. The receiver
# with its rails, the barrel with its flash hider, the flip-up iron sights, the 40-round magazine and the retractable
# stock.
MP7 = Weapon(
    name="mp7",
    folder=ASSETS / "Weapons" / "MP7",
    asset="weapons/mp7",
    model="mp7",
    decompiled=DECOMPILED / "mpapa7",
    cod_anims=f"{_MP7}/{_MP7}_anims",
    # The viewmodel's own bodygroup mesh, in its bind pose.
    vm_meshes=[f"{_MP7}/attachment_vm_sm_mpapa7_receiver.smd"],
    # The barrel, the magazine (the fitted one on j_mag1 and the reload's fresh one on j_mag2) and the stock.
    part_meshes=[(f"{_MP7_BARREL}.smd", f"{_MP7_BARREL}.smd"), (_MP7_MAG, _MP7_MAG), (_MP7_STOCK, _MP7_STOCK)],
    optional_meshes={
        "muzzle_tip": (f"{_MP7_BARREL}_tip.smd", f"{_MP7_BARREL}.smd"),  # the flash hider
        # The raised flip-up sights, which come off for an optic (MW2019's magnified optics take them off too).
        "iron_sights": (f"{_MP7}/attachment_vm_sm_mpapa7_tag_sight_on.smd", None),
        # The laser's mount on the right-hand rail, shown only under a laser. The rail CoD adds under the front
        # (attachment_vm_sm_mpapa7_ub_rail) is left out: the real MP7A1 has none, and the left hand holds the receiver
        # there, so the gun has no Underbarrel slot.
        "laser_rail": (f"{_MP7}/attachment_vm_sm_mpapa7_tag_laser.smd", None),
    },
    extra_bones={
        # 0.2 inside the front of the flash hider, on the bore (the barrel's tag_flash_attachment is 0.255 inside it).
        "muzzle": ("tag_barrel_attach", np.array([3.882, 0.0, 0.721])),
        # Where the rifles' pistol grip mounts sit from the right wrist (as for the P90), on the centreline.
        "tag_pistolgrip_attach": ("tag_sling", np.array([6.42, 0.0, -1.64])),
    },
    materials=mp7_materials,
    # From the addon's lua/weapons/mg_mpapa7/shared.lua.
    hip=view_offset(),
    aim=view_offset((0.0, 3.0, 0.0)),
    sprint=view_offset(),
    m4_sprint=True,
    ads_pose=("ads_in", slice(-1, None)),
    # The hip clip rolls the gun 2.3 degrees every shot; the aimed one only kicks it 0.7 back along the bore.
    ads_fire="fire_2",
    report_bones=["tag_tip", "tag_silencer", "tag_laser_attach", "tag_laser_show", "tag_grip_attach", "tag_rail_attach",
                  "tag_sight_on"],
)

def aug_materials() -> dict[str, str]:
    # Built by aug_assets.py.
    assets = json.loads((ASSETS / "Weapons" / "AUG" / "aug_assets.json").read_text(encoding="utf-8"))
    return assets["materials"]


_AUG = "v_augolf"
_AUG_BARREL = "attachment_vm_sm_augolf_arbarrel/attachment_vm_sm_augolf_arbarrel"
_AUG_MAG = "attachment_vm_sm_augolf_armag/attachment_vm_sm_augolf_armag.smd"
_AUG_LONG = "attachment_vm_sm_augolf_lmgbarrel/attachment_vm_sm_augolf_lmgbarrel"


def _aug_part(name: str) -> str:
    return f"attachment_vm_sm_augolf_{name}/attachment_vm_sm_augolf_{name}.smd"

# The Steyr AUG A3 (5.56x45mm): MW2019's AUG (mg_augolf) from Viper's MW2019 SMG pack (Workshop 2802430252), which is a
# 9mm gun by default. Built as the 5.56 rifle: the pack's 407 mm barrel and the AUG's own 30-round magazine, which
# reloads with its own clips (factory_reload). Like the P90's and MP7's, its pistol grip is the stock's, so
# tag_pistolgrip_attach is an extra bone.
AUG = Weapon(
    name="aug",
    folder=ASSETS / "Weapons" / "AUG",
    asset="weapons/aug",
    model="aug",
    decompiled=DECOMPILED / "augolf",
    cod_anims=f"{_AUG}/{_AUG}_anims",
    # The viewmodel's own bodygroup meshes, in its bind pose: the stock (the receiver housing with the pistol grip and
    # trigger guard), its butt, the top rail and the folding foregrip. The foregrip's mesh carries a second copy of it
    # in the rail's material, whose UVs don't fit that texture.
    vm_meshes=[f"{_AUG}/weapon_vm_sm_augolf_receiver.smd",
               f"{_AUG}/weapon_vm_sm_augolf_rail_1.smd",
               f"{_AUG}/weapon_vm_sm_augolf_tag_grip.smd@weapon_vm_sm_augolf_vertgrip"],
    # The barrel (without the _s copies of its pieces, which have no material of their own) and the magazine: the
    # fitted one on j_mag1 and the reload's fresh one on j_mag2.
    part_meshes=[],
    part_choices={
        "stock": [("factory", _aug_part("tag_stock_attach")),
                  ("lightweight", _aug_part("stockl")), ("tactical", _aug_part("stock_tactical"))],
        "barrel": [("factory", f"{_AUG_BARREL}.smd@!weapon_vm_sm_augolf_ar_barrel_s,weapon_vm_sm_augolf_lmg_barrel_s"),
                   ("long", f"{_AUG_LONG}.smd")],
        "magazine": [("factory", _AUG_MAG),
                     # The decorative decal mesh is omitted; the drum keeps its own PBR surface.
                     ("drum", _aug_part("drummag") + "@!weapon_vm_sm_augolf_lmg_mag_decal")],
    },
    tip_choices={"long": (f"{_AUG_LONG}_tip.smd", f"{_AUG_LONG}.smd")},
    reload_variants=["_drummag"],
    optional_meshes={
        "muzzle_tip": (f"{_AUG_BARREL}_tip.smd", f"{_AUG_BARREL}.smd"),  # the flash hider
        # The flip-up sights on the top rail, which an optic takes the place of.
        "iron_sights": (f"{_AUG}/weapon_vm_sm_augolf_tag_sight_1.smd", None),
        # The laser's mount on the barrel, shown only under a laser.
        "laser_rail": (f"{_AUG_BARREL}_laser.smd", f"{_AUG_BARREL}.smd"),
    },
    extra_bones={
        # 0.2 inside the front of the flash hider, on the bore (the barrel's tag_flash_attachment is 1.4 inside it).
        "muzzle": ("tag_barrel_attach", np.array([7.996, 0.0, 0.006])),
        # Where the rifles' pistol grip mounts sit from the right wrist (as for the P90), on the centreline, which is
        # 1.174 right of tag_sling: 4.2 in front of the wrist and 2.3 above it, in HC1's lengths (these offsets are
        # CoD's, which model_scale shrinks).
        "tag_pistolgrip_attach": ("tag_sling", np.array([16.397, -1.174, 0.525])),
    },
    materials=aug_materials,
    # From the addon's lua/weapons/mg_augolf/shared.lua.
    hip=view_offset(),
    aim=view_offset((0.0, 3.0, 0.0)),
    sprint=view_offset(),
    m4_sprint=True,
    ads_pose=("ads_in", slice(-1, None)),
    # The hip clip rolls the gun 4.6 degrees about the bore on the shot's first frame and rocks it +-2.6 for the next
    # five; the aimed one rolls it 0.56 at most and kicks it 0.94 straight back.
    ads_fire="fire_2",
    factory_reload="_armag",
    report_bones=["tag_tip", "tag_silencer", "tag_laser_attach", "tag_laser_show", "tag_grip_attach", "tag_rail_attach",
                  "tag_sight_on"],
    model_scale=1.1,
)

def uzi_materials() -> dict[str, str]:
    # Built by uzi_assets.py.
    assets = json.loads((ASSETS / "Weapons" / "Uzi" / "uzi_assets.json").read_text(encoding="utf-8"))
    return assets["materials"]


_UZI = "v_uzulu"
_UZI_BARREL = "attachment_vm_sm_uzulu_barrel/attachment_vm_sm_uzulu_barrel.smd"
# The receiver model the MW base bone-merges onto the viewmodel, for its bodygroup pieces.
_UZI_PIECES = "attachment_vm_sm_uzulu_receiver"
_UZI_PIECES_REFERENCE = f"{_UZI_PIECES}/attachment_vm_sm_uzulu_receiver.smd"


def _uzulu(model: str) -> tuple[str, str]:
    """A part_choices entry: one of the Uzi's attachment models (attachment_vm_sm_uzulu_<model>)."""
    folder = f"attachment_vm_sm_uzulu_{model}"
    return f"sm_uzulu_{model}", f"{folder}/{folder}.smd"


# The IMI Uzi (9x19mm): MW2019's Uzi (mg_uzulu) from Viper's MW2019 SMG pack (Workshop 2802430252). Like the P90's and
# MP7's, its pistol grip is the receiver's, so tag_pistolgrip_attach is an extra bone. The receiver with its barrel nut,
# the short barrel, the sights, the 32-round magazine and the folding metal stock. It's the real gun's size: from the
# receiver's back to the muzzle it measures 435 mm, the real gun's 445 without a stock.
UZI = Weapon(
    name="uzi",
    folder=ASSETS / "Weapons" / "Uzi",
    asset="weapons/uzi",
    model="uzi",
    decompiled=DECOMPILED / "uzulu",
    cod_anims=f"{_UZI}/{_UZI}_anims",
    # The viewmodel's own receiver mesh, in its bind pose, without the _s copies of its pieces (it has every piece
    # twice, the second copy in an _s material).
    vm_meshes=[f"{_UZI}/attachment_vm_sm_uzulu_receiver.smd@!weapon_vm_sm_uzulu_body_s,weapon_vm_sm_uzulu_frontgrip_s,"
               "weapon_vm_sm_uzulu_pstl_grip_s,weapon_vm_sm_uzulu_barrel_s"],
    # The barrel, and the front and rear sights (the receiver model's one-choice "sight" bodygroup).
    part_meshes=[(_UZI_BARREL, _UZI_BARREL), (f"{_UZI_PIECES}/attachment_vm_sm_uzulu_tag_sight.smd", _UZI_PIECES_REFERENCE)],
    optional_meshes={
        # The mount an optic brings onto the top cover (tag_rail), and the laser's on the receiver's right side.
        "optic_rail": (f"{_UZI_PIECES}/attachment_vm_sm_uzulu_rail.smd", _UZI_PIECES_REFERENCE),
        "laser_rail": (f"{_UZI_PIECES}/attachment_vm_sm_uzulu_receiver_laser.smd", _UZI_PIECES_REFERENCE),
    },
    extra_bones={
        # 0.2 inside the barrel's end, on the bore (the barrel's tag_flash_attachment is at its end).
        "muzzle": ("tag_barrel_attach", np.array([4.121, 0.0, 0.0])),
        # Where the rifles' pistol grip mounts sit from the right wrist (as for the P90), on the centreline, which is
        # 0.937 right of tag_sling.
        "tag_pistolgrip_attach": ("tag_sling", np.array([-1.31, -0.937, -1.51])),
    },
    materials=uzi_materials,
    # From the addon's lua/weapons/mg_uzulu/shared.lua.
    hip=view_offset(),
    aim=view_offset((0.0, 3.0, 0.0)),
    sprint=view_offset(),
    m4_sprint=True,
    ads_pose=("ads_in", slice(-1, None)),
    # The fire clip rolls the gun up to 1.5 degrees about the bore and pitches it 0.9 in its first three frames, and at
    # 600 rpm every shot starts it again; the aimed clip (fire_2) still rolls it 0.95. The bolt (seen through the
    # ejection port; the cocking knob on the top cover doesn't reciprocate, as on the real gun) and the trigger finger
    # are still by frame 5.
    steady_fire=8,
    report_bones=["tag_silencer", "tag_laser_attach", "tag_laser_show", "tag_rail", "tag_sight_on", "tag_stock_show"],
    # The folding metal stock (extended), folded, and the early fixed wooden stock; the 32-round magazine, then the 40
    # and the 50. Left out: CoD's barrels, its suppressed barrel and calibre conversion, the MW grips and stocks.
    part_choices={
        "stock": [_uzulu("stock"), _uzulu("stock_folded"), _uzulu("stockh")],
        # Each holds the fitted magazine (j_mag1) and the reload's fresh one (j_mag2).
        "magazine": [_uzulu("mag"), _uzulu("xmags"), _uzulu("xmag2")],
    },
    # Both longer magazines reload with the xmag clips, as in the addon.
    reload_variants=["_xmag"],
    # The lower receiver's front: where CoD's hand sits, HC1's thumb base sank 0.34 into its left side, the palm into
    # its bottom and the fingertips into its right side. Measured by skinning the arms against the gun mesh (154
    # vertices, 0.34 deep -> 60, 0.10; the verified Kastov 762 has 52, 0.10).
    left_grip=GripFit(shift=(0.0, 0.25, -0.1), fingers=0.1),
)

def fal_materials() -> dict[str, str]:
    # Built by fal_assets.py.
    assets = json.loads((ASSETS / "Weapons" / "FAL" / "fal_assets.json").read_text(encoding="utf-8"))
    return assets["materials"]


_FAL = "v_falima"
_FAL_BARREL = "attachment_vm_ar_falima_barrel/attachment_vm_ar_falima_barrel"
_FAL_SHORT = "attachment_vm_ar_falima_barsmg/attachment_vm_ar_falima_barsmg"
_FAL_FOREND = "attachment_vm_ar_falima_forend/attachment_vm_ar_falima_forend"
_FAL_MAG = "attachment_vm_ar_falima_mag/attachment_vm_ar_falima_mag.smd"
_FAL_STOCK = "attachment_vm_ar_falima_stock/attachment_vm_ar_falima_stock.smd"
# The receiver model the MW base bone-merges onto the viewmodel, for its bodygroup pieces.
_FAL_PIECES = "attachment_vm_ar_falima_reciever"
_FAL_PIECES_REFERENCE = f"{_FAL_PIECES}/attachment_vm_ar_falima_reciever.smd"


def _falima(model: str) -> str:
    """One of the FAL's attachment models (attachment_vm_ar_falima_<model>)."""
    return f"attachment_vm_ar_falima_{model}/attachment_vm_ar_falima_{model}.smd"


# The FN FAL (7.62x51mm): MW2019's FAL (mg_falima) from Viper's MW2019 Assault Rifles pack (Workshop 2528829149), the
# 50.00 rifle: the 533 mm barrel with its flash hider, the handguard with the gas block and front sight, the 20-round
# magazine and the fixed stock. Like the P90's, its rig has no pistol grip part (the grip is the receiver's), so
# tag_pistolgrip_attach is an extra bone. It's the real gun's size: 42.9 in from the butt to the muzzle, the real
# 50.00's 1,090 mm. The gunsmith's parts are the pack's real FAL ones: the Para's tubular folding stock, the 18-inch
# barrel of the folding-stock 50.62 (with a short flash hider) and the 30-round magazine.
FAL = Weapon(
    name="fal",
    folder=ASSETS / "Weapons" / "FAL",
    asset="weapons/fal",
    model="fal",
    decompiled=DECOMPILED / "falima",
    cod_anims=f"{_FAL}/{_FAL}_anims",
    # The viewmodel's own receiver mesh, in its bind pose.
    vm_meshes=[f"{_FAL}/attachment_vm_ar_falima_reciever.smd"],
    # The handguard, with the gas block and the front sight.
    part_meshes=[(f"{_FAL_FOREND}.smd", f"{_FAL_FOREND}.smd")],
    # The stock, the barrel ahead of the gas block and the magazine (the fitted one on j_mag1 and the reload's fresh one
    # on j_mag2), each the 50.00's then the gunsmith's. Left out: the pack's long barrel (1.64 longer than the 50.00's,
    # ~575 mm, which no service FAL had: 533, the SLR's 554, 458 and 436) and its loose muzzle piece, which the addon
    # never fits, its 24-round magazine (no FAL magazine holds 24), the receiver with no stock, MW's generic stocks, and
    # the FAL's grips, which move the left hand (a part can't).
    part_choices={
        "stock": [("factory", _FAL_STOCK), ("para", _falima("stockl"))],
        "barrel": [("factory", f"{_FAL_BARREL}.smd"), ("short", f"{_FAL_SHORT}.smd")],
        "magazine": [("factory", _FAL_MAG), ("xmag", _falima("xmags"))],
    },
    # The 18-inch barrel's short flash hider: muzzle_tip 1, between the factory one and none.
    tip_choices={"short": (f"{_FAL_SHORT}_tip.smd", f"{_FAL_SHORT}.smd")},
    # The 30-round magazine reloads with its own clips.
    reload_variants=["_xmag"],
    optional_meshes={
        "muzzle_tip": (f"{_FAL_BARREL}_tip.smd", f"{_FAL_BARREL}.smd"),  # the flash hider
        # The rail an optic brings onto the top cover.
        "optic_rail": (f"{_FAL_PIECES}/attachment_vm_ar_falima_rail.smd", _FAL_PIECES_REFERENCE),
        # The laser's mount on the handguard's right side, shown only under a laser.
        "laser_rail": (f"{_FAL_FOREND}_laser.smd", f"{_FAL_FOREND}.smd"),
        # The rear sight, raised, and folded down under an optic (the receiver model's tag_sight bodygroup).
        "iron_sights": (f"{_FAL_PIECES}/attachment_vm_ar_falima_tag_sight_on.smd", _FAL_PIECES_REFERENCE),
        "sight_folded": (f"{_FAL_PIECES}/attachment_vm_ar_falima_tag_sight_off.smd", _FAL_PIECES_REFERENCE),
    },
    extra_bones={
        # 0.2 inside the front of the flash hider, on the bore (the barrel's tag_flash_attachment is at its front).
        "muzzle": ("tag_barrel_attach", np.array([9.419, 0.0, -0.007])),
        # Where the rifles' pistol grip mounts sit from the right wrist (as for the P90), on the centreline.
        "tag_pistolgrip_attach": ("tag_sling", np.array([2.747, 0.0, -1.872])),
    },
    materials=fal_materials,
    # From the addon's lua/weapons/mg_falima/shared.lua (no offsets).
    hip=view_offset(),
    aim=view_offset(),
    sprint=view_offset(),
    m4_sprint=True,
    ads_pose=("ads_in", slice(-1, None)),
    # About 5.0 kg loaded (4.25 kg empty, a 0.25 kg magazine and 20 rounds of 25.4 g), 1.25 kg over the AKM, by the
    # RPK's scaling: 0.25 x sqrt((5.0 + 4) / 7.75).
    ads_time=0.27,
    # The hip clip rolls the gun up to 3 degrees about the bore and swings it 1 forward every shot; the aimed one
    # rolls it 0.25 at most and kicks it 0.6 straight back.
    ads_fire="fire_2",
    report_bones=["tag_tip", "tag_silencer", "tag_laser_attach", "tag_laser_show2", "tag_rail", "tag_reflex",
                  "tag_sight_on", "tag_grip_attach"],
)

def famas_materials() -> dict[str, str]:
    return json.loads((ASSETS / "Weapons/FAMAS/famas_assets.json").read_text())["materials"]


_FAMAS = "v_falpha"
_FAMAS_BARREL = "attachment_vm_ar_falpha_barrel/attachment_vm_ar_falpha_barrel"
_FAMAS_MAG = "attachment_vm_ar_falpha_mag/attachment_vm_ar_falpha_mag.smd"
FAMAS = Weapon(
    name="famas", folder=ASSETS / "Weapons/FAMAS", asset="weapons/famas", model="famas",
    decompiled=DECOMPILED / "falpha", cod_anims=f"{_FAMAS}/{_FAMAS}_anims",
    vm_meshes=[f"{_FAMAS}/attachment_vm_ar_falpha_receiver.smd#!tag_stock_hide",
               f"{_FAMAS}/attachment_vm_ar_falpha_triggrip.smd"],
    part_meshes=[],
    optional_meshes={
        "muzzle_tip": (f"{_FAMAS_BARREL}_tip.smd", f"{_FAMAS_BARREL}.smd"),
        "laser_rail": (f"{_FAMAS_BARREL}_laser.smd", f"{_FAMAS_BARREL}.smd"),
        "iron_sights": (f"{_FAMAS}/attachment_vm_ar_falpha_toprail_sight_on.smd", None),
        "sight_folded": (f"{_FAMAS}/attachment_vm_ar_falpha_toprail_sight_off.smd", None),
    },
    extra_bones={
        "muzzle": ("tag_barrel_attach", np.array([11.28, 0.0, 0.0])),
        "tag_pistolgrip_attach": ("tag_sling", np.array([2.747, 0.0, -1.872])),
    },
    materials=famas_materials, hip=view_offset(), aim=view_offset(), sprint=view_offset(),
    m4_sprint=True, ads_pose=("ads_in", slice(-1, None)), ads_time=0.25,
    ads_fire="fire_2",
    report_bones=["tag_tip", "tag_laser_attach", "tag_reflex", "tag_grip_attach"],
    part_choices={
        "barrel": [("factory", f"{_FAMAS_BARREL}.smd")] + [
            (name, f"attachment_vm_ar_falpha_{name}/attachment_vm_ar_falpha_{name}.smd")
            for name in ("barshort", "barlong2", "barrellong_alt")],
        "stock": [("factory", f"{_FAMAS}/attachment_vm_ar_falpha_receiver.smd#tag_stock_hide")] + [
            (name, f"attachment_vm_ar_falpha_{name}/attachment_vm_ar_falpha_{name}.smd")
            for name in ("stock_light", "stock_stable", "stock_tactical_v1")],
        "magazine": [("factory", _FAMAS_MAG)] + [
            (name, f"attachment_vm_ar_falpha_{name}/attachment_vm_ar_falpha_{name}.smd")
            for name in ("xmags", "xmags2")],
        "rail": [("factory", f"{_FAMAS}/attachment_vm_ar_falpha_toprail_cust2.smd"),
                 ("classic", "attachment_vm_ar_falpha_toprail/attachment_vm_ar_falpha_toprail_crust.smd"),
                 ("low", "derived/low_rail.smd")],
    },
    tip_choices={name: (f"attachment_vm_ar_falpha_{name}/attachment_vm_ar_falpha_{name}_tip.smd",
                        f"attachment_vm_ar_falpha_{name}/attachment_vm_ar_falpha_{name}.smd")
                 for name in ("barshort", "barlong2", "barrellong_alt")},
    optional_variants={
        "iron_sights": [("low", "attachment_vm_ar_falpha_railcust/attachment_vm_ar_falpha_railcust_sight_on.smd",
                         "attachment_vm_ar_falpha_railcust/attachment_vm_ar_falpha_railcust.smd")],
        "sight_folded": [("low", "attachment_vm_ar_falpha_railcust/attachment_vm_ar_falpha_railcust_sight_on_2.smd",
                          "attachment_vm_ar_falpha_railcust/attachment_vm_ar_falpha_railcust.smd")],
    },
    reload_variants=["_xmag", "_xmag2"],
    reload_clip_overrides={"reload_xmag": "reload", "reload_xmag2": "reload"},
)

def m18_materials() -> dict[str, str]:
    # Built by p320_assets.py.
    assets = json.loads((ASSETS / "Weapons" / "M18" / "m18_assets.json").read_text(encoding="utf-8"))
    return assets["materials"]


def _papa320(model: str, sights: str | None = None) -> str:
    """One of the M18's slide models (attachment_vm_pi_papa320_<model>), joined with its sights: the model's "sight"
    bodygroup, a model of its own (the black slide's is the factory one's file)."""
    folder = f"attachment_vm_pi_papa320_{model}"
    return f"{folder}/{folder}.smd+{folder}/attachment_vm_pi_papa320_{sights or model}_sight_on.smd"


# The SIG Sauer M18 (9x19mm): MW2019's "M19" (mg_p320) from Viper's MW2019 pistol pack (Workshop 2459723892), the US
# Army's compact M17 with the coyote grip module and slide. The factory slide is 6.9 long, the real carry-length
# slide's size. A pistol rig: the gun hangs off tag_pistol_offset (read as tag_sling), and the rig has no left-hand IK
# tag (the left hand cups the right), no pistol grip mount and no muzzle, so those are extra bones.
M18 = Weapon(
    name="m18",
    folder=ASSETS / "Weapons" / "M18",
    asset="weapons/m18",
    model="m18",
    decompiled=DECOMPILED / "p320",
    cod_anims="v_p320_anims",
    # The grip module with the trigger. The slide, barrel, sights and magazine are the part_choices below.
    vm_meshes=["attachment_vm_pi_papa320_receiver.smd"],
    part_meshes=[],
    optional_meshes={},
    extra_bones={
        # 0.2 inside the barrel's end, on the bore (the slide model's tag_flash_attachment is 0.07 past its end).
        "muzzle": ("tag_barrel_attach", np.array([-0.49, 0.0, -0.126])),
        # Placed so the world model's grip sits where w_usp's does in its model, for the third-person Pistol hold:
        # the backstrap at x -3.86 and the magazine's floor at z 0.04. Its bore then sits at w_usp's height (4.77).
        "tag_pistolgrip_attach": ("tag_sling", np.array([-1.04, 0.0, -0.70])),
    },
    materials=m18_materials,
    # From the addon's lua/weapons/mg_p320/shared.lua.
    hip=view_offset(),
    aim=view_offset((0.15, 0.0, 0.0)),
    sprint=view_offset(),
    m4_sprint=True,
    ads_pose=("ads_in", slice(-1, None)),
    # The fire clips flip the muzzle up ~10 degrees as the slide cycles (1.75 back), back by frame 12; the hip one
    # also swings it 4.3 degrees sideways, the aimed one 1.6.
    ads_fire="fire_2",
    # The QC's empty_offset: while the magazine is empty the slide stays back on the slide stop, the barrel tilts down
    # out of battery and the magazine's top rounds are gone.
    slide_lock="a_delta_empty_additive_for_offset",
    bone_renames={"tag_pistol_offset": "tag_sling"},
    report_bones=["tag_reflex", "tag_sight_on", "tag_laser_attach", "tag_stock_attach", "tag_flash"],
    part_choices={
        # The slide with its barrel and sights (the Barrel slot, as a pistol's slide is in CoD): the factory coyote
        # slide, the black one, one with lightening cuts (0.4 longer), and a long slide over an extended barrel.
        "barrel": [("pi_papa320_slide", _papa320("slide")),
                   ("pi_papa320_slide_black", _papa320("slide_black", "slide")),
                   ("pi_papa320_slide_vented", _papa320("slide_vented")),
                   ("pi_papa320_barrel_ext", _papa320("barrel_ext"))],
        # Each holds the fitted magazine (j_mag1) and the reload's fresh one (j_mag2).
        "magazine": [("pi_papa320_mag", "attachment_vm_pi_papa320_mag/attachment_vm_pi_papa320_mag.smd"),
                     ("pi_papa320_mag_ext", "attachment_vm_pi_papa320_mag_ext/attachment_vm_pi_papa320_mag_ext.smd"),
                     ("pi_papa320_mag_ext2",
                      "attachment_vm_pi_papa320_mag_ext2/attachment_vm_pi_papa320_mag_ext2.smd")],
    },
    # The 21-round magazine reloads with the xmag clips (the 32's xmaglrg ones aren't ported: it isn't offered).
    reload_variants=["_xmag"],
)

def mcx_materials() -> dict[str, str]:
    # Built by mcx_assets.py.
    assets = json.loads((ASSETS / "Weapons" / "MCX" / "mcx_assets.json").read_text(encoding="utf-8"))
    return assets["materials"]


_MCX = "v_mcharlie"
_MCX_BARREL = "attachment_vm_ar_mcharlie_barrel/attachment_vm_ar_mcharlie_barrel"
# The receiver model the MW base bone-merges onto the viewmodel, for its rear sight.
_MCX_RECEIVER = "attachment_vm_ar_mcharlie_receiver/attachment_vm_ar_mcharlie"


def _mcx_sights(state: str) -> str:
    """The flip-up sights, raised (on) or folded down (off): the rear one at the back of the top rail (the receiver
    model's tag_sight bodygroup) and the front one at its front (the barrel's), each placed by its own model's reference
    pose."""
    return f"{_MCX_RECEIVER}_tag_sight_{state}.smd+{_MCX_BARREL}_tag_sight_{state}.smd"


# The SIG MCX Virtus SBR (5.56x45mm): MW2019's "M13" (mg_mcharlie) from Viper's MW2019 Assault Rifles pack (Workshop
# 2528829149), the 11.5-inch short-barrelled rifle as SIG sells it: the free-float M-LOK handguard with its full-length
# top rail, flip-up sights, SIG's three-prong flash hider, a 30-round polymer magazine and the folding telescoping stock.
# It's the real gun's size. Like the FAL's, its rig has no pistol grip part (the grip is the lower receiver's), so
# tag_pistolgrip_attach is an extra bone. The gunsmith's own part is SIG's thin folding stock (the pack's light stock).
MCX = Weapon(
    name="mcx",
    folder=ASSETS / "Weapons" / "MCX",
    asset="weapons/mcx",
    model="mcx",
    decompiled=DECOMPILED / "mcharlie",
    cod_anims=f"{_MCX}/{_MCX}_anims",
    # The viewmodel's own receiver mesh (the lower and the upper), in its bind pose. Its stock adapter (the tag_stock
    # bodygroup) is left out: it's an adapter for MW's generic stocks, and each MCX stock carries its own hinge.
    vm_meshes=[f"{_MCX}/attachment_vm_ar_mcharlie_receiver.smd"],
    # The barrel with its handguard (each MW barrel has its own length of handguard), and the magazine: the fitted one
    # on j_mag1 and the reload's fresh one on j_mag2.
    part_meshes=[(f"{_MCX_BARREL}.smd", f"{_MCX_BARREL}.smd"),
                 ("attachment_vm_ar_mcharlie_mag/attachment_vm_ar_mcharlie_mag.smd",
                  "attachment_vm_ar_mcharlie_mag/attachment_vm_ar_mcharlie_mag.smd")],
    # The stock: the factory folding telescoping one, then SIG's thin folding stock. Left out: the pack's other stock
    # (CoD's), its 50- and 60-round magazines, its .300 BLK magazine and barrel (another calibre), and its other barrels.
    part_choices={
        "stock": [("factory", "attachment_vm_ar_mcharlie_stock/attachment_vm_ar_mcharlie_stock.smd"),
                  ("thin", "attachment_vm_ar_mcharlie_lightstock/attachment_vm_ar_mcharlie_lightstock.smd")],
    },
    optional_meshes={
        "muzzle_tip": (f"{_MCX_BARREL}_tip.smd", f"{_MCX_BARREL}.smd"),  # the flash hider
        # The flip-up sights raised, and folded down under an optic.
        "iron_sights": (_mcx_sights("on"), _mcx_sights("on")),
        "sight_folded": (_mcx_sights("off"), _mcx_sights("off")),
    },
    extra_bones={
        # 0.2 inside the front of the flash hider's prongs, on the bore (the barrel's tag_flash_attachment is 0.6
        # behind their tips).
        "muzzle": ("tag_barrel_attach", np.array([12.819, 0.0, -0.023])),
        # Where the rifles' pistol grip mounts sit from the right wrist (as for the P90), on the centreline.
        "tag_pistolgrip_attach": ("tag_sling", np.array([2.747, 0.0, -1.872])),
    },
    materials=mcx_materials,
    # From the addon's lua/weapons/mg_mcharlie/shared.lua, except aim. The addon's iron-sight aim (0, -1, 0) leaves the
    # rear aperture's centre 0.01 above the camera and the front post's tip 0.058 deg over the aim point; this lowers the
    # gun onto the line through them and turns out its tilt, which puts both on the aim point (ads_in's last frame).
    hip=view_offset(),
    aim=view_offset((0.0, -1.0, -0.007), (0.036, 0.0, 0.0)),
    sprint=view_offset(),
    m4_sprint=True,
    ads_pose=("ads_in", slice(-1, None)),
    # The hip clip rolls the gun up to 2.5 degrees about the bore and pitches it 1.1 every shot, and at 850 rpm each shot
    # starts it again; the aimed one rolls it 0.5 at most and kicks it 0.5 straight back.
    ads_fire="fire_2",
    report_bones=["tag_tip", "tag_silencer", "tag_flash_attachment", "tag_flash", "tag_laser_attach", "tag_reflex",
                  "tag_sight_on", "tag_grip_attach", "tag_folding_grip"],
    # The thumb lies over the top rail from its left side, and aimed CoD's hand sits lower: HC1's thicker thumb sank into
    # the rail (the user's screenshot, 2026-10-05). Its axis was 0.44 over the rail at the hip and 0.25 aimed, where
    # the AK-105's, M16A4's and FAL's thumbs keep 0.49-0.52. This lifts it to 0.60 and 0.52, the fingertips go from
    # 0.13 to 0.18 off the handguard and the palm stays 0.57 off it (the M16A4's 0.57). Measured from the bones against
    # the gun mesh, since the arms' mesh wasn't to hand; first applied to the exported clips, not from the rips.
    left_grip=GripFit(shift=(0.0, -0.05, 0.15), thumb=0.2),
)

def l85a2_materials() -> dict[str, str]:
    # Built by l85a2_assets.py.
    assets = json.loads((ASSETS / "Weapons" / "L85A2" / "l85a2_assets.json").read_text(encoding="utf-8"))
    return assets["materials"]


_L85 = "v_lima86"
_L85_BARREL = "attachment_vm_lm_lima86_barrel_short/attachment_vm_lm_lima86_barrel_short"


# The L85A2 (5.56x45mm): MW2019's "SA87" (mg_lima86) from Viper's MW2019 LMG pack (Workshop 2960120610). The pack's
# default is the L86A2 light support weapon's long barrel; with its short one it's the L85A2 rifle, at the real gun's
# size (785 mm long, 518 mm barrel): the A2's railed handguard, the carrying handle with its rear aperture and the
# foresight on its bracket (the non-infantry iron sights), the MW flash hider and a 30-round magazine. Like the FAL's,
# its rig has no pistol grip part (the grip is the receiver's), so tag_pistolgrip_attach is an extra bone.
L85A2 = Weapon(
    name="l85a2",
    folder=ASSETS / "Weapons" / "L85A2",
    asset="weapons/l85a2",
    model="l85a2",
    decompiled=DECOMPILED / "lima86",
    cod_anims=f"{_L85}/{_L85}_anims",
    # The viewmodel's own bodygroup meshes, in its bind pose: the receiver (with the front end) and the butt plate.
    vm_meshes=[f"{_L85}/attachment_vm_lm_lima86_receiver.smd", f"{_L85}/attachment_vm_lm_lima86_stock.smd"],
    # The short barrel, and the magazine: the fitted one on j_mag1 and the reload's fresh one on j_mag2. Left out: the
    # pack's long and mid barrels (the L86A2's), its bipod, its 60-round magazines and CoD's stocks.
    part_meshes=[(f"{_L85_BARREL}.smd", f"{_L85_BARREL}.smd"),
                 ("attachment_vm_lm_lima86_mag/attachment_vm_lm_lima86_mag.smd",
                  "attachment_vm_lm_lima86_mag/attachment_vm_lm_lima86_mag.smd")],
    optional_meshes={
        "muzzle_tip": (f"{_L85_BARREL}_tip.smd", f"{_L85_BARREL}.smd"),  # the flash hider
        # The carrying handle with the rear aperture, and the foresight on its bracket: an optic takes both off, as on
        # the real gun, where they're one kit.
        "iron_sights": (f"{_L85}/attachment_vm_lm_lima86_sight.smd", None),
        # The laser's mount on the handguard's right side, shown only under a laser.
        "laser_rail": (f"{_L85}/attachment_vm_lm_lima86_laser.smd", None),
    },
    extra_bones={
        # 0.2 inside the front of the flash hider, on the bore (the barrel's tag_flash_attachment is 0.67 inside it).
        "muzzle": ("tag_barrel_attach", np.array([5.54, 0.0, 0.0])),
        # Where the rifles' pistol grip mounts sit from the right wrist (as for the P90), on the centreline: 4.2 in front
        # of the idle clip's wrist and 2.3 above it.
        "tag_pistolgrip_attach": ("tag_sling", np.array([8.011, 0.0, -2.328])),
    },
    materials=l85a2_materials,
    # From the addon's lua/weapons/mg_lima86/shared.lua.
    hip=view_offset(),
    aim=view_offset((0.0, 1.0, 0.0)),
    sprint=view_offset(),
    m4_sprint=True,
    ads_pose=("ads_in", slice(-1, None)),
    # About 4.7 kg loaded with the iron sights (3.82 kg empty, 4.98 kg with SUSAT and a loaded magazine), 0.95 kg over
    # the AKM's 3.75: 0.25 s x sqrt((4.7 + 4) / (3.75 + 4)), as for the RPK.
    ads_time=0.26,
    # The hip clip rolls the gun 2.5 degrees about the bore and yaws it 1.2 every shot; the aimed one only kicks it
    # 0.24 straight back.
    ads_fire="fire_2",
    report_bones=["tag_tip", "tag_silencer", "tag_flash_attachment", "tag_flash", "tag_laser_attach", "tag_laser_show",
                  "tag_reflex", "tag_acog_2", "tag_grip_attach", "tag_stock_attach", "tag_mag_attach"],
    # The rig's tag_brass is in the handguard (17.8 ahead of tag_sling, 3 under the bore). The real ejection port is
    # behind the cocking handle's slot, under its hinged cover (x -3.93 to -1.62, z -0.49 to 0.33, the receiver's wall
    # at y -0.68 and the cover at -0.83): the cases leave its middle.
    moved_bones={"tag_brass": ("tag_sling", np.array([-2.6, -0.75, -0.1]))},
    # The handguard's lower half: where CoD's hand sits, HC1's palm heel and thumb sank 0.39 into its left side and the
    # fingers into the bottom rail. Measured by skinning the arms against the gun mesh (417 vertices, 0.39 deep -> 24,
    # 0.10 at the hip and 26, 0.10 aimed; the verified Kastov 762 has 54 and 49, 0.10). The fingers still wrap the
    # rail's underside.
    left_grip=GripFit(shift=(0.0, 0.55, -0.55), fingers=0.4, thumb=0.1),
)


def hk416_materials() -> dict[str, str]:
    # Built by hk416_assets.py.
    assets = json.loads((ASSETS / "Weapons" / "HK416" / "hk416_assets.json").read_text(encoding="utf-8"))
    return assets["materials"]


_HK = "v_ron_hk416"
_HK_BARREL = "v_ron_hk416_barrel"


def _hk416_mag(folder: str, mesh: str, rounds: str = "hk416_fmj") -> str:
    """A magazine with its rounds: the body (on j_mag1, and the reload's fresh one on j_mag2) and the top rounds of
    each."""
    return f"{folder}/{mesh}+{folder}/{rounds}_1.smd+{folder}/{rounds}_2.smd"


# The HK416 A5 (5.56x45mm), with the 11-inch barrel: RoN's HK416 for the MW base ("[MW Unofficial] RON HK416 A5", Workshop
# 3385630838), the model Ready or Not ships, with Escape from Tarkov's HK E1 and Slim Line stocks and its Magpul and HK
# magazines. It's about the real gun's size: 29.3 in from the butt to the muzzle with the factory stock collapsed, where HK
# USA gives 27.9 in for the 11-inch A5's, and its top rail is 0.814 wide (a Picatinny rail's 0.835). Its own rig, not a
# CoD one, so its pieces are the viewmodel's bodygroups (vm_meshes), its barrel and magazines are bone-merged models, and
# its Tarkov stocks are VElements (part_mounts).
HK416 = Weapon(
    name="hk416",
    folder=ASSETS / "Weapons" / "HK416",
    asset="weapons/hk416",
    model="hk416",
    decompiled=DECOMPILED / "hk416",
    cod_anims=f"{_HK}/{_HK}_anims",
    # The receiver, the handguard, the pistol grip, the charging handle, the bolt carrier and the loose round the
    # reloads chamber (on j_magrel).
    vm_meshes=[f"{_HK}/hk416_body.smd", f"{_HK}/hk416_handguard.smd", f"{_HK}/hk416_pistolgrip.smd",
               f"{_HK}/hk416_chargerhandle.smd", f"{_HK}/hk416_bolt.smd", f"{_HK}/hk416_bullet_fmj.smd"],
    part_meshes=[(f"{_HK_BARREL}/hk416_barrel.smd", f"{_HK_BARREL}/hk416_barrel.smd")],
    part_choices={
        # The magazine: HK's steel 30-rounder (the gun's own), then HK's polymer Gen 2 and Magpul's PMAG Gen M3 in 20,
        # 30 (with its window) and 40 rounds. Left out: the pack's ISO and TAQ magazines (Tarkov's made-up ones) and the
        # speed-pull loops.
        "magazine": [
            ("factory", _hk416_mag("ron_hk416_magazine", "hk416_magazine.smd", "hk416_FMJ")),
            ("gen2", _hk416_mag("ron_hk416_gen2_magazine", "hk_gen_2_mags.smd", "hk416_FMJ")),
            ("pmag20", _hk416_mag("ron_hk416_magpul_20rd", "mag_stanag_magpul_pmag_gen_m3_556x45_20_LOD0.smd")),
            ("pmag30", _hk416_mag("ron_hk416_magpul_30rd", "magpul_mag_1.smd")),
            ("pmag40", _hk416_mag("ron_hk416_magpul_40rd", "magpul_mag_40.smd")),
        ],
        # The stock: the viewmodel's own collapsible stock, then Tarkov's HK E1 and HK Slim Line. Left out: the pack's
        # other stocks (other makers' AR stocks and an AK-12's).
        "stock": [("factory", f"{_HK}/hk416_stock.smd"),
                  ("e1", "hk416_eft_e1_stock/hk_e1.smd"),
                  ("slim_line", "hk416_eft_slim_line_stock/hk_slim_line.smd")],
    },
    # The pack's lua (mg_base/modules/attachmentss/hk416_ron/stock/hk416_e1.lua, hk416_slim_line.lua): both on
    # tag_stock_attach at Vector(0, 1.6, -0.07), which MoveVElement reads as 1.6 forward and 0.07 down.
    part_mounts={
        "hk416_eft_e1_stock/hk_e1.smd": ("tag_stock_attach", np.array([1.6, 0.0, -0.07])),
        "hk416_eft_slim_line_stock/hk_slim_line.smd": ("tag_stock_attach", np.array([1.6, 0.0, -0.07])),
    },
    optional_meshes={
        "muzzle_tip": (f"{_HK_BARREL}/hk416_muz.smd", f"{_HK_BARREL}/hk416_barrel.smd"),  # the flash hider
        # HK's flip-up diopter sights raised, and folded down under an optic.
        "iron_sights": (f"{_HK}/hk416_iro.smd", None),
        "sight_folded": (f"{_HK}/hk416_iro_off.smd", None),
        # The M-LOK rail section on the handguard's right side, under a laser. There's no Underbarrel slot (so no rail
        # on the bottom): the left hand cups the handguard's underside from 6.5 to 10.4, and its bottom rail ends at 11.1.
        "laser_rail": (f"{_HK}/mlok_right.smd", None),
    },
    extra_bones={
        # 0.2 inside the front of the flash hider, on the bore (the rig's tag_flash is 0.8 inside it).
        "muzzle": ("tag_barrel_attach", np.array([13.04, 0.0, -0.035])),
        # Where the rifles' pistol grip mounts sit from the right wrist (as for the P90), on the centreline: 4.2 in front
        # of the idle clip's wrist and 2.3 above it.
        "tag_pistolgrip_attach": ("tag_sling", np.array([1.974, 0.0, -1.561])),
    },
    materials=hk416_materials,
    # From the addon's lua/weapons/mg_ron_hk416/shared.lua: Idle (0, 0.5, 0) and Aim (0, 0.5, -0.18).
    hip=view_offset((0.0, 0.5, 0.0)),
    aim=view_offset((0.0, 0.5, -0.18)),
    sprint=view_offset(),
    m4_sprint=True,
    ads_pose=("ads_in", slice(-1, None)),
    ads_fire="fire_2",
    reload_variants=["_smag", "_xmag"],
    report_bones=["tag_flash", "tag_silencer", "tag_brass", "tag_reflex", "tag_holo", "tag_acog_2", "tag_sight_on",
                  "tag_stock_attach", "tag_mag_attach", "tag_ik_loc_le", "tag_grip_hide"],
)

def ak12_materials() -> dict[str, str]:
    # Built by ak12_assets.py; the AK-105's magazines and the AK grips keep the AK-105's and 74u's materials.
    assets = json.loads((ASSETS / "Weapons" / "AK12" / "ak12_assets.json").read_text(encoding="utf-8"))
    return assets["materials"]


def _ak105_part(model: str) -> tuple[str, str]:
    """A part_choices entry for one of the AK-105's own attachment models, from another gun's decompile."""
    choice, path = _attachment(model)
    return choice, f"../akilo105/{path}"


# The AK-12 (5.45x39mm, Kalashnikov's 6P70 of 2020): Escape from Tarkov's model from the ARC9 EFT Assault Rifles pack
# (Workshop 2962829818), on the AK-105's CoD rig and clips. The real gun is an AK: its magazine well, trigger group,
# selector and mag catch are the AK-74M's, so they're fitted onto the AK-105's (within 0.08 at the trigger, the catch
# and the magazine's top), and its 415 mm barrel, gas block with the front sight, railed dust cover and handguard and
# its folding, telescoping stock come with it. Tools/ak12_rig.py writes the pieces as SMDs on the AK-105's skeleton
# (decompiled/ak12/rig): the bolt carrier on j_boltcarrier, the trigger on j_trigger, the selector on j_fireselect, the
# mag catch on j_magrelease and the magazine with its top rounds on j_mag1 and j_mag2.
_AK12_RIG = "rig"
AK12 = Weapon(
    name="ak12",
    folder=ASSETS / "Weapons" / "AK12",
    asset="weapons/ak12",
    model="ak12",
    decompiled=DECOMPILED / "ak12",
    cod_anims="../akilo105/vm_iw9_akilo105_anims",
    vm_meshes=[f"{_AK12_RIG}/ak12_receiver.smd"],
    part_meshes=[],
    optional_meshes={
        "muzzle_tip": (f"{_AK12_RIG}/ak12_brake.smd", None),  # the 5.45 muzzle brake, off under a muzzle device
        "iron_sights": (f"{_AK12_RIG}/ak12_rear_sight.smd", None),  # the diopter rear sight on the dust cover's rail
    },
    # 0.2 inside the front of the muzzle brake, on the bore.
    extra_bones={"muzzle": ("tag_sling", np.array([28.22, 0.573, 1.03]))},
    materials=ak12_materials,
    hip=view_offset(),
    # The AK-105's ads_in leaves its own sights' line on the eye. The AK-12's diopter sits 0.23 higher and its front post
    # is a little lower, so this lowers the gun until the aperture's centre is on the aim point and pitches it 0.095
    # degrees up onto the post's tip (measured at ads_in's last frame: both within 0.001 and 0.005 degrees).
    aim=view_offset((-0.009, 0.0, -0.234), (0.095, 0.0, 0.0)),
    sprint=view_offset(),
    m4_sprint=True,
    ads_pose=("ads_in", slice(-1, None)),
    report_bones=["tag_brass", "tag_mag_attach", "tag_stock_attach", "tag_pistolgrip_attach"],
    part_choices={
        # The AK-12's own grip, then the AK-74M's and the AK-platform grips: it takes any AK grip.
        "pistol_grip": [("factory", f"{_AK12_RIG}/ak12_pgrip.smd"), _ak105_part("ar_akilo105_pgrip_v0")] + [
            _kastovia(model) for model in (
                "sh_vecho_pgrip_v0", "ar_akilo_griptac_v0", "ar_akilo_gripstdy_v0", "ar_akilo_gripass_v0",
                "sh_vecho_gripsnp_v0", "ar_akilo_pstlgrp_v0")],
        # The AK-12's own 30-round magazine (with its window), then the 5.45 AK-74 magazines it takes: the AK-74M's
        # 30, a 20, the RPK-74's 45 and a four-column 60. Each holds the fitted magazine (j_mag1) and the reload's
        # fresh one (j_mag2).
        "magazine": [("factory", f"{_AK12_RIG}/ak12_mag.smd"), _ak105_part("ar_akilo105_mag_v0"),
                     _kastovia("ar_akilo105_smag_v0"), _kastovia("ar_akilo105_xmag_v0"),
                     _ak105_part("ar_akilo105_xmaglrg_v0")],
    },
    reload_variants=["_smag", "_xmag", "_xmaglrg"],
    # The AK-105's factory barrel's (att_vm_p04_ar_akilo105_barrel_v0.lua: grip_pose_l_offset).
    grip_pose="a_delta_barhvyshort_additive_for_offset",
)


def ak15_materials() -> dict[str, str]:
    # Built by ak15_assets.py: the AK-12's, its own magazine and rounds, and the RPK's AKM and RPK magazines.
    assets = json.loads((ASSETS / "Weapons" / "AK15" / "ak15_assets.json").read_text(encoding="utf-8"))
    return assets["materials"]


def _rkilo_part(model: str) -> tuple[str, str]:
    """A part_choices entry for one of the RPK's own magazine models (decompiled to easy_att_vm_p04_<model>), from
    another gun's decompile."""
    choice, path = _rkilo(model, f"easy_att_vm_p04_{model}")
    return choice, f"../rkilo/{path}"


# The AK-15 (7.62x39mm, Kalashnikov's 6P71): the AK-12 in 7.62, with the same receiver, furniture, sights and brake
# on a 7.62 barrel, so it's the AK-12's model and rig (above) with Tarkov's AK-103 polymer 30-round magazine and 7.62
# rounds in place of the 5.45 magazine (Tools/ak15_rig.py writes rig/ak15_mag.smd).
AK15 = Weapon(
    name="ak15",
    folder=ASSETS / "Weapons" / "AK15",
    asset="weapons/ak15",
    model="ak15",
    decompiled=DECOMPILED / "ak12",
    cod_anims="../akilo105/vm_iw9_akilo105_anims",
    vm_meshes=[f"{_AK12_RIG}/ak12_receiver.smd"],
    part_meshes=[],
    optional_meshes={
        "muzzle_tip": (f"{_AK12_RIG}/ak12_brake.smd", None),
        "iron_sights": (f"{_AK12_RIG}/ak12_rear_sight.smd", None),
    },
    extra_bones={"muzzle": ("tag_sling", np.array([28.22, 0.573, 1.03]))},
    materials=ak15_materials,
    hip=view_offset(),
    # The AK-12's: the same sights on the same receiver.
    aim=view_offset((-0.009, 0.0, -0.234), (0.095, 0.0, 0.0)),
    sprint=view_offset(),
    m4_sprint=True,
    ads_pose=("ads_in", slice(-1, None)),
    report_bones=["tag_brass", "tag_mag_attach", "tag_stock_attach", "tag_pistolgrip_attach"],
    part_choices={
        "pistol_grip": AK12.part_choices["pistol_grip"],
        # Its own AK-103 magazine, then the 7.62x39 magazines it takes: the AKM's 30-round steel one and the RPK's 40
        # (the RPK's models).
        "magazine": [("factory", f"{_AK12_RIG}/ak15_mag.smd"), _rkilo_part("ar_akilo_mag_v0"),
                     _rkilo_part("ar_akilo_xmag_v0")],
    },
    # The RPK 40 reloads with the AK-105's 45-round clips, the nearest in length.
    reload_variants=["_xmag"],
    grip_pose="a_delta_barhvyshort_additive_for_offset",
)

WEAPONS ={weapon.name: weapon for weapon in (KASTOV_762, KASTOV_74U, VITYAZ, RPK, BIZON, AK105, VEPR12, M16, P90,
                                              MP7, AUG, UZI, FAL, FAMAS, M18, MCX, L85A2, HK416, AK12, AK15)}


def add_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--weapon", choices=sorted(WEAPONS), default=KASTOV_762.name, help="the gun to build")


def from_command_line(description: str | None = None) -> Weapon:
    """The --weapon of a script with no other arguments."""
    parser = argparse.ArgumentParser(description=description, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_argument(parser)
    return WEAPONS[parser.parse_args().weapon]

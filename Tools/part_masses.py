"""Every gunsmith part's weight against the factory part it replaces: GunsmithPart.Mass, in kg.

The game turns it into what weight really does (GunsmithAttachmentEffects.ApplyMass): a heavier gun kicks back less (free
recoil goes as one over the weight), comes up to the eye more slowly (as the square root of the weight swung with the
arms) and slows every gait by about 1% per kg over the rifles' 3.75 kg.

The figures are makers' published weights, or the usual ones for that kind of part, with the mount where the part needs
one. A magazine counts loaded: its empty weight plus its rounds (ROUND_KG). A part that replaces another weighs the
difference; one that fits where the gun has nothing (optics, grips, lasers) weighs all it weighs. A suppressor takes off
the ~50 g flash hider it replaces.

The ported guns' own parts (kastov_prefabs.own_parts) are worked out from each part_choices choice's own weight
(OWN_CHOICES, OWN_MAGAZINES) against the gun's factory choice, so a rerun of kastov_prefabs.py writes the same figures.
The M16A4's copies of the M4 parts (m16_gunsmith.resources) are against the M16A4's own fixed stock and 20-inch barrel.

Each gun's own weight, loaded with its factory magazine and parts, is its Equipment.LoadedMass (GUN_KG), which the
parts add to. kastov_prefabs.py writes it into the ported guns' prefabs; this script writes it into every gun's.

Run: python Tools/part_masses.py           writes Mass into every part file and LoadedMass into every gun, in place
     python Tools/part_masses.py --check   lists the files it would change, and parts it has no figure for
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import kastov_weapons as W

ASSETS = W.ASSETS

# Each gun's weight with a loaded factory magazine, kg (Equipment.LoadedMass), by its weapon prefab's folder and name.
# Makers' figures, or the manuals': the empty gun plus its loaded magazine (ROUND_KG, the magazines below).
GUN_KG = {
    "M4A1/weapon_m4a1": 3.4,          # M4A1 2.88 kg empty + a loaded USGI 30
    "ScarH/weapon_scarh": 4.6,        # SCAR-H 3.58 kg + a loaded 30 of M80
    "MP5/weapon_mp5": 3.4,            # MP5A3 2.88 kg + a loaded 30
    "M700/weapon_m700": 5.4,          # an M24-type heavy-barrel M700 with its scope and 5 rounds
    "Spaghelli/weapon_spaghelli": 4.1,  # a semi-auto combat shotgun (~3.8 kg) with 8 shells
    "USP/weapon_usp": 1.14,           # USP .45 0.78 kg + a loaded 12
    "USP_SD/weapon_usp_sd": 1.3,      # the same with its threaded barrel and can
    "Colt1911/weapon_colt1911": 1.35,  # M1911A1 1.1 kg + a loaded 7
    "Kastov/weapon_kastov762": 3.75,  # AKM with a loaded 30 (the manual's 3.6-3.8)
    "Kastov74u/weapon_kastov74u": 3.2,  # AKS-74U 2.7 kg + a loaded 30
    "Vityaz/weapon_vityaz": 3.4,      # PP-19-01 2.9 kg + a loaded 30
    "RPK/weapon_rpk": 6.8,            # RPK 4.8 kg + the loaded 75-round drum
    "Bizon/weapon_bizon": 3.0,        # PP-19 2.1 kg + the loaded 64-round helical magazine
    "AK105/weapon_ak105": 3.5,        # AK-105 3.0 kg + a loaded 30
    "Vepr12/weapon_vepr12": 4.8,      # Vepr-12 4.2 kg + a loaded 8
    "M16/weapon_m16": 4.0,            # M16A4 3.4 kg + a loaded 30
    "P90/weapon_p90": 3.1,            # P90 2.6 kg + the loaded 50
    "MP7/weapon_mp7": 2.3,            # MP7A1 1.9 kg + a loaded 40
    "AUG/weapon_aug": 3.8,            # AUG A3 3.3 kg + a loaded 30
    "Uzi/weapon_uzi": 4.2,            # Uzi 3.5-3.7 kg with the metal stock + a loaded 32
    "FAL/weapon_fal": 5.0,            # FAL 50.00 4.25 kg + a loaded 20
    "FAMAS/weapon_famas": 4.0,        # FAMAS F1 3.6 kg + a loaded 25
    "M18/weapon_m18": 0.95,           # M18 0.74 kg + a loaded 17
    "MCX/weapon_mcx": 3.4,            # MCX Virtus SBR 2.9 kg + a loaded 30
    "L85A2/weapon_l85a2": 4.7,        # L85A2 3.82 kg + the iron sights' carrying handle + a loaded 30
    "HK416/weapon_hk416": 3.75,       # HK416 A5 11-inch 3.13 kg (HK USA's 6.9 lb) + HK's steel 30 loaded
    "AK12/weapon_ak12": 4.0,          # AK-12 3.5 kg without a magazine (Rosoboronexport's catalogue) + a loaded 30
}


def gun_kg(weapon_name: str) -> float:
    """A ported gun's GUN_KG, by its kastov_weapons name."""
    return GUN_KG[W.WEAPONS[weapon_name].folder.relative_to(ASSETS / "Weapons").as_posix() + f"/weapon_{weapon_name}"]


# One loaded cartridge, kg.
ROUND_KG = {
    "5.56": 0.0123,     # M855: 4.0 g bullet, 12.3 g round
    "5.45": 0.0105,     # 7N6
    "7.62x39": 0.0163,  # PS
    "7.62x51": 0.0254,  # M80
    "9x19": 0.012,      # 124 gr ball
    "9x19 M1152": 0.0115,  # 115 gr
    "12ga": 0.040,      # 2 3/4" 00 buck
}
GUN_ROUND = {
    "kastov762": "7.62x39", "rpk": "7.62x39", "kastov74u": "5.45", "ak105": "5.45", "vityaz": "9x19", "uzi": "9x19",
    "vepr12": "12ga", "aug": "5.56", "famas": "5.56", "m16": "5.56", "m4a1": "5.56", "fal": "7.62x51",
    "scarh": "7.62x51", "mp5": "9x19", "m18": "9x19 M1152", "mcx": "5.56",
    "hk416": "5.56", "ak12": "5.45",
}

# Empty magazines, kg, and how many rounds they hold. The AK-74's polymer 30 is 0.23 kg; the AKM's steel 30 0.33; the
# RPK's steel 40 0.42 and its 75-round drum 0.9. A USGI aluminium STANAG 30 is 0.117 kg (15 0.08, 20 0.09); a PMAG 40
# 0.18; the 45- and 60-rounders 0.2 and 0.36 (SureFire's MAG5-60). The MP5's steel 30 is 0.17, its 45 0.25.
AK_MAGAZINES = {
    "ar_akilo74_mag_v0": (0.23, 30), "ar_akilo105_mag_v0": (0.23, 30), "ar_akilo105_smag_v0": (0.17, 20),
    "ar_akilo105_xmag_v0": (0.29, 45),  # RPK-74's 45
    "ar_akilo105_xmaglrg_v0": (0.40, 60),  # four-column 60
    "ar_akilo_mag_v0": (0.33, 30), "ar_akilo_xmag_v0": (0.42, 40), "lm_rkilo_mag_v0": (0.90, 75),
}
OWN_MAGAZINES = {
    "kastov762": {"ak47_mag_default": (0.33, 30), "ak47_mag_polymer": (0.25, 30), "ak47_mag_extended": (0.42, 40),
                  "ak47_mag_drum": (0.90, 75)},
    "vityaz": {"sm_aviktor_mag_v0": (0.20, 30), "sm_aviktor_xmag_v0": (0.27, 45)},
    "vepr12": {"sh_vecho_mag_v0": (0.35, 8), "sh_vecho_xmag_v0": (0.47, 12), "sh_vecho_drummag_v0": (1.30, 25)},
    "uzi": {"sm_uzulu_mag": (0.20, 32), "sm_uzulu_xmags": (0.24, 40), "sm_uzulu_xmag2": (0.28, 50)},
    "aug": {"factory": (0.13, 30), "drum": (0.60, 60)},  # Steyr's polymer 30
    "fal": {"factory": (0.25, 20), "xmag": (0.38, 30)},  # steel 20; the FALO's 30
    "famas": {"factory": (0.15, 25)},
    "m18": {"pi_papa320_mag": (0.075, 17), "pi_papa320_mag_ext": (0.085, 21)},
    "m16": {"standard": (0.117, 30), "smag": (0.08, 15), "xmag": (0.20, 45), "xmaglrg": (0.36, 60)},
    # HK's steel 30 (~0.25 kg) and polymer 30 (~0.14); Magpul's PMAG Gen M3 20, 30 and 40 (3.9, 4.8 and 6.3 oz).
    "hk416": {"factory": (0.25, 30), "gen2": (0.14, 30), "pmag20": (0.11, 20), "pmag30": (0.136, 30),
              "pmag40": (0.18, 40)},
    "ak12": {"factory": (0.215, 30)},  # the AK-12's polymer 30 with its window, a little lighter than the AK-74M's
}

# AK-platform stocks and pistol grips, each on its own, kg: the AKS-74U's folding stock 0.35, the AK-74M's polymer
# side-folder 0.45, the AKM's wooden stock 0.48, the RPK's club foot 0.75, a wire stock 0.3, and so on.
AK_CHOICES = {
    "ar_akilo74_stock_v0": 0.35, "ar_akilo74_stockno_v0": 0.03, "ar_akilo74_stockskel_v0": 0.25,
    "ar_akilo_stock_v0": 0.45, "ar_akilo105_stock_v0": 0.45, "ar_akilo_stockh_v0": 0.48, "ar_akilo_stocktac_v0": 0.42,
    "ar_akilo_stocktac02_v0": 0.38, "ar_akilo_stockwire_v0": 0.30, "sh_vecho_stock_v0": 0.55,
    "sh_vecho_stocktac_v0": 0.35, "lm_rkilo_stock_v0": 0.75, "lm_rkilo_stockh_v0": 0.70, "lm_rkilo_stocktac_v0": 0.50,
    "lm_rkilo_stockar_v0": 0.50,
    "ar_akilo_pstlgrp_v0": 0.08, "ar_akilo105_pgrip_v0": 0.08, "ar_akilo_griptac_v0": 0.10,
    "ar_akilo_gripstdy_v0": 0.09, "ar_akilo_gripass_v0": 0.07, "sh_vecho_pgrip_v0": 0.09, "sh_vecho_gripsnp_v0": 0.13,
}
# Each gun's other own choices, kg, against a base of 0 where only the difference is known.
OWN_CHOICES = {
    "kastov762": {"ak47_stock_default": 0.50, "ak47_stock_adjustable": 0.45, "ak47_stock_heavy": 0.60,
                  "ak47_stock_padded": 0.45, "ak47_stock_light": 0.30, "ak47_stock_delete": 0.05,
                  "ak47_stock_tactical": 0.42, "ak47_grip_default": 0.08, "ak47_grip_contoured": 0.09,
                  "ak47_grip_textured": 0.10, "ak47_grip_skeleton": 0.06,
                  "ak47_barrel_default": 0.0, "ak47_barrel_compact": -0.12},  # 415 mm cut to ~315
    "vityaz": {"sm_aviktor_barrel_v0": 0.0, "sm_aviktor_barlightlong_v0": 0.10},
    "aug": {"factory": 0.0, "lightweight": -0.08, "tactical": 0.10, "long": 0.65},  # the HBAR's 621 mm heavy barrel
    "fal": {"factory": 0.0, "para": -0.10, "short": -0.22},  # 533 mm barrel cut to 458
    "famas": {"factory": 0.0, "barshort": -0.15, "barlong2": 0.15, "barrellong_alt": 0.45, "stock_light": -0.10,
              "stock_stable": 0.05, "stock_tactical_v1": 0.25, "classic": 0.0, "low": 0.0},
    "uzi": {"sm_uzulu_stock": 0.0, "sm_uzulu_stock_folded": 0.0, "sm_uzulu_stockh": 0.10},
    "m18": {"pi_papa320_slide": 0.0, "pi_papa320_slide_black": 0.0},  # the same slide in another finish
    "mcx": {"factory": 0.0, "thin": -0.06},  # SIG's thin folding stock, ~2 oz under its folding telescoping one
    # Against the collapsible stock (~0.25 kg): HK's E1 with its rubber buttpad ~0.3, the Slim Line ~0.2.
    "hk416": {"factory": 0.0, "e1": 0.05, "slim_line": -0.05},
    "ak12": {"factory": 0.09},  # the AK-12's own pistol grip, a little bigger than the AK-74M's
}

# The MWII attachments shared across guns, by file stem, wherever they're fitted.
SHARED = {
    # Optics with their mounts. Mini red dots on a riser (a Trijicon RMR on a mount ~0.12); holographic sights 0.32
    # (an EOTech EXPS3 0.32); a Tube Red Dot on its mount 0.33 (Aimpoint's CompM4s 0.33); 3x prisms 0.4-0.5 (Trijicon's
    # ACOG TA31 0.43); a 3x magnifier and its sight 0.43-0.9; 6x scopes in their mounts 0.86-0.95; digital sights 0.8-1.0.
    "att_vm_2x_west01": 0.43, "att_vm_2x_west02": 0.68, "att_vm_2x_west02_holo": 0.32, "att_vm_4x_east01_tall": 0.45,
    "att_vm_4x_west01_tall": 0.43, "att_vm_4x_west02_tall": 0.40, "att_vm_holo_east01": 0.30,
    "att_vm_holo_west01": 0.33, "att_vm_holo_west02": 0.32, "att_vm_hybrid_west01": 0.48,
    "att_vm_hybrid_west02": 0.72, "att_vm_hybrid_west02_thermal": 0.90, "att_vm_hybrid_west03": 0.50,
    "att_vm_minireddot01_tall": 0.12, "att_vm_minireddot02_tall": 0.13, "att_vm_minireddot03_tall": 0.14,
    "att_vm_reflex_02": 0.32, "att_vm_reflex_east01": 0.25, "att_vm_reflex_east02_tall": 0.23,
    "att_vm_reflex_west02_tall": 0.33, "att_vm_reflex_west03": 0.20, "att_vm_reflex_west04": 0.20,
    "att_vm_scope_mike14": 0.86, "att_vm_scope_vz": 0.95, "att_vm_thermal_east01": 0.95,
    "att_vm_thermal_east01_hybrid": 1.00, "att_vm_thermal_west01": 0.80,
    # Muzzle devices against the factory flash hider (~50 g): hiders the same, compensators and brakes of steel a
    # little heavier. Suppressors take the hider off: a SOCOM556-Mini2 is 0.42 kg, a KAC NT4 0.68.
    "att_vm_flashhider01": 0.0, "att_vm_flashhider02": 0.0, "att_vm_flashhider03": 0.0, "att_vm_flashhider04": 0.0,
    "att_vm_compensator01": 0.03, "att_vm_compensator02": 0.03, "att_vm_muzzlebrake01": 0.06,
    "att_vm_muzzlebrake02": 0.06, "att_vm_muzzlebrake03": 0.08, "att_vm_breacher01": 0.06, "att_vm_breacher02": 0.06,
    "att_vm_silencer01": 0.37, "att_vm_silencer02": 0.52, "att_vm_silencer03": 0.45, "att_vm_silencer04": 0.43,
    "att_vm_silencer05": 0.32, "att_vm_silencer06": 0.63,
    # Lasers with their mounts (a compact green laser 0.1; a PEQ-15-sized module 0.2-0.22).
    "att_vm_p01_ar_mike4_laser01": 0.10, "att_vm_p01_ar_mike4_laser02": 0.22, "att_vm_p01_ar_mike4_laser03": 0.20,
    "attachment_vm_sm_mpapa5_laser01": 0.10, "attachment_vm_sm_mpapa5_laser02": 0.22,
    "attachment_vm_sm_mpapa5_laser03": 0.20,
    # Foregrips: polymer grips 0.05-0.12, a bipod grip 0.3, an M203 with its round 1.6.
    "att_vm_p01_ar_mike4_angledgrip01": 0.06, "att_vm_p01_ar_mike4_angledgrip02": 0.07,
    "att_vm_p01_ar_mike4_bipodgrip": 0.30, "att_vm_p01_ar_mike4_stubbygrip01": 0.06,
    "att_vm_p01_ar_mike4_stubbygrip02": 0.05, "att_vm_p01_ar_mike4_ubgl": 1.60,
    "att_vm_p01_ar_mike4_vertgrip01": 0.10, "att_vm_p01_ar_mike4_vertgrip02": 0.08,
    "att_vm_p01_ar_mike4_vertgrip03": 0.12,
    "attachment_vm_sm_mpapa5_angledgrip01": 0.06, "attachment_vm_sm_mpapa5_angledgrip02": 0.07,
    "attachment_vm_sm_mpapa5_bipodgrip": 0.30, "attachment_vm_sm_mpapa5_stubbygrip01": 0.06,
    "attachment_vm_sm_mpapa5_stubbygrip02": 0.05, "attachment_vm_sm_mpapa5_vertgrip01": 0.10,
    "attachment_vm_sm_mpapa5_vertgrip02": 0.08, "attachment_vm_sm_mpapa5_vertgrip03": 0.12,
}


def loaded(magazine: tuple[float, int], gun: str) -> float:
    empty, rounds = magazine
    return empty + rounds * ROUND_KG[GUN_ROUND[gun]]


def mag_change(gun: str, choice: str, factory: str) -> float:
    table = {**AK_MAGAZINES, **OWN_MAGAZINES.get(gun, {})}
    return loaded(table[choice], gun) - loaded(table[factory], gun)


# The M4A1's parts, against its Standard Carbine Stock, 14.5" barrel, Default Pistol Grip and a loaded USGI 30.
M4_STOCKS = {"ar_mike16_stock_v0": 0.20, "ar_mike4_stock_base": 0.0, "ar_mike4_stockl_v0": -0.05,
             "ar_mike4_stockno_v0": -0.25, "ar_mike4_stocktac_v0": -0.08, "dm_msecho_stock_v0": 0.35,
             "dm_stango25_stock_v0": 0.12, "sm_alpha57_stock_v0": 0.10, "sm_alpha57_stockwire_v0": -0.10}
M4_GRIPS = {"pistolgrip_v0": 0.0, "grpass_v0": 0.0, "grpskel_v0": -0.02, "grpsn_v0": 0.02, "grpstdy_v0": 0.01,
            "grptac_v0": 0.0}
M4_BARRELS = {"barrel_base": 0.0, "barshort_v0": -0.35, "barhvyshort_v0": -0.12, "barmidhvy_v0": -0.05,
              "barhvy_v0": 0.20, "barlight_v0": -0.20, "barlong_v0": 0.15}
# The M16A4's A2 fixed stock is ~0.2 kg over a carbine stock, its 20-inch barrel 0.35 over the 14.5.
M16_STOCK, M16_BARREL = 0.20, 0.35


def explicit() -> dict[str, float]:
    parts = {}
    mw = "gunsmith/m4a1/mw2022/att_vm_p01_"
    for key, kg in M4_STOCKS.items():
        parts[f"{mw}{key}.gnsmth"] = kg
        parts[f"gunsmith/m16/att_vm_p01_{key}.gnsmth"] = round(kg - M16_STOCK, 3)
    for key, kg in M4_GRIPS.items():
        parts[f"{mw}ar_mike4_{key}.gnsmth"] = kg
        parts[f"gunsmith/m16/att_vm_p01_ar_mike4_{key}.gnsmth"] = kg
    for key, kg in M4_BARRELS.items():
        parts[f"{mw}ar_mike4_{key}.gnsmth"] = kg
        parts[f"gunsmith/m16/att_vm_p01_ar_mike4_{key}.gnsmth"] = round(kg - M16_BARREL, 3)
    parts[f"{mw}ar_mike16_barrel_v0.gnsmth"] = M16_BARREL
    m16 = OWN_MAGAZINES["m16"]
    for choice, key in (("standard", "ar_mike4_mag_v0"), ("smag", "ar_mike16_smag_v0"), ("xmag", "ar_mike4_xmag_v0"),
                        ("xmaglrg", "ar_mike4_xmaglrg_v0")):
        kg = round(loaded(m16[choice], "m4a1") - loaded(m16["standard"], "m4a1"), 3)
        parts[f"{mw}{key}.gnsmth"] = kg
        parts[f"gunsmith/m16/att_vm_p01_{key}.gnsmth"] = kg
    usgi30 = loaded((0.117, 30), "m4a1")
    scar30 = loaded((0.30, 30), "scarh")
    mp5_30 = loaded((0.17, 30), "mp5")
    parts.update({
        # M4A1's older parts.
        "gunsmith/m4a1/precision_stock/precision_stock.gnsmth": 0.35,  # a PRS-type stock
        "gunsmith/m4a1/heavy_barrel/heavy_barrel.gnsmth": 0.35,  # heavy 16" barrel and its long rail
        "gunsmith/m4a1/rear_mag/extended_mag.gnsmth": round(loaded((0.18, 40), "m4a1") - usgi30, 3),
        "gunsmith/m4a1/rear_mag/short_mag.gnsmth": round(loaded((0.09, 20), "m4a1") - usgi30, 3),
        "gunsmith/m4a1/rear_mag/rubber_grip.gnsmth": 0.03, "gunsmith/m4a1/rear_mag/taped_grip.gnsmth": 0.01,
        "gunsmith/m4a1/muzzle/compact_suppressor.gnsmth": 0.37, "gunsmith/m4a1/muzzle/rifle_suppressor.gnsmth": 0.57,
        "gunsmith/m4a1/underbarrel/m4a1_underbarrel_foregrip.gnsmth": 0.09,
        "gunsmith/m4a1/underbarrel/m4a1_underbarrel_vertical.gnsmth": 0.10,
        "gunsmith/m4a1/optics/m4a1_optic_eotech.gnsmth": 0.32, "gunsmith/m4a1/optics/m4a1_optic_rmr.gnsmth": 0.10,
        "gunsmith/m4a1/optics/reflex.gnsmth": 0.20, "gunsmith/m4a1/optics/scout.gnsmth": 0.40,
        "gunsmith/m4a1/optics/tube.gnsmth": 0.30,
        # Buffers against the H2's 4.6 oz: Carbine 3.0, H 3.8, H3 5.4.
        "gunsmith/m4a1/action/carbine_buffer.gnsmth": -0.045, "gunsmith/m4a1/action/h_buffer.gnsmth": -0.023,
        "gunsmith/m4a1/action/h3_buffer.gnsmth": 0.023,
        "gunsmith/m4a1/trigger/m4_trigger_group.gnsmth": 0.0, "gunsmith/m16/trigger/m16a3_trigger_group.gnsmth": 0.0,
        "gunsmith/aug/action/suppressed_gas_regulator.gnsmth": 0.0,
        "gunsmith/ammunition/tracer_rounds.gnsmth": 0.0,
        # SCAR-H, against its loaded 30.
        "gunsmith/scarh/rear_mag/extended_mag.gnsmth": round(loaded((0.45, 40), "scarh") - scar30, 3),
        "gunsmith/scarh/rear_mag/short_mag.gnsmth": round(loaded((0.20, 20), "scarh") - scar30, 3),
        "gunsmith/scarh/rear_mag/rubber_grip.gnsmth": 0.03, "gunsmith/scarh/rear_mag/taped_grip.gnsmth": 0.01,
        "gunsmith/scarh/optics/scarh_optic_reflex.gnsmth": 0.20,
        "gunsmith/scarh/barrel/scarh_suppressor.gnsmth": 0.65,
        "gunsmith/hc1/compact_suppressor/compact_suppressor.gnsmth": 0.51,
        "gunsmith/hc1/rifle_suppressor/rifle_suppressor.gnsmth": 0.65,
        "gunsmith/hc1/angled_grip/angled_grip.gnsmth": 0.06, "gunsmith/hc1/vertical_grip/vertical_grip.gnsmth": 0.10,
        # MP5, against the A3's retractable stock, its barrel and a loaded steel 30. The MP5SD is ~0.5 kg over an A3.
        "gunsmith/mpapa5/magazines/magazine_45_round.gnsmth": round(loaded((0.25, 45), "mp5") - mp5_30, 3),
        "gunsmith/mpapa5/stocks/att_vm_stock_heavy01.gnsmth": 0.25,
        "gunsmith/mpapa5/stocks/att_vm_stock_heavy02.gnsmth": 0.10,
        "gunsmith/mpapa5/stocks/att_vm_stock_light01.gnsmth": -0.20,
        "gunsmith/mpapa5/stocks/att_vm_stock_medium01.gnsmth": -0.10,
        "gunsmith/mpapa5/stocks/att_vm_stock_no.gnsmth": -0.30,
        "gunsmith/mpapa5/stocks/stock_classic_full.gnsmth": 0.05,
        "gunsmith/mpapa5/stocks/stock_collapsible.gnsmth": 0.30,
        "gunsmith/mpapa5/barrels/barrel_integral_suppressor.gnsmth": 0.45,
        "gunsmith/mpapa5/barrels/barrel_monolithic_suppressor.gnsmth": 0.55,
        "gunsmith/mpapa5/barrels/barrel_short.gnsmth": -0.08,
        "gunsmith/mpapa5/underbarrel/rail_grip.gnsmth": 0.13,
        # 9 mm cans, on a thread with no hider to take off.
        "gunsmith/mpapa5/muzzles/att_vm_silencer01.gnsmth": 0.26,
        "gunsmith/mpapa5/muzzles/att_vm_silencer02.gnsmth": 0.35,
        "gunsmith/mpapa5/muzzles/att_vm_silencer03.gnsmth": 0.40,
        "gunsmith/mpapa5/muzzles/att_vm_silencer04.gnsmth": 0.30,
        "gunsmith/m700/optics/m700_optic_longrange.gnsmth": 0.40,  # a bigger scope than the factory one
        "gunsmith/usp/barrel/usp_suppressor.gnsmth": 0.30,  # threaded barrel and a 9 mm can
    })
    return parts


EXPLICIT = explicit()
OWN_PART = re.compile(r"gunsmith/([^/]+)/[^/]+/att_vm_p04_(.+)\.gnsmth")


def mass_of(relative: str) -> float:
    """The Mass for the part file at `relative` (under Assets, forward slashes). KeyError if there's no figure."""
    if relative in EXPLICIT:
        return EXPLICIT[relative]
    match = OWN_PART.fullmatch(relative)
    if match and match[1] in W.WEAPONS:
        gun, choice = match[1], match[2]
        for group, choices in W.WEAPONS[gun].part_choices.items():
            names = [name for name, _ in choices]
            if choice not in names:
                continue
            if group == "magazine":
                return round(mag_change(gun, choice, names[0]), 3)
            table = {**AK_CHOICES, **OWN_CHOICES.get(gun, {})}
            return round(table[choice] - table[names[0]], 3)
    return SHARED[Path(relative).stem]


def put(document: dict, relative: str) -> dict:
    """`document` (a part being written, for the file at `relative`) with its Mass after its Category, as `with_mass`
    writes it, or none if it weighs the same as the factory part."""
    kg = mass_of(relative)
    out = {}
    for key, value in document.items():
        if key == "Mass":
            continue
        out[key] = value
        if key == "Category" and kg != 0:
            out["Mass"] = kg
    return out


# Categories whose parts weigh something worth counting (charms, camos and stickers don't).
CATEGORIES = {"Barrel", "Stock", "Underbarrel", "Optic", "Muzzle", "Ammunition", "RearGrip", "Magazine", "Laser",
              "Rail", "Action", "Trigger"}
CATEGORY_NAMES = ["Charm", "Camoflague", "Barrel", "Stock", "Underbarrel", "Optic", "Sticker", "MasteryCamo",
                  "AnimatedCamo", "GlowingCamo", "Reticle", "Camoflague3D", "Muzzle", "Ammunition", "RearGrip",
                  "Magazine", "Laser", "Rail", "Action", "Trigger"]
MASS = re.compile(r'("Mass"\s*:\s*)(-?[0-9.eE+-]+)')
CATEGORY = re.compile(r'([ \t]*)"Category"\s*:\s*[^,\r\n]+,')


def with_mass(text: str, kg: float) -> str:
    """`text` (a part file) with its Mass set to `kg`, in place, leaving the rest of the file as it was."""
    value = f"{kg:g}"
    if MASS.search(text):
        return MASS.sub(lambda m: m[1] + value, text, count=1)
    if kg == 0:
        return text
    match = CATEGORY.search(text)
    newline = "\r\n" if "\r\n" in text else "\n"
    return text[:match.end()] + f'{newline}{match[1]}"Mass": {value},' + text[match.end():]


LOADED_MASS = re.compile(r'("LoadedMass"\s*:\s*)(-?[0-9.eE+-]+)')
SPEED_PENALTY = re.compile(r'([ \t]*)"SpeedPenalty"\s*:')


def with_loaded_mass(text: str, kg: float) -> str:
    """`text` (a weapon prefab) with its Equipment's LoadedMass set to `kg`, before its SpeedPenalty."""
    value = f"{kg:g}"
    if LOADED_MASS.search(text):
        return LOADED_MASS.sub(lambda m: m[1] + value, text, count=1)
    matches = list(SPEED_PENALTY.finditer(text))
    assert len(matches) == 1, "one Equipment with a SpeedPenalty"
    match = matches[0]
    newline = "\r\n" if "\r\n" in text else "\n"
    return text[:match.start()] + f'{match[1]}"LoadedMass": {value},{newline}' + text[match.start():]


def parts():
    for path in sorted((ASSETS / "gunsmith").rglob("*.gnsmth")):
        document = json.loads(path.read_text(encoding="utf-8-sig"))
        category = document.get("Category")
        if isinstance(category, int):
            category = CATEGORY_NAMES[category]
        if category in CATEGORIES:
            yield path, path.relative_to(ASSETS).as_posix()


def main() -> None:
    check = "--check" in sys.argv
    changed, missing = [], []
    for path, relative in parts():
        try:
            kg = mass_of(relative)
        except KeyError:
            missing.append(relative)
            continue
        raw = path.read_bytes()
        bom = raw.startswith(b"\xef\xbb\xbf")
        text = raw.decode("utf-8-sig")
        new = with_mass(text, kg)
        if new == text:
            continue
        changed.append(f"{relative}: {kg:+g} kg")
        if not check:
            path.write_bytes((b"\xef\xbb\xbf" if bom else b"") + new.encode("utf-8"))
    for name, kg in GUN_KG.items():
        path = ASSETS / "Weapons" / f"{name}.prefab"
        raw = path.read_bytes()
        bom = raw.startswith(b"\xef\xbb\xbf")
        text = raw.decode("utf-8-sig")
        new = with_loaded_mass(text, kg)
        if new == text:
            continue
        changed.append(f"Weapons/{name}.prefab: LoadedMass {kg:g} kg")
        if not check:
            path.write_bytes((b"\xef\xbb\xbf" if bom else b"") + new.encode("utf-8"))
    for line in changed:
        print(("would change " if check else "") + line)
    for relative in missing:
        print(f"NO FIGURE     {relative}")
    print(f"{len(changed)} file(s) {'to change' if check else 'changed'}, {len(missing)} part(s) without a figure")
    if missing:
        sys.exit(1)


if __name__ == "__main__":
    main()

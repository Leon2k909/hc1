"""Our names for the attachments ported from Call of Duty rips (the MW2022 M4 parts in Assets/gunsmith/m4a1/mw2022 and
the MW2019 MP5 parts in Assets/gunsmith/mpapa5), by the rip's model key.

The ports keep the rips' file names, because saved builds and build codes refer to parts by path. Players only see
these names, so no CoD brand, model name or number goes in them: each name says what the part is. The AK-family parts
are named in kastov_prefabs.py (PARTS_74U and the rest), under the same rule.

GunsmithAttachmentEffects gives parts their effects by words in the name ("suppressor", "muzzle brake", "compensator",
"flash hider", barrel lengths, "angled", "grip", "support", ...). A new name must keep the part's effect: compare
effect_class() of the old and new names, which follows that code's rules.
"""
from __future__ import annotations

NAMES = {
    # Optics
    "att_vm_2x_west01": "2x Magnifier and Mini Dot",
    "att_vm_2x_west02": "2x Magnifier and Holo",
    "att_vm_2x_west02_holo": "Enclosed Holographic Sight",
    "att_vm_4x_east01_tall": "3x Sunshade Scope",
    "att_vm_4x_west01_tall": "3x Combat Scope",
    "att_vm_4x_west02_tall": "3x Prism Scope",
    "att_vm_holo_east01": "Tube Collimator Sight",
    "att_vm_holo_west01": "Dial Holographic Sight",
    "att_vm_holo_west02": "QD Holographic Sight",
    "att_vm_hybrid_west01": "3x Scope with Top Dot",
    "att_vm_hybrid_west02": "3x Flip Magnifier and Holo",
    "att_vm_hybrid_west02_thermal": "3x Flip Magnifier and Digital Sight",
    "att_vm_hybrid_west03": "3x Prism Scope with Offset Dot",
    "att_vm_minireddot01_tall": "Notched Mini Red Dot",
    "att_vm_minireddot02_tall": "Mini Red Dot",
    "att_vm_minireddot03_tall": "Wide-Window Mini Red Dot",
    "att_vm_reflex_02": "Box Collimator Sight",
    "att_vm_reflex_east01": "Long-Body Reflex Sight",
    "att_vm_reflex_east02_tall": "Ring Reflex Sight",
    "att_vm_reflex_west02_tall": "Tube Red Dot",
    "att_vm_reflex_west03": "Hooded Reflex Sight",
    "att_vm_reflex_west04": "Round-Hood Reflex Sight",
    "att_vm_scope_mike14": "6x Marksman Scope",
    "att_vm_scope_vz": "6x Precision Scope",
    # The thermal-looking optics are plain 3x sights in game, so they aren't called thermal.
    "att_vm_thermal_east01": "3x Digital Scope",
    "att_vm_thermal_east01_hybrid": "3x Digital Scope with Offset Dot",
    "att_vm_thermal_west01": "3x Box Digital Scope",
    # Muzzles
    "att_vm_breacher01": "Crowned Standoff Device",
    "att_vm_breacher02": "Ported Standoff Device",
    "att_vm_compensator01": "Multi-Port Compensator",
    "att_vm_compensator02": "Slotted Compensator",
    "att_vm_flashhider01": "Three-Prong Flash Hider",
    "att_vm_flashhider02": "Ribbed Flash Hider",
    "att_vm_flashhider03": "Crowned Flash Hider",
    "att_vm_flashhider04": "Slotted Flash Hider",
    "att_vm_muzzlebrake01": "Single-Port Muzzle Brake",
    "att_vm_muzzlebrake02": "Two-Port Muzzle Brake",
    "att_vm_muzzlebrake03": "Three-Port Muzzle Brake",
    "att_vm_silencer01": "Slim Suppressor",
    "att_vm_silencer02": "Long Suppressor",
    "att_vm_silencer03": "Wide Suppressor",
    "att_vm_silencer04": "Vented Suppressor",
    "att_vm_silencer05": "Short Suppressor",
    "att_vm_silencer06": "Heavy Suppressor",
    # Underbarrel (the M4's keys; the MP5's copies are below)
    "att_vm_p01_ar_mike4_angledgrip01": "Angled Foregrip",
    "att_vm_p01_ar_mike4_angledgrip02": "Ridged Angled Foregrip",
    "att_vm_p01_ar_mike4_bipodgrip": "Bipod Foregrip",
    "att_vm_p01_ar_mike4_stubbygrip01": "Wide Stubby Foregrip",
    "att_vm_p01_ar_mike4_stubbygrip02": "Stubby Foregrip",
    "att_vm_p01_ar_mike4_vertgrip01": "Ribbed Vertical Foregrip",
    "att_vm_p01_ar_mike4_vertgrip02": "Slotted Vertical Foregrip",
    "att_vm_p01_ar_mike4_vertgrip03": "Tall Vertical Foregrip",
    "att_vm_p01_ar_mike4_ubgl": "40mm Grenade Launcher",
    # Lasers
    "att_vm_p01_ar_mike4_laser01": "Compact Green Laser",
    "att_vm_p01_ar_mike4_laser02": "Green Laser Module",
    "att_vm_p01_ar_mike4_laser03": "Red Laser Module",
    # M4 barrels
    "att_vm_p01_ar_mike16_barrel_v0": '20" Rifle Barrel',
    "att_vm_p01_ar_mike4_barhvy_v0": '14" Heavy Carbine Barrel',
    "att_vm_p01_ar_mike4_barhvyshort_v0": '11.5" Heavy Carbine Barrel',
    "att_vm_p01_ar_mike4_barlight_v0": "Lightweight Free-Float Barrel",
    "att_vm_p01_ar_mike4_barlong_v0": "419mm Free-Float Barrel",
    "att_vm_p01_ar_mike4_barmidhvy_v0": '11.5" Quad-Rail Barrel',
    "att_vm_p01_ar_mike4_barrel_base": '14.5" Free-Float Barrel',
    "att_vm_p01_ar_mike4_barshort_v0": '7.5" Compact Barrel',
    # M4 stocks
    "att_vm_p01_ar_mike16_stock_v0": "Fixed Full Stock",
    "att_vm_p01_ar_mike4_stock_base": "Standard Carbine Stock",
    "att_vm_p01_ar_mike4_stockl_v0": "Open-Frame Carbine Stock",
    "att_vm_p01_ar_mike4_stockno_v0": "Bare Buffer Tube",
    "att_vm_p01_ar_mike4_stocktac_v0": "Minimalist Carbine Stock",
    "att_vm_p01_dm_msecho_stock_v0": "Adjustable Marksman Stock",
    "att_vm_p01_dm_stango25_stock_v0": "Heavy Carbine Stock",
    "att_vm_p01_sm_alpha57_stock_v0": "Telescoping PDW Stock",
    "att_vm_p01_sm_alpha57_stockwire_v0": "Folding Wire Stock",
    # M4 pistol grips
    "att_vm_p01_ar_mike4_grpass_v0": "Stippled Pistol Grip",
    "att_vm_p01_ar_mike4_grpskel_v0": "Skeleton Pistol Grip",
    "att_vm_p01_ar_mike4_grpsn_v0": "Palm Support Grip",
    "att_vm_p01_ar_mike4_grpstdy_v0": "Ribbed Pistol Grip",
    "att_vm_p01_ar_mike4_grptac_v0": "Straight Pistol Grip",
    # MP5 stocks and barrels
    "att_vm_stock_heavy01": "Precision Heavy Stock",
    "att_vm_stock_heavy02": "Heavy Skeleton Stock",
    "att_vm_stock_light01": "Ultralight Stock",
    "att_vm_stock_medium01": "Open-Frame Stock",
    "stock_collapsible": "Collapsible Stock",
    "barrel_monolithic_suppressor": "Railed Suppressor Barrel",
    "rail_grip": "Rail Handguard",
}

# The MP5's copies of the M4's underbarrel parts and lasers.
for _part in ("angledgrip01", "angledgrip02", "bipodgrip", "stubbygrip01", "stubbygrip02", "vertgrip01", "vertgrip02",
              "vertgrip03", "laser01", "laser02", "laser03"):
    NAMES[f"attachment_vm_sm_mpapa5_{_part}"] = NAMES[f"att_vm_p01_ar_mike4_{_part}"]


def name(key: str, fallback: str | None = None) -> str | None:
    """Our name for a ported part, by its model key (a .gnsmth's file name without the extension)."""
    return NAMES.get(key, fallback)


def effect_class(category: str, part_name: str) -> tuple:
    """Which of GunsmithAttachmentEffects' name rules a part gets: Apply's and Describe's branches, in their order."""
    n = part_name.lower()
    suppressor = category in ("Muzzle", "Barrel") and ("suppressor" in n or "silencer" in n)
    branch = None
    if category == "Muzzle":
        branch = next((w for w in ("muzzle brake", "compensator") if w in n), None) or (
            "flash" if "flash guard" in n or "flash hider" in n else None)
    elif category == "Barrel":
        falloff = next((w for w in ('7.5"', '11.5"', "short barrel", '20"', "long", "419mm", "recon barrel") if w in n), None)
        rate = next((w for w in ('7.5"', '11.5"', '20"', "419mm") if w in n), None)
        groups = {'7.5"': "short", '11.5"': "mid", "short barrel": "mid", '20"': "long", "long": "long", "419mm": "long",
                  "recon barrel": "recon"}
        branch = (groups.get(falloff), rate, "short barrel" in n and not ('7.5"' in n or '11.5"' in n))
    elif category == "Stock":
        branch = ("less" if any(w in n for w in ("no stock", "buffer tube")) else
                  "more" if any(w in n for w in ("precision", "full stock", "stalker")) else
                  "light" if any(w in n for w in ("collapsible", "ultralight")) else None)
    elif category == "Underbarrel":
        branch = ("bipod" if "bipod" in n else
                  "angled" if any(w in n for w in ("angled", "commando foregrip", "tactical foregrip")) else
                  "grip" if "grip" in n else None)
    elif category == "RearGrip":
        branch = "rubber" if "rubber" in n or "support" in n else None
    return suppressor, branch

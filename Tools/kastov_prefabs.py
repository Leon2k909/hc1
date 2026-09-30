#!/usr/bin/env python3
"""Write a Kastov-pipeline gun's HC1 prefabs, equipment resource and HUD icon, using the M4A1's as templates. For
the 762:

  Assets/Weapons/Kastov/kastov762.equip
  Assets/Weapons/Kastov/weapon_kastov762.prefab   gameplay components (ammo, shooting, reload, recoil, ADS)
  Assets/Weapons/Kastov/vm_kastov762.prefab       viewmodel: v_kastov + bone-merged HC1 arms
  Assets/Weapons/Kastov/wm_kastov762.prefab       third-person model held in hold_R
  Assets/Weapons/Kastov/mount_kastov762.prefab    holstered model
  Assets/ui/weapons/guns/kastov762_01.png         white silhouette icon, like the other guns
  and adds the gun to the eligible weapons of the gunsmith parts that fit its slots (FITTING_PARTS).
  A gun with part_choices (the 74u) also gets its own parts, one per non-factory choice:
  Assets/gunsmith/<gun>/<folder>/att_vm_p04_<model>.gnsmth

The 74u's gameplay prefab and icon were made by hand (see Prefabs.gameplay), so for it only the prefab's ADS fields
are set.

GUIDs are derived from the template GUIDs, so re-running produces identical files.
Run: python Tools/kastov_prefabs.py [--weapon kastov762|kastov74u|vityaz|rpk|bizon|ak105|vepr12|m16|p90|mp7|uzi|aug|fal|m18]
"""

from __future__ import annotations

import json
import re
import uuid
from copy import deepcopy
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image

import kastov_weapons
from kastov_dmx import rotation_to_quaternion
from kastov_weapons import Weapon

PROJECT = Path(__file__).resolve().parents[1]
ASSETS = PROJECT / "Assets"
M4 = ASSETS / "Weapons" / "M4A1"
MP5 = ASSETS / "Weapons" / "MP5"
USP = ASSETS / "Weapons" / "USP"
EXTRACTED = Path(r"D:\tmp\hc1-mw22-tools\extracted")
NAMESPACE = uuid.UUID("5b0e4f1c-2f7e-4d8a-9a51-7c4f0e2b9d63")
GUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


@dataclass(frozen=True)
class Part:
    """One of a gun's own gunsmith parts: a non-factory choice of a Weapon.part_choices bodygroup.

    Recoil scales are relative to the factory part, from what the real part does (a fixed, heavier stock steadies
    the gun; no stock leaves nothing to brace against), not the addon's game-balance numbers.
    """
    name: str
    description: str
    vertical_recoil: float = 1.0
    horizontal_recoil: float = 1.0
    magazine_capacity: int = 0
    reload_time: float = 1.0
    # A barrel of another length: how far it moves the muzzle (GunsmithPart.MuzzleShift).
    muzzle_shift: tuple[float, float, float] | None = None
    # A magazine of another kind than the factory one (the RPK's box magazines): its reload (a Weapon.reload_variants
    # suffix), and that reload's times, tactical and empty (GunsmithPart.ReloadAnimation, ReloadTime, EmptyReloadTime).
    reload_variant: str | None = None
    reload_times: tuple[float, float] | None = None
    # Other bodygroups the part switches, e.g. a fixed stock hiding the folding stock's hinge (kastov_vmdl.BODY_GROUPS).
    bodygroups: dict[str, int] = field(default_factory=dict)
    optic_bodygroups: dict[str, int] = field(default_factory=dict)
    optic_mount_shift: tuple[float, float, float] | None = None
    rail_optic_aim: tuple[float, float, float] | None = None
    rail_iron_aim: tuple[float, float, float] | None = None
    # A barrel whose own flash hider is shorter than the factory one: how much further back than muzzle_shift (where a
    # muzzle device mounts) its bare muzzle is, where the shots leave it with no device fitted (GunsmithPart.TipShift).
    tip_shift: tuple[float, float, float] | None = None
    # The damage falloff distance against the factory part's, for a part no name rule in GunsmithAttachmentEffects
    # covers (GunsmithPart.DamageFalloffScale): a barrel of another length, by the muzzle energy it gives.
    falloff: float = 1.0
    # False for a choice the real gun can't take (the FAMAS F1 only feeds from its own 25-round magazine): the model
    # keeps the bodygroup, but no gunsmith part is written for it, and a group left with nothing offered gets no slot.
    offered: bool = True

    def effect(self) -> str:
        """The recoil change in words, as the gunsmith lists it."""
        def change(scale: float) -> str:
            return f"{round(abs(1 - scale) * 100)}% {'less' if scale < 1 else 'more'}"
        if self.falloff != 1:
            return (f"Damage falls off {round(abs(1 - self.falloff) * 100)}% "
                    f"{'earlier' if self.falloff < 1 else 'later'} at distance.")
        if self.muzzle_shift:
            # GunsmithAttachmentEffects: a "long" barrel's damage falls off later.
            return "Damage falls off earlier at distance." if self.muzzle_shift[0] < 0 else "Damage falls off later at distance."
        if self.reload_times:
            return f"Reloads in {self.reload_times[0]:g}s ({self.reload_times[1]:g}s when empty)."
        if self.magazine_capacity:
            if self.reload_time == 1:
                return "Standard reload speed."
            return f"Reloads {round(abs(1 - self.reload_time) * 100)}% {'faster' if self.reload_time < 1 else 'slower'}."
        if self.vertical_recoil == self.horizontal_recoil == 1:
            return "No effect on recoil."
        if self.vertical_recoil == self.horizontal_recoil:
            return f"{change(self.vertical_recoil)} recoil.".capitalize()
        parts = [f"{change(scale)} {axis} recoil" for axis, scale in
                 (("vertical", self.vertical_recoil), ("horizontal", self.horizontal_recoil)) if scale != 1]
        return (", ".join(parts) + ".").capitalize()


# part_choices group -> (gunsmith category, folder under Assets/gunsmith/<gun>).
PART_SLOTS = {"stock": ("Stock", "stocks"), "pistol_grip": ("RearGrip", "pistol_grips"),
              "magazine": ("Magazine", "magazines"), "barrel": ("Barrel", "barrels"), "rail": ("Rail", "rails")}

# The 74u's own parts, by part_choices choice. The names are ours, not the addon's CoD ones (see part_names.py). Its
# factory parts are the side-folding skeleton stock, the AK-74 pistol grip and the 30-round magazine.
PARTS_74U = {
    "ar_akilo74_stockno_v0": Part("Stockless", "Stock removed: nothing to brace against the shoulder.", 1.4, 1.4),
    "ar_akilo74_stockskel_v0": Part("Cut-Down Skeleton Stock", "Cut-down skeleton stock. Lighter, with a smaller buttpad.",
                                    1.05, 1.05),
    "ar_akilo_stock_v0": Part("Polymer Folding Stock", "Full-length polymer folding stock with a wider buttpad.",
                              0.92, 0.92),
    "ar_akilo_stockh_v0": Part("Wooden Stock", "Fixed wooden stock. Heavier and rigid.", 0.9, 0.9),
    "ar_akilo_stocktac_v0": Part("Adjustable Tactical Stock", "Adjustable tactical stock with a rubber buttpad.",
                                 0.92, 0.92),
    "ar_akilo_stocktac02_v0": Part("Vented Tactical Stock", "Adjustable tactical stock.", 0.93, 0.93),
    "ar_akilo_stockwire_v0": Part("Wire Stock", "Light wire stock. Flexes and shifts on the shoulder.",
                                  1.05, 1.08),
    "sh_vecho_stock_v0": Part("Strut Stock", "Full-length fixed stock.", 0.92, 0.92),
    "sh_vecho_stocktac_v0": Part("Skeleton Tactical Stock", "Adjustable skeleton tactical stock.", 0.95, 0.95),
    "lm_rkilo_stock_v0": Part("RPK Club-Foot Stock", "The RPK's heavy wooden stock.", 0.88, 0.88),
    "lm_rkilo_stockh_v0": Part("Thumbhole Stock", "Heavy fixed stock with a support hand rest.", 0.85, 0.85),
    "ar_akilo_griptac_v0": Part("Textured Grip", "Textured rubber grip.", 0.98, 0.98),
    "ar_akilo_gripstdy_v0": Part("Palm Swell Grip", "Ergonomic grip with a palm swell.", 0.97, 1.0),
    "ar_akilo_gripass_v0": Part("Slim Stippled Grip", "Slim lightweight grip."),
    "sh_vecho_pgrip_v0": Part("Shotgun Pistol Grip", "Shotgun-style pistol grip."),
    "sh_vecho_gripsnp_v0": Part("Wrist Brace Grip", "Grip with an extended backstrap that braces the wrist.", 0.96, 0.97),
    "ar_akilo105_smag_v0": Part("20 Round Mag", "Short 20-round magazine. Lighter and quicker to seat.",
                                magazine_capacity=20, reload_time=0.95),
    "ar_akilo105_xmag_v0": Part("45 Round Mag", "RPK-74 45-round magazine. Longer and heavier to change.",
                                magazine_capacity=45, reload_time=1.08),
}

# The AK platform parts the Vityaz shares with the 74u, plus the 74u's factory stock.
_KASTOVIA_PARTS = {**PARTS_74U, "ar_akilo74_stock_v0": Part("AKS-74U Folding Stock", "The AKS-74U's side-folding skeleton stock.")}
_VITYAZ_CHOICES = kastov_weapons.VITYAZ.part_choices


def _relative_to(factory: Part, part: Part) -> Part:
    """A part's recoil relative to another factory part than the 74u's."""
    return replace(part, vertical_recoil=round(part.vertical_recoil / factory.vertical_recoil, 2),
                   horizontal_recoil=round(part.horizontal_recoil / factory.horizontal_recoil, 2))


# The Vityaz's own parts. Its factory stock is the polymer folding stock, so the stocks' recoil is relative to that; its factory
# grip is the 74u's.
PARTS_VITYAZ = {
    **{choice: _relative_to(PARTS_74U["ar_akilo_stock_v0"], _KASTOVIA_PARTS[choice])
       for choice, _ in _VITYAZ_CHOICES["stock"][1:]},
    **{choice: _KASTOVIA_PARTS[choice] for choice, _ in _VITYAZ_CHOICES["pistol_grip"][1:]},
    "sm_aviktor_xmag_v0": Part("45 Round Mag", "Extended 9mm magazine. Longer and heavier to change.",
                               magazine_capacity=45, reload_time=1.08),
    # port_kastov: the long barrel's brake (barlong_tip.smd) sits 5.433 ahead of the factory one (bartip.smd).
    "sm_aviktor_barlightlong_v0": Part("Long Barrel",
                                       "Longer barrel under the factory handguard, with the same muzzle brake.",
                                       muzzle_shift=(5.433, 0.0, 0.0)),
}


# The RPK's own parts. Its factory stock is the RPK's wooden one, so the stocks' recoil is relative to that; its grips
# are the 74u's. The RPK's stocktac and stockar are the AK's adjustable tactical and polymer folding stocks on an RPK adapter. The box
# magazines reload with their own animations, far quicker than the drum (Ammo is back in at the clips' "ready" frames,
# like the drum's, and the last foley plays just before).
_RPK_CHOICES = kastov_weapons.RPK.part_choices
_RPK_PARTS = {**_KASTOVIA_PARTS,
              "lm_rkilo_stocktac_v0": replace(PARTS_74U["ar_akilo_stocktac_v0"],
                                              description="Adjustable tactical stock with a rubber buttpad, on an RPK adapter."),
              "lm_rkilo_stockar_v0": replace(PARTS_74U["ar_akilo_stock_v0"],
                                             description="Full-length polymer folding stock, on an RPK adapter.")}
PARTS_RPK = {
    **{choice: _relative_to(PARTS_74U["lm_rkilo_stock_v0"], _RPK_PARTS[choice])
       for choice, _ in _RPK_CHOICES["stock"][1:]},
    **{choice: _KASTOVIA_PARTS[choice] for choice, _ in _RPK_CHOICES["pistol_grip"][1:]},
    "ar_akilo_mag_v0": Part("30 Round Mag", "The AKM's 30-round steel magazine. Much quicker to change than the drum.",
                            magazine_capacity=30, reload_variant="_mag", reload_times=(2.2, 2.6)),
    "ar_akilo_xmag_v0": Part("40 Round Mag", "The RPK's own 40-round box magazine. Quicker to change than the drum.",
                             magazine_capacity=40, reload_variant="_xmag", reload_times=(2.3, 2.8)),
}


# The Bizon's own parts: the AK platform stocks and grips. Its factory stock is the 74u's (the AKS-74U's), so their recoil
# is the 74u's.
PARTS_BIZON = {choice: _KASTOVIA_PARTS[choice] for group in kastov_weapons.BIZON.part_choices.values()
               for choice, _ in group[1:]}


# The AK-105's own parts. Its factory stock is the AK-74M's side-folding polymer stock, as the polymer folding stock
# part is, so the stocks' recoil is relative to that; its grips are the 74u's, and the 74u's factory grip is one of
# them. The wooden and thumbhole stocks hide the folding stock's hinge block, as the addon's do (tag_stock_hinge). The
# other magazines reload with their own animations: Ammo is back in once the gun is level again.
_AK105_CHOICES = kastov_weapons.AK105.part_choices
_AK105_GRIPS = {**_KASTOVIA_PARTS, "ar_akilo_pstlgrp_v0": Part("AK-74 Pistol Grip", "The AK-74's standard pistol grip.")}
PARTS_AK105 = {
    **{choice: replace(_relative_to(PARTS_74U["ar_akilo_stock_v0"], _KASTOVIA_PARTS[choice]),
                       bodygroups={"stock_hinge": 1} if choice in ("ar_akilo_stockh_v0", "lm_rkilo_stockh_v0") else {})
       for choice, _ in _AK105_CHOICES["stock"][1:]},
    **{choice: _AK105_GRIPS[choice] for choice, _ in _AK105_CHOICES["pistol_grip"][1:]},
    "ar_akilo105_smag_v0": Part("20 Round Mag", "Short 20-round magazine. Lighter and quicker to seat.",
                                magazine_capacity=20, reload_variant="_smag", reload_times=(2.05, 2.3)),
    "ar_akilo105_xmag_v0": Part("45 Round Mag", "RPK-74 45-round magazine. Longer and heavier to change.",
                                magazine_capacity=45, reload_variant="_xmag", reload_times=(2.4, 2.75)),
    "ar_akilo105_xmaglrg_v0": Part("60 Round Mag", "Four-column 60-round magazine. Heavier and slower to change.",
                                   magazine_capacity=60, reload_variant="_xmaglrg", reload_times=(2.5, 2.8)),
}


# The Vepr-12's own parts. Its factory stock is the strut stock, so the stocks' recoil is relative to that; its factory
# grip, the shotgun pistol grip, has the 74u's grips' baseline. The 12-round magazine and the drum reload with their own
# animations: Ammo is back in once the left hand is back on the grip (the clips' grip-pose events).
_VEPR12_CHOICES = kastov_weapons.VEPR12.part_choices
PARTS_VEPR12 = {
    **{choice: _relative_to(PARTS_74U["sh_vecho_stock_v0"], _KASTOVIA_PARTS[choice])
       for choice, _ in _VEPR12_CHOICES["stock"][1:]},
    **{choice: _AK105_GRIPS[choice] for choice, _ in _VEPR12_CHOICES["pistol_grip"][1:]},
    "sh_vecho_xmag_v0": Part("12 Round Mag", "The Vepr-12's 12-round box magazine. Longer and heavier to change.",
                             magazine_capacity=12, reload_variant="_xmag", reload_times=(2.67, 3.27)),
    "sh_vecho_drummag_v0": Part("25 Round Drum", "25-round drum. Much heavier and slower to change.",
                                magazine_capacity=25, reload_variant="_drummag", reload_times=(3.17, 4.2)),
}


# The Uzi's own parts. Its factory stock is the folding metal stock, extended, so the stocks' recoil is relative to that:
# folded under the receiver it braces nothing, like the 74u's Stockless; the early Uzis' short fixed wooden stock is the
# 74u's Wooden Stock. Both longer magazines reload with the xmag clips, whose hand is back on the grip at the same frames
# as the factory reload's.
PARTS_UZI = {
    "sm_uzulu_stock_folded": Part("Folded Stock", "Stock folded under the receiver: nothing to brace against the shoulder.",
                                  1.4, 1.4),
    "sm_uzulu_stockh": PARTS_74U["ar_akilo_stockh_v0"],
    "sm_uzulu_xmags": Part("40 Round Mag", "40-round magazine. Sticks out further below the grip.",
                           magazine_capacity=40, reload_variant="_xmag", reload_times=(2.53, 3.23)),
    "sm_uzulu_xmag2": Part("50 Round Mag", "50-round magazine. Long and heavy, well below the grip.",
                           magazine_capacity=50, reload_variant="_xmag", reload_times=(2.53, 3.23)),
}

# The M18's own parts, by part_choices choice. Its factory parts are the coyote slide and the 17-round magazine. A P320
# takes any P320 slide, and SIG sells them in black. The Army issues the M18 with 21-round magazines as well, which
# reload with the pack's xmag clips: the gun is level again at 1.57 s, and 2.13 s empty (measured like the factory
# reload's). Left out: the vented slide and the long slide with its compensator (CoD's), and the 32-round magazine
# (no real P320 magazine holds 32; SIG's longest holds 21).
PARTS_M18 = {
    "pi_papa320_slide_black": Part("Black Slide", "SIG's black Nitron slide, for a two-tone pistol."),
    "pi_papa320_slide_vented": Part("Vented Slide", "", offered=False),
    "pi_papa320_barrel_ext": Part("Long Slide", "", offered=False),
    "pi_papa320_mag_ext": Part("21 Round Mag", "The Army's 21-round extended magazine. Sticks out below the grip.",
                               magazine_capacity=21, reload_variant="_xmag", reload_times=(1.57, 2.13)),
    "pi_papa320_mag_ext2": Part("32 Round Mag", "", offered=False),
}


@dataclass(frozen=True)
class Gameplay:
    """A generated gameplay prefab's values, on the M4's prefab: fields by component type (Equipment is on the root,
    the rest on Functions). `borrow` first copies the named fields from another gun's gameplay prefab, and `remove`
    takes the M4's components off Functions (a pistol's has no FovOffset shot kick)."""
    fields: dict[str, dict]
    borrow: tuple[Path, dict[str, list[str]]] | None = None
    remove: tuple[str, ...] = ()


# The 762's sounds, and reload foley at the CoD reload's sound-event frames (30 fps).
SOUNDS_762 = "sounds/weapons/kastov"
RELOAD_SOUNDS = {0: "reload_01", 12: "reload_02", 36: "reload_03", 72: "reload_04", 78: "reload_05"}
EMPTY_RELOAD_SOUNDS = {0: "reload_empty_01", 8: "reload_empty_02", 38: "reload_empty_03", 41: "reload_empty_04",
                       69: "reload_empty_05", 72: "reload_empty_06", 86: "reload_empty_07"}


def sound_times(frames: dict[int, str]) -> dict[str, str]:
    return {f"{round(frame / 30, 3):g}": f"{SOUNDS_762}/kastov_{name}.sound" for frame, name in frames.items()}


def ballistics(velocity: float, drag: str, coefficient: float, sight_mm: float, zero: float,
               bullet: tuple[float, float]) -> dict:
    """Shootable's real bullet path (Shootable.Ballistics.cs): the load's muzzle velocity from this barrel (m/s), its
    bullet's ballistic coefficient for the G1 or G7 drag function, the sights' height over the bore, the gun's zero (m)
    and the bullet's diameter and length (mm, one of the loads below), which set its supersonic crack (BulletFlyby.cs)."""
    return {"MuzzleVelocity": velocity, "DragFunction": drag, "BallisticCoefficient": coefficient,
            "SightHeight": round(sight_mm / 25.4, 2), "ZeroRange": zero,
            "BulletDiameter": bullet[0], "BulletLength": bullet[1]}


# Bullets' diameters and lengths (mm), from the loads' drawings and published dimensions.
M855_BULLET = (5.70, 23.0)      # 5.56x45 M855, 62 gr
M193_BULLET = (5.70, 19.0)      # 5.56x45 M193, 55 gr
PS_BULLET = (7.92, 26.8)        # 7.62x39 PS (57-N-231)
N7N6_BULLET = (5.60, 25.5)      # 5.45x39 7N6
M80_BULLET = (7.82, 28.7)       # 7.62x51 M80, 147 gr
NINE_BULLET = (9.02, 15.5)      # 9x19, 124 gr FMJ
M1152_BULLET = (9.02, 14.7)     # 9x19 M1152, 115 gr FMJ
MAKAROV_BULLET = (9.27, 11.5)   # 9x18 57-N-181S
SS190_BULLET = (5.70, 21.6)     # 5.7x28 SS190
DM11_BULLET = (4.65, 16.5)      # 4.6x30 DM11 (the length is an estimate)
BUCK_00_BALL = (8.38, 8.38)     # 00 buckshot: a sphere


# 7.62x39 PS (57-N-231): G7 0.149 fits the AKM manual's (1970) velocity table, and with a ~50 mm sight height (not
# published) reproduces its trajectory table to ~1 cm. The AKM's and RPK's battle zero is sight 3 (the AKM's "П"): the
# path crosses the line of sight again at 300 m, 25 cm high at 100 m.
PS_BALLISTICS = {"drag": "G7", "coefficient": 0.149, "sight_mm": 50, "zero": 300, "bullet": PS_BULLET}


def gameplay_762() -> Gameplay:
    return Gameplay({
        "WeaponAmmo": {"Ammo": 30, "MaxAmmo": 30},
        # The AKM's 415 mm barrel: 715 m/s.
        "Shootable": {"BaseDamage": 26, "FireRate": 600, "ShootSound": f"{SOUNDS_762}/kastov_shot.sound",
                      "SuppressedShootSound": f"{SOUNDS_762}/kastov_shot_sup.sound",
                      "SupportedFireModes": ["Automatic", "Semi"], "CurrentFireMode": "Automatic",
                      **ballistics(715, **PS_BALLISTICS)},
        # Ammo is back in at the CoD reloads' "ready" frames (74 and 91); the last foley plays just before.
        "Reloadable": {"ReloadTime": 2.65, "EmptyReloadTime": 3.05, "TimedReloadSounds": sound_times(RELOAD_SOUNDS),
                       "EmptyReloadSounds": sound_times(EMPTY_RELOAD_SOUNDS)},
        "ShootRecoil": {"Scale": "2.4,5.8"},  # a little more kick than the M4's 2,5
    })


def gameplay_vityaz() -> Gameplay:
    """A 9mm SMG like the MP5: its damage, falloff, range, 9mm effects, recoil pattern, view punch and move speed."""
    assets = load(ASSETS / "Weapons" / "Vityaz" / "vityaz_assets.json")
    sounds = assets["sounds"]

    def times(timed: dict[str, str]) -> dict[str, str]:
        return {f"{float(time):g}": sound for time, sound in timed.items()}

    return Gameplay(
        {
            "WeaponAmmo": {"Ammo": 30, "MaxAmmo": 30},
            # The real Vityaz's cyclic rate (700-750 rpm); automatic and semi, no burst.
            # 9x19 from its 237 mm barrel: 380 m/s (cartridge not stated), modelled as 124 gr ball (Hornady FMJ-RN, G1
            # 0.145). Its sight height and zero weren't found: ~55 mm, and 100 m like the MP5's (estimates).
            "Shootable": {"FireRate": 750, "ShootSound": sounds["fire"],
                          "SuppressedShootSound": sounds["fire_suppressed"],
                          "SupportedFireModes": ["Automatic", "Semi"], "CurrentFireMode": "Automatic",
                          **ballistics(380, "G1", 0.145, 55, 100, NINE_BULLET)},
            # Ammo is back in once the gun is level again (2.5s, and 3.2s after the empty reload's bolt pull).
            "Reloadable": {"ReloadTime": 2.5, "EmptyReloadTime": 3.1,
                           "TimedReloadSounds": times(assets["reload_sounds"]),
                           "EmptyReloadSounds": times(assets["empty_reload_sounds"])},
            # A straight blowback 9mm with a heavier bolt than the MP5's roller delay: a little more kick.
            "ShootRecoil": {"Scale": "0.5,3"},
        },
        borrow=(MP5 / "weapon_mp5.prefab", {
            "Equipment": ["SpeedPenalty"],
            "Shootable": ["BaseDamage", "BaseDamageFalloff", "MaxRange", "EjectionPrefab", "MuzzleFlashPrefab",
                          "MuzzleFlashScale", "MuzzleSmokeScale", "SuppressorFireRateScale"],
            "ShootRecoil": ["RecoilPattern", "HorizontalSpread", "VerticalSpread"],
            "ViewPunch": ["AnglesOffset", "Curve", "Lifetime", "MaxAnglesOffset", "MaxPositionOffset",
                          "PositionOffset"],
        }),
    )


def gameplay_bizon() -> Gameplay:
    """The Vityaz's 9mm SMG values (the MP5's damage, falloff, range, effects, recoil pattern, view punch and move
    speed) with the Bizon's own cartridge, rate, magazine and recoil."""
    assets = load(ASSETS / "Weapons" / "Bizon" / "bizon_assets.json")
    sounds = assets["sounds"]
    return Gameplay(
        {
            # The 64-round helical magazine of the 9x18mm Makarov Bizon.
            "WeaponAmmo": {"Ammo": 64, "MaxAmmo": 64},
            # Its cyclic rate in 9x18 (680 rpm); automatic and semi, no burst. 57-N-181S ball from the 230 mm barrel:
            # 320 m/s, modelled as a 95 gr FMJ (Sellier & Bellot, G1 0.122). The sights sit 51 mm over the bore (the
            # model's sight line), and the flip rear sight's longer setting is 100 m.
            "Shootable": {"FireRate": 680, "ShootSound": sounds["fire"],
                          "SuppressedShootSound": sounds["fire_suppressed"],
                          "SupportedFireModes": ["Automatic", "Semi"], "CurrentFireMode": "Automatic",
                          **ballistics(320, "G1", 0.122, 51, 100, MAKAROV_BULLET)},
            # Ammo is back in once the gun is level again (2.1s, and 2.8s after the empty reload's bolt pull).
            "Reloadable": {"ReloadTime": 2.1, "EmptyReloadTime": 2.8,
                           "TimedReloadSounds": assets["reload_sounds"],
                           "EmptyReloadSounds": assets["empty_reload_sounds"]},
            # Free recoil against the Vityaz's (0.5,3): a 9x18 round (6.1 g at 320 m/s) from a 2.1 kg gun kicks it back
            # at ~0.95 m/s, a 9x19 round (8 g at 380 m/s) from the 2.9 kg Vityaz at ~1.1 m/s.
            "ShootRecoil": {"Scale": "0.43,2.6"},
        },
        borrow=(MP5 / "weapon_mp5.prefab", {
            "Equipment": ["SpeedPenalty"],
            "Shootable": ["BaseDamage", "BaseDamageFalloff", "MaxRange", "EjectionPrefab", "MuzzleFlashPrefab",
                          "MuzzleFlashScale", "MuzzleSmokeScale", "SuppressorFireRateScale"],
            "ShootRecoil": ["RecoilPattern", "HorizontalSpread", "VerticalSpread"],
            "ViewPunch": ["AnglesOffset", "Curve", "Lifetime", "MaxAnglesOffset", "MaxPositionOffset",
                          "PositionOffset"],
        }),
    )


def rpk_reload_sounds() -> dict[str, dict[str, str]]:
    """Each RPK reload clip's timed foley (rpk_assets.py)."""
    return load(ASSETS / "Weapons" / "RPK" / "rpk_assets.json")["reloads"]


def gameplay_rpk() -> Gameplay:
    """The 762's cartridge, shot and damage from a heavier gun with a longer barrel, fed from the 75-round drum."""
    reloads = rpk_reload_sounds()
    return Gameplay({
        # A rifle's penalty, and the real slowdown of the RPK's extra weight: 6.8 kg with a loaded drum against the
        # AKM's 3.75 kg (the manuals), and loads slow soldiers' 30 m sprints by 0.8% and 6 m rushes by 1.1% per kg
        # (Hunt et al. 2016, Ergonomics): 3.05 kg x ~1% = 3%.
        "Equipment": {"SpeedPenalty": 40, "WeightSlowdown": 0.03},
        "WeaponAmmo": {"Ammo": 75, "MaxAmmo": 75},
        # The real RPK's cyclic rate; automatic and semi. Its 590 mm barrel: 745 m/s (the 1964 manual).
        "Shootable": {"BaseDamage": 26, "FireRate": 600, "ShootSound": f"{SOUNDS_762}/kastov_shot.sound",
                      "SuppressedShootSound": f"{SOUNDS_762}/kastov_shot_sup.sound",
                      "SupportedFireModes": ["Automatic", "Semi"], "CurrentFireMode": "Automatic",
                      **ballistics(745, **PS_BALLISTICS)},
        # Ammo is back in once the drum is seated and the gun level (4.25s), and after the bolt pull (5.05s) when empty.
        "Reloadable": {"ReloadTime": 4.25, "EmptyReloadTime": 5.05, "TimedReloadSounds": reloads["reload"],
                       "EmptyReloadSounds": reloads["reload_empty"]},
        # The same cartridge as the 762 from a gun ~1.5 kg heavier: less kick.
        "ShootRecoil": {"Scale": "2,4.8"},
        # Rapid fire takes an M16/M4 barrel to ~430 C (800 F) in 140 rounds, ~3 C a round, and the RPK's heavier barrel
        # lasted 1,232 rounds of continuous fire against the M4A1's 596 before bursting: ~1.5 C a round (~0.85 kJ, 15% of
        # a PS round's 1.6 g of powder, into a ~1.2 kg barrel, which loses ~1 W/K to the air: 10 minutes to cool by e).
        # That keeps the RPK manual's limits (150 rounds in a minute, 200 in 3, 300 in 5) at 215-355 C. An RPK-profile
        # barrel showed no shift in point of impact at ~200 C above the air; past that the groups open to ~1 MOA more by
        # ~410 C, where the US Army found a chambered round cooks off within 10 s (a guess: no study measured the spread).
        "BarrelHeat": {"HeatPerShot": 1.5, "CoolingTime": 600, "DispersionStart": 200, "HotTemperature": 410,
                       "HotDispersion": 0.3, "CookOffTemperature": 410, "CookOffTime": 10},
    })


def ak105_reload_sounds() -> dict[str, dict[str, str]]:
    """Each AK-105 reload clip's timed foley (ak105_assets.py)."""
    return load(ASSETS / "Weapons" / "AK105" / "ak105_assets.json")["reloads"]


def gameplay_ak105() -> Gameplay:
    """The real AK-105's figures (the AK-102/104/105 manual) on the M4's prefab, with the 5.45mm round doing the M4's
    5.56 damage like the AKS-74U's."""
    sounds = load(ASSETS / "Weapons" / "AK105" / "ak105_assets.json")["sounds"]
    reloads = ak105_reload_sounds()
    return Gameplay({
        # 3.5 kg with a loaded magazine, the M4's 3.4 kg: the rifles' penalty and no WeightSlowdown.
        "Equipment": {"SpeedPenalty": 40},
        "WeaponAmmo": {"Ammo": 30, "MaxAmmo": 30},
        # 600 rpm cyclic; automatic and semi. 7N6 ball leaves the 314 mm barrel at 840 m/s (G7 0.157). The front post
        # sits 48.5 mm over the bore, and the gun is zeroed at sight 3 hitting 16 cm high at 100 m, which crosses the
        # line of sight again at 300 m.
        "Shootable": {"BaseDamage": 20, "FireRate": 600, "ShootSound": sounds["fire"],
                      "SuppressedShootSound": sounds["fire_suppressed"],
                      "SupportedFireModes": ["Automatic", "Semi"], "CurrentFireMode": "Automatic",
                      **ballistics(840, "G7", 0.157, 48.5, 300, N7N6_BULLET)},
        # Ammo is back in once the gun is level again (2.3s, and 2.6s after the empty reload's bolt pull).
        "Reloadable": {"ReloadTime": 2.3, "EmptyReloadTime": 2.6, "TimedReloadSounds": reloads["reload"],
                       "EmptyReloadSounds": reloads["reload_empty"]},
        # Free recoil against the M4's (2,5): a 7N6 round (3.4 g at 840 m/s, 1.45 g of powder) kicks the loaded 3.5 kg
        # AK-105 back at ~1.43 m/s, an M855 round the loaded M4 at ~1.86 m/s.
        "ShootRecoil": {"Scale": "1.54,3.85"},
    })


def vepr12_reload_sounds() -> dict[str, dict[str, str]]:
    """Each Vepr-12 reload clip's timed foley (vepr12_assets.py)."""
    return load(ASSETS / "Weapons" / "Vepr12" / "vepr12_assets.json")["reloads"]


def curve(keys: list[tuple[float, float, float]]) -> list[dict]:
    """A Curve's frames from (x, y, slope) keys, with smooth handles stored the way the editor stores them (in = -out)."""
    return [{"x": x, "y": y, "in": -slope + 0.0, "out": slope, "mode": "Mirrored"} for x, y, slope in keys]


# 00 buckshot's damage along its path is the pellets' kinetic energy, as Ballistics.cs's sphere model flies them from
# 365 m/s (BC 0.071): 68% at 25 m, 49% at 50 m, 29% at 100 m and 11% at 200 m, where they stop (MaxRange). Keys every
# 12.5-50 m, with the energy's slope as their tangents, follow it to within 0.1%.
BUCKSHOT_RANGE = 200
BUCKSHOT_FALLOFF = curve([(0, 1, -3.317), (0.0625, 0.819, -2.497), (0.125, 0.683, -1.909), (0.1875, 0.577, -1.493),
                          (0.25, 0.494, -1.194), (0.375, 0.371, -0.802), (0.5, 0.287, -0.57), (0.75, 0.177, -0.335),
                          (1, 0.111, -0.206)])


def gameplay_vepr12() -> Gameplay:
    """The real Vepr-12's figures with 2 3/4" 00 buckshot, and the Spaghelli's pellet damage and shotgun effects."""
    sounds = load(ASSETS / "Weapons" / "Vepr12" / "vepr12_assets.json")["sounds"]
    reloads = vepr12_reload_sounds()
    return Gameplay(
        {
            # 4.8 kg with a loaded 8-round magazine against the AKM's 3.75 kg: ~1% slower, as for the RPK.
            "Equipment": {"SpeedPenalty": 40, "WeightSlowdown": 0.01, "CrosshairType": "Shotgun"},
            "WeaponAmmo": {"Ammo": 8, "MaxAmmo": 8},
            # Semi-automatic only. A 12-gauge Kalashnikov action cycles at ~450 rpm (the Saiga-12's, converted to fully
            # automatic), which caps how fast the trigger can be pulled. Nine 8.4 mm, 3.49 g pellets at 365 m/s from the
            # 305 mm barrel. A cylinder bore throws them in a ~49 cm pattern at 25 yd (~0.021 rad across; Shootable's
            # spread puts nine pellets 0.82 x BulletSpread apart on average). The sights sit 48.7 mm over the bore (the
            # model's sight line), zeroed at 25 m like the other buckshot guns. Semi only, so a suppressor's back-pressure
            # wouldn't change how fast it fires (it takes none, having no Muzzle slot).
            "Shootable": {"BulletCount": 9, "BulletSpread": 0.026, "FireRate": 450, "SuppressorFireRateScale": 1,
                          "MaxRange": round(BUCKSHOT_RANGE * 39.3701), "BaseDamageFalloff": BUCKSHOT_FALLOFF,
                          "ShootSound": sounds["fire"], "SupportedFireModes": ["Semi"], "CurrentFireMode": "Semi",
                          **ballistics(365, "Sphere", 0.071, 48.7, 25, BUCK_00_BALL)},
            # Ammo is back in once the left hand is back on the grip (the clips' grip-pose events: 2.3s, and 2.87s after
            # the empty reload's bolt pull).
            "Reloadable": {"ReloadTime": 2.3, "EmptyReloadTime": 2.87, "TimedReloadSounds": reloads["reload"],
                           "EmptyReloadSounds": reloads["reload_empty"]},
            # Free recoil against the M4's (2,5): 00 buck (34 g of shot and wad at 365 m/s, 1.8 g of powder) kicks the
            # loaded 4.8 kg gun back at ~2.8 m/s, an M855 round the loaded M4 at ~1.86 m/s.
            "ShootRecoil": {"Scale": "3,7.6"},
            "ScreenShakeOnShot": {"Length": 0.2, "Size": 4},
        },
        borrow=(ASSETS / "Weapons" / "Spaghelli" / "weapon_spaghelli.prefab", {
            "Shootable": ["BaseDamage", "EjectionPrefab", "MuzzleFlashPrefab", "MuzzleFlashChance", "MuzzleFlashScale",
                          "MuzzleSmokePrefab", "MuzzleSmokeScale"],
            "ViewPunch": ["AnglesOffset", "Curve", "Lifetime", "MaxAnglesOffset", "MaxPositionOffset",
                          "PositionOffset"],
            "FovOffset": ["Curve", "Length", "Size"],
        }),
    )


def m16_reload_sounds() -> dict[str, dict[str, str]]:
    """Each M16A4 reload clip's timed foley (m16_assets.py)."""
    return load(ASSETS / "Weapons" / "M16" / "m16_assets.json")["reloads"]


def gameplay_m16() -> Gameplay:
    """The real M16A4's figures on the M4's prefab: the M4's M855 round (its damage, falloff and recoil pattern) from a
    20-inch barrel, semi-automatic and in three-round bursts."""
    sounds = load(ASSETS / "Weapons" / "M16" / "m16_assets.json")["sounds"]
    reloads = m16_reload_sounds()
    return Gameplay({
        # ~4.0 kg with a loaded 30-round magazine, 0.6 kg over the M4: the rifles' penalty, and too little over the
        # AKM's 3.75 kg for a WeightSlowdown (~0.25%).
        "Equipment": {"SpeedPenalty": 40},
        "WeaponAmmo": {"Ammo": 30, "MaxAmmo": 30},
        # 800 rpm cyclic, the middle of the M16's 700-900. Semi-automatic and three-round burst, no automatic: a trigger
        # pull fires one burst (Shootable.OnInputUpdate), and the next can follow as fast as the cyclic rate allows.
        # M855 leaves the 20-inch barrel at 945 m/s (3,100 ft/s; the M4's at 905), G7 0.151 like the M4's. The sights
        # sit 68.5 mm over the bore (the model's sight line through the carry handle's aperture), zeroed at 300 m.
        "Shootable": {"BaseDamage": 20, "FireRate": 800, "ShootSound": sounds["fire"],
                      "SuppressedShootSound": sounds["fire_suppressed"],
                      "SupportedFireModes": ["Semi", "Burst"], "CurrentFireMode": "Semi", "BurstAmount": 3,
                      "BurstEndDelay": 0, **ballistics(945, "G7", 0.151, 68.5, 300, M855_BULLET)},
        # Ammo is back in once the gun is level again (2.3s, and 2.4s after the empty reload's bolt release).
        "Reloadable": {"ReloadTime": 2.3, "EmptyReloadTime": 2.4, "TimedReloadSounds": reloads["reload"],
                       "EmptyReloadSounds": reloads["reload_empty"]},
        # Free recoil against the M4's (2,5): an M855 round (4.02 g at 945 m/s, 1.7 g of powder) kicks the loaded
        # ~4.0 kg M16A4 back at ~1.65 m/s, the loaded M4 at ~1.86 m/s.
        "ShootRecoil": {"Scale": "1.78,4.44"},
    })


def gameplay_p90() -> Gameplay:
    """The real P90's figures (FN's data sheets) with SS190 ball, and the Vityaz's 9mm SMG values for the rest (the
    MP5's damage, falloff, range, effects, recoil pattern, view punch and move speed)."""
    assets = load(ASSETS / "Weapons" / "P90" / "p90_assets.json")
    sounds, reloads = assets["sounds"], assets["reloads"]
    return Gameplay(
        {
            # The 50-round magazine lying along the top of the gun.
            "WeaponAmmo": {"Ammo": 50, "MaxAmmo": 50},
            # 900 rpm, the figure usually quoted (FN's sheet gives 850-1,100); automatic and semi. SS190 ball leaves the
            # 264 mm barrel at 715 m/s (FN). No BC is published for its 2.0 g (31 gr) bullet: G1 0.155 is the pointed
            # 40 gr V-MAX's form factor (Hornady's G1 0.200; FN's SS197SR bullet) at the SS190's sectional density. The
            # sights sit 101 mm over the bore (the model's sight line, above the magazine and the top rail), zeroed at
            # 100 m like the other SMGs.
            "Shootable": {"FireRate": 900, "ShootSound": sounds["fire"],
                          "SuppressedShootSound": sounds["fire_suppressed"],
                          "SupportedFireModes": ["Automatic", "Semi"], "CurrentFireMode": "Automatic",
                          **ballistics(715, "G1", 0.155, 101, 100, SS190_BULLET)},
            # Ammo is back in once the left hand is back on the grip (the clips' grip-pose events: 2.53s, and 2.93s
            # after the empty reload's charging handle) and the reload's last foley has played.
            "Reloadable": {"ReloadTime": 2.55, "EmptyReloadTime": 3.05, "TimedReloadSounds": reloads["reload"],
                           "EmptyReloadSounds": reloads["reload_empty"]},
            # Free recoil against the Vityaz's (0.5,3): an SS190 round (2.0 g at 715 m/s, ~0.43 g of powder) kicks the
            # loaded 3.1 kg P90 back at ~0.64 m/s, a 9x19 round the 2.9 kg Vityaz at ~1.1 m/s.
            "ShootRecoil": {"Scale": "0.29,1.73"},
        },
        borrow=(MP5 / "weapon_mp5.prefab", {
            "Equipment": ["SpeedPenalty"],
            "Shootable": ["BaseDamage", "BaseDamageFalloff", "MaxRange", "EjectionPrefab", "MuzzleFlashPrefab",
                          "MuzzleFlashScale", "MuzzleSmokeScale", "SuppressorFireRateScale"],
            "ShootRecoil": ["RecoilPattern", "HorizontalSpread", "VerticalSpread"],
            "ViewPunch": ["AnglesOffset", "Curve", "Lifetime", "MaxAnglesOffset", "MaxPositionOffset",
                          "PositionOffset"],
        }),
    )


def gameplay_mp7() -> Gameplay:
    """The real MP7A1's figures with DM11 ball, and the Vityaz's 9mm SMG values for the rest (the MP5's damage, falloff,
    range, effects, recoil pattern, view punch and move speed)."""
    assets = load(ASSETS / "Weapons" / "MP7" / "mp7_assets.json")
    sounds, reloads = assets["sounds"], assets["reloads"]
    return Gameplay(
        {
            # The 40-round magazine in the pistol grip.
            "WeaponAmmo": {"Ammo": 40, "MaxAmmo": 40},
            # H&K's 950 rpm; automatic and semi. DM11 ball (a 2.0 g copper-plated steel bullet) leaves the 180 mm barrel
            # at 720 m/s, G1 ~0.141-0.150. The sights sit 73.5 mm over the bore (the model's sight line through the
            # flip-up rear sight), zeroed at 100 m like the other SMGs (the MP7's own zero wasn't found).
            "Shootable": {"FireRate": 950, "ShootSound": sounds["fire"],
                          "SuppressedShootSound": sounds["fire_suppressed"],
                          "SupportedFireModes": ["Automatic", "Semi"], "CurrentFireMode": "Automatic",
                          **ballistics(720, "G1", 0.145, 73.5, 100, DM11_BULLET)},
            # Ammo is back in once the gun is level again (2.1s, and 2.17s after the empty reload's bolt release).
            "Reloadable": {"ReloadTime": 2.1, "EmptyReloadTime": 2.17, "TimedReloadSounds": reloads["reload"],
                           "EmptyReloadSounds": reloads["reload_empty"]},
            # Free recoil against the Vityaz's (0.5,3): a DM11 round (2.0 g at 720 m/s, ~0.4 g of powder, a guess from
            # the case's capacity) kicks the 1.9 kg MP7A1 with a loaded 40-round magazine (~2.3 kg) back at ~0.85 m/s,
            # a 9x19 round the 2.9 kg Vityaz at ~1.1 m/s.
            "ShootRecoil": {"Scale": "0.38,2.3"},
        },
        borrow=(MP5 / "weapon_mp5.prefab", {
            "Equipment": ["SpeedPenalty"],
            "Shootable": ["BaseDamage", "BaseDamageFalloff", "MaxRange", "EjectionPrefab", "MuzzleFlashPrefab",
                          "MuzzleFlashScale", "MuzzleSmokeScale", "SuppressorFireRateScale"],
            "ShootRecoil": ["RecoilPattern", "HorizontalSpread", "VerticalSpread"],
            "ViewPunch": ["AnglesOffset", "Curve", "Lifetime", "MaxAnglesOffset", "MaxPositionOffset",
                          "PositionOffset"],
        }),
    )


def uzi_reload_sounds() -> dict[str, dict[str, str]]:
    """Each Uzi reload clip's timed foley (uzi_assets.py)."""
    return load(ASSETS / "Weapons" / "Uzi" / "uzi_assets.json")["reloads"]


def gameplay_uzi() -> Gameplay:
    """The real Uzi's figures with 9x19 ball, and the Vityaz's 9mm SMG values for the rest (the MP5's damage, falloff,
    range, effects, recoil pattern and view punch)."""
    sounds = load(ASSETS / "Weapons" / "Uzi" / "uzi_assets.json")["sounds"]
    reloads = uzi_reload_sounds()
    return Gameplay(
        {
            # 3.5-3.7 kg empty with the metal stock (sources differ), ~4.2 kg with a loaded 32-round magazine: more
            # than the M4, so the rifles' penalty rather than the MP5's, and too little over the AKM's 3.75 kg for a
            # WeightSlowdown (~0.45%).
            "Equipment": {"SpeedPenalty": 40},
            # The 32-round magazine in the pistol grip.
            "WeaponAmmo": {"Ammo": 32, "MaxAmmo": 32},
            # 600 rpm cyclic from the open bolt; automatic and semi. 9x19 ball leaves the 260 mm barrel at 400 m/s,
            # modelled as 124 gr ball (G1 0.145) like the Vityaz's. The sights sit 47 mm over the bore (the model's sight
            # line through the rear aperture and the front post's tip, 309 mm apart like the real gun's), zeroed at
            # 100 m: the flip rear sight's 100 m aperture.
            "Shootable": {"FireRate": 600, "ShootSound": sounds["fire"],
                          "SuppressedShootSound": sounds["fire_suppressed"],
                          "SupportedFireModes": ["Automatic", "Semi"], "CurrentFireMode": "Automatic",
                          **ballistics(400, "G1", 0.145, 47, 100, NINE_BULLET)},
            # When the gun is level again in its own clips (tag_sling back within 4 degrees and 0.6 of idle, relative to
            # the camera): 2.53s, and 3.23s after the empty reload's cocking knob pull. The grip-pose events come earlier
            # (2.3s and 2.97s), with the gun still tilted 12 and 27 degrees. The xmag clips level it at the same times.
            "Reloadable": {"ReloadTime": 2.53, "EmptyReloadTime": 3.23, "TimedReloadSounds": reloads["reload"],
                           "EmptyReloadSounds": reloads["reload_empty"]},
            # Free recoil against the Vityaz's (0.5,3): a 9x19 round (8 g at 400 m/s, ~0.4 g of powder) kicks the loaded
            # ~4.2 kg Uzi back at ~0.83 m/s, the 2.9 kg Vityaz at ~1.1 m/s.
            "ShootRecoil": {"Scale": "0.38,2.26"},
        },
        borrow=(MP5 / "weapon_mp5.prefab", {
            "Shootable": ["BaseDamage", "BaseDamageFalloff", "MaxRange", "EjectionPrefab", "MuzzleFlashPrefab",
                          "MuzzleFlashScale", "MuzzleSmokeScale", "SuppressorFireRateScale"],
            "ShootRecoil": ["RecoilPattern", "HorizontalSpread", "VerticalSpread"],
            "ViewPunch": ["AnglesOffset", "Curve", "Lifetime", "MaxAnglesOffset", "MaxPositionOffset",
                          "PositionOffset"],
        }),
    )


def gameplay_aug() -> Gameplay:
    """The real Steyr AUG A3's figures with the 16-inch barrel: the M4's M855 round (its damage, falloff and recoil
    pattern)."""
    assets = load(ASSETS / "Weapons" / "AUG" / "aug_assets.json")
    sounds, reloads = assets["sounds"], assets["reloads"]
    return Gameplay({
        # 3.3 kg empty with the 16-inch barrel, ~3.8 kg with a loaded 30-round magazine: the rifles' penalty, and too
        # little over the AKM's 3.75 kg for a WeightSlowdown.
        "Equipment": {"SpeedPenalty": 40},
        "WeaponAmmo": {"Ammo": 30, "MaxAmmo": 30},
        # 715 rpm, the middle of Steyr's 680-750; automatic and semi (the real gun's two-stage trigger fires semi on
        # the first stage and automatic when pulled through). M855 leaves the 407 mm (16-inch) barrel at ~916 m/s,
        # between the M4's 905 from 14.5 inches and the M16A4's 945 from 20 (Steyr quotes 970 m/s from its 508 mm
        # barrel), G7 0.151 like theirs. The sights sit 61.7 mm over the bore (the model's sight line through the
        # flip-up sights on the top rail), zeroed at 300 m like the other M855 rifles.
        "Shootable": {"BaseDamage": 20, "FireRate": 715, "ShootSound": sounds["fire"],
                      "SuppressedShootSound": sounds["fire_suppressed"],
                      "SupportedFireModes": ["Automatic", "Semi"], "CurrentFireMode": "Automatic",
                      **ballistics(916, "G7", 0.151, 61.7, 300, M855_BULLET)},
        # Ammo is back in once the left hand is back on the foregrip (the clips' grip-pose events: 1.83s, and 2.97s
        # after the empty reload's charging handle), after the reload's last foley.
        "Reloadable": {"ReloadTime": 1.83, "EmptyReloadTime": 2.97, "TimedReloadSounds": reloads["reload"],
                       "EmptyReloadSounds": reloads["reload_empty"]},
        # Free recoil against the M4's (2,5): an M855 round (4.02 g at 916 m/s, 1.7 g of powder) kicks the loaded
        # ~3.8 kg AUG back at ~1.69 m/s, the loaded M4 at ~1.86 m/s.
        "ShootRecoil": {"Scale": "1.81,4.53"},
    })


def gameplay_fal() -> Gameplay:
    """The real FN FAL 50.00's figures (FN's manual) with 7.62x51 M80 ball, and the SCAR-H's bigger muzzle flash. The
    falloff, recoil pattern and view punch are the M4's, as the SCAR-H's are."""
    assets = load(ASSETS / "Weapons" / "FAL" / "fal_assets.json")
    sounds, reloads = assets["sounds"], assets["reloads"]
    return Gameplay(
        {
            # 4.25 kg empty, ~5.0 kg with a loaded 20-round magazine (0.25 kg and 20 rounds of 25.4 g) against the
            # AKM's 3.75 kg: ~1% slower per kg, as for the RPK.
            "Equipment": {"SpeedPenalty": 40, "WeightSlowdown": 0.0125},
            "WeaponAmmo": {"Ammo": 20, "MaxAmmo": 20},
            # 675 rpm, the middle of FN's 650-700; semi and automatic, starting on semi, as armies fired it. M80 ball
            # leaves the 533 mm (21-inch) barrel at 840 m/s, G7 0.200 like the SCAR-H's. Its muzzle energy (3,362 J)
            # against M855's from the M4 (1,646 J) scales the M4's damage 20 to 41, so in hardcore a body hit at full
            # damage always kills. The sights sit 48.6 mm over the bore (the model's sight line through the rear
            # aperture and the front post's tip), zeroed at 200 m: the rear sight's lowest setting, the battle zero.
            # A suppressor doesn't speed it up: its gas regulator is set for the gun as it's fitted (FN's procedure closes
            # it click by click until the bolt just locks back, then two clicks more), so a can's back-pressure is taken out.
            "Shootable": {"BaseDamage": 41, "FireRate": 675, "SuppressorFireRateScale": 1, "ShootSound": sounds["fire"],
                          "SuppressedShootSound": sounds["fire_suppressed"],
                          "SupportedFireModes": ["Semi", "Automatic"], "CurrentFireMode": "Semi",
                          **ballistics(840, "G7", 0.200, 48.6, 200, M80_BULLET)},
            # When the gun is level again in its own clips (tag_sling back within 4 degrees and 0.6 of idle, relative to
            # the camera): 2.67s, and 3.4s after the empty reload's charging handle.
            "Reloadable": {"ReloadTime": 2.67, "EmptyReloadTime": 3.4, "TimedReloadSounds": reloads["reload"],
                           "EmptyReloadSounds": reloads["reload_empty"]},
            # Free recoil against the M4's (2,5): an M80 round (9.53 g at 840 m/s, 2.98 g of powder) kicks the loaded
            # ~5.0 kg FAL back at ~2.48 m/s, an M855 round the loaded M4 at ~1.86 m/s.
            "ShootRecoil": {"Scale": "2.66,6.66"},
        },
        borrow=(ASSETS / "Weapons" / "ScarH" / "weapon_scarh.prefab", {
            "Shootable": ["MuzzleFlashChance", "MuzzleFlashScale"],
        }),
    )


def gameplay_famas() -> Gameplay:
    assets = load(ASSETS / "Weapons/FAMAS/famas_assets.json")
    sounds, reloads = assets["sounds"], assets["reloads"]
    return Gameplay({
        "Equipment": {"SpeedPenalty": 40},
        "WeaponAmmo": {"Ammo": 25, "MaxAmmo": 25},
        # French Army F1: 25 rounds, 1,000 rpm, 930 m/s. BC/recoil/zero are game tuning.
        "Shootable": {"BaseDamage": 20, "FireRate": 1000, "ShootSound": sounds["fire"],
                      "SuppressedShootSound": sounds["fire_suppressed"],
                      "SupportedFireModes": ["Automatic", "Burst", "Semi"], "CurrentFireMode": "Automatic",
                      "BurstAmount": 3, "BurstEndDelay": 0,
                      **ballistics(930, "G1", .243, 80, 300, M193_BULLET)},
        "Reloadable": {"ReloadTime": 2.3, "EmptyReloadTime": 2.8,
                       "TimedReloadSounds": reloads["reload"], "EmptyReloadSounds": reloads["reload_empty"]},
        "ShootRecoil": {"Scale": "1.9,4.7"},
    })


def m18_reload_sounds() -> dict[str, dict[str, str]]:
    """Each M18 reload clip's timed foley (p320_assets.py)."""
    return load(ASSETS / "Weapons" / "M18" / "m18_assets.json")["reloads"]


def gameplay_m18() -> Gameplay:
    """The real SIG Sauer M18's figures with 9x19 M1152 ball. The damage and falloff are the 9mm guns' (the MP5's),
    with the falloff distance cut by the short barrel's muzzle energy, as a shorter barrel part's is. The pistol
    handling is the USP's: its hold, crosshair, move speed, recoil without a pattern, view punch, 9mm casing and
    pistol flash, and no FovOffset shot kick."""
    sounds = load(ASSETS / "Weapons" / "M18" / "m18_assets.json")["sounds"]
    reloads = m18_reload_sounds()
    mp5 = component(find(load(MP5 / "weapon_mp5.prefab")["RootObject"], "Functions"), "Shootable")
    return Gameplay(
        {
            # About 0.75 kg with an empty magazine and 0.95 kg loaded: the pistols' penalty.
            "Equipment": {"HoldType": "Pistol", "CrosshairType": "ThreeLines", "SpeedPenalty": 20},
            # The 17-round magazine.
            "WeaponAmmo": {"Ammo": 17, "MaxAmmo": 17},
            # Semi only. A pistol fires as fast as its trigger is pulled, so FireRate is the shortest split, 0.13 s, as
            # for the USP, and a suppressor wouldn't change it. M1152 ball (115 gr FMJ) leaves the 3.9-inch barrel at ~375 m/s, G1 0.14. The sights sit
            # 16 mm over the bore (the model's front post and rear notch against the barrel's axis), zeroed at 25 m like
            # the other pistols. That's 524 J against the MP5's 643 J (124 gr at 400 m/s), so damage falls off over
            # 0.815 of its distance (MaxRange 8000).
            "Shootable": {"BaseDamage": mp5["BaseDamage"], "BaseDamageFalloff": mp5["BaseDamageFalloff"],
                          "MaxRange": round(mp5["MaxRange"] * 0.815), "FireRate": 450, "SuppressorFireRateScale": 1,
                          "ShootSound": sounds["fire"],
                          "SupportedFireModes": ["Semi"], "CurrentFireMode": "Semi",
                          **ballistics(375, "G1", 0.14, 16, 25, M1152_BULLET)},
            # When the gun is level again in its own clips (tag_sling back within 4 degrees and 0.6 of idle, relative to
            # the camera): 1.57 s, and 2.1 s after the empty reload's slide release.
            "Reloadable": {"ReloadTime": 1.57, "EmptyReloadTime": 2.1, "TimedReloadSounds": reloads["reload"],
                           "EmptyReloadSounds": reloads["reload_empty"]},
            # Free recoil against the USP's .45 (230 gr at 255 m/s from ~1.14 kg loaded, ~3.5 m/s): the loaded M18 is
            # kicked back at ~3.2 m/s, 0.93 of it.
            "ShootRecoil": {"VerticalSpread": "1.86", "HorizontalSpread": "1.3 -1.3"},
        },
        borrow=(USP / "weapon_usp.prefab", {
            "Shootable": ["EjectionPrefab", "MuzzleFlashPrefab", "MuzzleFlashChance", "MuzzleFlashScale",
                          "MuzzleSmokeScale"],
            "ShootRecoil": ["UseRecoilPattern", "RecoilPattern", "HorizontalSpread", "VerticalSpread"],
            "ViewPunch": ["AnglesOffset", "Curve", "Lifetime", "MaxAnglesOffset", "MaxPositionOffset",
                          "PositionOffset"],
        }),
        remove=("FovOffset",),
    )


@dataclass(frozen=True)
class Prefabs:
    """The HC1 side of a gun: its equipment resource, prefabs and gunsmith mounts."""
    title: str
    description: str
    price: int
    deploy_sound: str
    # The addon's spawn icon the HUD icon is drawn from: a VTF under EXTRACTED, without the extension. None keeps
    # the existing icon.
    icon_source: str | None
    # A renderer's BodyGroups is its mesh-group mask: the models' Parts.DefaultMask (body and muzzle tip shown, rails
    # hidden; see kastov_vmdl.BODY_GROUPS). Read it again from the compiled model if the bodygroups change.
    default_mesh_groups: int
    # Viewmodel bone objects the prefab references (name -> parent, local position, local rotation x y z w), from
    # the v_ model's bind pose. The renderer's CreateBoneObjects adopts them and drives them with the animation.
    bones: dict[str, tuple[str | None, str, str]]
    # World model points (port_kastov.py prints them): muzzle and ejection port.
    world_muzzle: str
    world_eject: str
    # Where the third-person left wrist goes (LeftHandIK, turned by WORLD_LEFT_HAND_ROTATION): 3.5 left of the
    # handguard's right side, 1.19 under its bottom and 3.9 behind where the index finger should reach, which puts the
    # palm under the handguard and the fingers round its right side. Checked in offscreen renders of the player model.
    # None for a pistol: its hold type has no left-hand IK, like the USP's and 1911's.
    world_left_hand: str | None
    # Gunsmith slots taking the M4's MW22 parts: category, where the part's origin goes on the gun (world model space,
    # which is also the viewmodel's bind space; the parts reach forward from their origin), where it sits on the M4
    # (the parts' BindPosition), and the bodygroups a fitted part switches on. In first person the parts follow
    # MOUNT_BONE; the world model has no such bone, so they mount on the model itself.
    slots: list[tuple[str, tuple, tuple, dict[str, int]]]
    # Charms hang from their slot's own transform, so the viewmodel's slot rides on the tag_sling bone object: the left
    # side of the receiver, above the pistol grip. None: no charm slot (the pistols have none).
    charm: tuple[float, float, float] | None
    # Optic ADS offsets are calibrated on the M4; this moves them to the gun's sight line (ManualOffset).
    optic_aim_correction: str
    # The gameplay prefab's values; None when the prefab exists already, and only its ADS fields are written.
    gameplay: Callable[[], Gameplay] | None
    category: str = "AssaultRifle"
    kill_reward: int = 300
    # The bind pose puts the grip where the M4's is; raise the gun to sit at the M4's height in the gunsmith.
    gunsmith_offset: str = "0,0,4"
    # Salts the derived GUIDs, keeping each gun's prefabs apart (the 762's predate it).
    guid_salt: str = ""
    # The gun's own parts (Part), by Weapon.part_choices choice, and where each part_choices group's slot sits (world
    # model space; the gunsmith frames the slot there).
    parts: dict[str, Part] = field(default_factory=dict)
    part_slot_positions: dict[str, tuple[float, float, float]] = field(default_factory=dict)
    # A part_choices group slot's FittedBodygroups, e.g. a longer barrel showing its own muzzle tip
    # (Weapon.tip_choices).
    part_slot_bodygroups: dict[str, dict[str, int]] = field(default_factory=dict)
    # Each reload clip's timed foley, for parts with their own reload (Part.reload_variant).
    reload_sounds: Callable[[], dict[str, dict[str, str]]] | None = None
    # LeftHandIK's rotation when the left hand doesn't hold a handguard (the AUG's vertical foregrip); None is
    # WORLD_LEFT_HAND_ROTATION.
    world_left_hand_rotation: str | None = None
    # The sticker's flat patch (GunsmithSticker), on the left side, which the gunsmith and first person show: its
    # centre and outward normal in world model space (the viewmodel's bind space), and its width and height. The
    # viewmodel's slot rides the tag_sling bone object, like the charm's. None: no sticker slot.
    sticker: tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float]] | None = None
    # The viewmodel bone object the sticker rides (one of `bones`): a pistol's slide, so it moves with the slide.
    sticker_bone: str = "tag_sling"
    # What hasn't been checked in-game yet, shown by the gun's name in the gunsmith to the developer only
    # (EquipmentResource.ReviewNote). Empty once it's all been checked.
    review_note: str = ""
    # Per optic, where the eye moves and how the gun turns ("x,y,z", "pitch,yaw,roll") to co-witness the optic's dot
    # with iron sights it leaves up (ManualOffset.OpticSightLines): (optic resource path, position, angles).
    optic_sight_lines: list[tuple[str, str, str]] = field(default_factory=list)
    # The equipment resource's other fields over the M4's: a pistol's Slot and armour penetration.
    equip_fields: dict = field(default_factory=dict)
    # The share of the icon's width the gun spans: 0.9 like the M4's, less for a pistol (the USP's spans 0.35).
    icon_width: float = 0.9


PARTS_AK47 = {
    "ak47_stock_adjustable": Part("Polymer Folding Stock", "Full-length polymer stock with a receiver adapter.", .96, .96,
                                  bodygroups={"stock_adapter": 1}),
    "ak47_stock_heavy": Part("Heavy Wooden Stock", "Rigid wooden stock with a broad shoulder rest.", .90, .90),
    "ak47_stock_padded": Part("Adjustable Stock", "Adjustable stock with a padded shoulder rest.", .92, .92),
    "ak47_stock_light": Part("Lightweight Skeleton Stock", "Open-frame stock with a receiver adapter.", 1.04, 1.04,
                             bodygroups={"stock_adapter": 1}),
    "ak47_stock_delete": Part("Stock Delete", "Rear mounting plate with the shoulder stock removed.", 1.4, 1.4),
    "ak47_stock_tactical": Part("Tactical Stock", "Full-length tactical stock.", .95, .95),
    "ak47_grip_contoured": Part("Contoured Grip", "Shaped pistol grip with a palm swell.", .97, 1),
    "ak47_grip_textured": Part("Textured Grip", "Textured pistol grip for a firm hold.", .98, .98),
    "ak47_grip_skeleton": Part("Skeleton Grip", "Open-frame pistol grip."),
    "ak47_mag_polymer": Part("30 Round Polymer Magazine", "Polymer 7.62 magazine.", magazine_capacity=30),
    "ak47_mag_extended": Part("40 Round Extended Magazine", "Long 7.62 box magazine.", magazine_capacity=40,
                               reload_variant="_xmag", reload_times=(3.0, 3.4)),
    "ak47_mag_drum": Part("75 Round Drum", "Large 7.62 drum magazine.", magazine_capacity=75,
                           reload_variant="_dmag", reload_times=(3.4, 4.4)),
    "ak47_barrel_compact": Part("Short Barrel", "Compact barrel retaining the wooden handguard.",
                                muzzle_shift=(-4.976562, 0, 0)),
}

PREFABS = {
    "kastov762": Prefabs(
        title="AK-47",
        description="Hard-hitting 7.62 assault rifle. Fires slower and kicks harder than the M4.",
        price=2700,
        deploy_sound="sounds/weapons/kastov/kastov_raise.sound",
        icon_source="3803722029/materials/vgui/entities/mg_mw4_ak47",
        default_mesh_groups=340002817,
        bones={
            "tag_sling": (None, "-4.673,0,4.129", "0,0,0,1"),
            "tag_barrel_attach": ("tag_sling", "9.391,0.001,0.47", "0,0,0,1"),
            "muzzle": ("tag_barrel_attach", "15.828,0,0", "0,0,0,1"),
            "tag_brass": ("tag_sling", "7.148,-0.636,1.023", "0.000049,0.000049,-0.707038,0.707175"),
        },
        world_muzzle="20.546,0,4.599",
        world_eject="2.476,-0.636,5.152",
        world_left_hand="7.3,2.82,2.39",  # the front of the handguard
        slots=[
            ("Optic", (-2.45, 0, 6.302), (0.25, 0, 8.73), {"optic_rail": 1}),  # on the side-mount rail (-4.2 to 2.2)
            ("Muzzle", (18.515, 0, 4.599), (17.62, 0, 7.4147), {"muzzle_tip": 2}),  # tag_tip, for the slant brake
            ("Underbarrel", (8.55, 0, 3.127), (8.3, 0, 6.2), {"grip_rail": 1}),  # the front of the bottom rail (6.5 to 10.6)
            ("Laser", (7.35, -1.131, 5.14), (8.6, -1.22, 7.4147), {"laser_rail": 1}),  # on the right-side rail (7.4 to 10.1)
        ],
        charm=(0.0, 1.75, 2.3),
        sticker=((1.5204, 0.705, 4.7312), (-0.0003, 0.9977, -0.0684), (1.4, 0.7)),
        # Measured in-game: puts the camera where it sits relative to a fitted optic on the M4 (dev_optic_correction
        # to retune).
        optic_aim_correction="4.084,0,-1.208",
        gameplay=gameplay_762,
        parts=PARTS_AK47,
        part_slot_positions={"stock": (-6, 0, 3.5), "pistol_grip": (-2, 0, 1),
                             "magazine": (3, 0, -1), "barrel": (12, 0, 4.6)},
        part_slot_bodygroups={"barrel": {"muzzle_tip": 1}},
        reload_sounds=lambda: load(ASSETS / "Weapons" / "Kastov" / "kastov_attachment_assets.json")["reloads"],
    ),
    "kastov74u": Prefabs(
        title="AKS-74U",
        description="Compact carbine. Fast fire rate, hits hard up close, falls off at range.",
        price=2300,
        deploy_sound="weapons/kastov74u/sounds/ks74u.raise.sound",
        icon_source=None,
        # The rails' mask plus the factory stock, grip and magazine (read from the compiled model).
        default_mesh_groups=605028693,
        bones={
            "tag_sling": (None, "-6.971,-0.573,3.351", "0,0,0,1"),
            "tag_barrel_attach": ("tag_sling", "11.839,0.573,2.436", "0,0,0,1"),
            "muzzle": ("tag_barrel_attach", "8.378,0,-1.398", "0,0,0,1"),
            "tag_brass": ("tag_sling", "9.103,-0.17,1.884", "0.00001,0.00001,-0.707094,0.707119"),
        },
        world_muzzle="13.246,0,4.389",
        world_eject="2.132,-0.743,5.235",
        world_left_hand="5.4,2.72,2.07",  # the front of the handguard
        slots=[
            ("Optic", (-2.2, 0, 6.311), (0.25, 0, 8.73), {"optic_rail": 1}),  # on the side-mount rail (-4.3 to 0.25)
            ("Muzzle", (10.264, 0, 4.383), (17.62, 0, 7.4147), {"muzzle_tip": 1}),  # tag_tip, for the muzzle booster
            ("Underbarrel", (8.1, 0, 3.107), (8.3, 0, 6.2), {"grip_rail": 1}),  # the front of the bottom rail (5.6 to 10.2)
            ("Laser", (7.44, -1.092, 5.382), (8.6, -1.22, 7.4147), {"laser_rail": 1}),  # tag_laser_attach (rail 7.45 to 10)
        ],
        charm=(0.0, 1.75, 2.3),
        sticker=((2.554, 0.6918, 4.1779), (0.001, 1.0, -0.0018), (1.4, 0.7)),
        # The 762's measured correction moved by how far the 74u's ADS pose puts its optic slot from the 762's
        # (port_kastov: Kastov.ads, the slot through tag_sling). Tune in-game with dev_optic_correction.
        optic_aim_correction="3.162,0,-1.226",
        gameplay=None,
        guid_salt="kastov74u/",
        parts=PARTS_74U,
        # port_kastov.py's world stock, grip and mag points (tag_stock_attach, tag_pistolgrip_attach, tag_mag_attach).
        part_slot_positions={"stock": (-5.716, 0, 3.649), "pistol_grip": (-3.0, 0, 3.0), "magazine": (2.516, 0, 3.257)},
    ),
    "vityaz": Prefabs(
        title="PP-19-01 Vityaz",
        description="Russian 9x19mm submachine gun built on the AK-74. Straight blowback, 30-round magazine.",
        price=1500,
        deploy_sound="weapons/vityaz/sounds/vityaz.raise.sound",
        icon_source="3499492742/materials/vgui/entities/mg_iw9_aviktor",
        # The muzzle tip (factory, the long barrel's, none) and the factory stock, grip, magazine and barrel.
        default_mesh_groups=22036489,
        bones={
            "tag_sling": (None, "-6.971,-0.573,3.351", "0,0,0,1"),
            "tag_barrel_attach": ("tag_sling", "11.839,0.573,2.436", "0,0,0,1"),
            "muzzle": ("tag_barrel_attach", "6.943,0,-1.398", "0,0,0,1"),
            "tag_brass": ("tag_sling", "7.791,-0.17,1.884", "0.000007,0.000011,-0.707094,0.707119"),
        },
        world_muzzle="11.811,0,4.389",
        world_eject="0.82,-0.743,5.235",
        world_left_hand="5.6,2.7,1.95",  # the front of the handguard, like the 74u's
        slots=[
            ("Optic", (-2.748, 0, 6.136), (0.25, 0, 8.73), {}),  # tag_reflex, on the top rail (-4.5 to 2.3)
            # tag_tip, for the brake. A fitted device hides either barrel's brake (choice 2 beats the barrel slot's 1).
            ("Muzzle", (10.264, 0, 4.383), (17.62, 0, 7.4147), {"muzzle_tip": 2}),
            ("Underbarrel", (7.15, 0, 3.113), (8.3, 0, 6.2), {}),  # the front of the bottom rail (5.25 to 9.25)
            ("Laser", (7.44, -1.06, 4.484), (8.6, -1.22, 7.4147), {}),  # tag_laser_attach (right-side flat 7.5 to 9.25)
        ],
        charm=(0.0, 1.75, 2.3),
        sticker=((1.492, 0.6747, 3.719), (-0.0012, 1.0, -0.0022), (1.6, 0.8)),
        # The 762's measured correction moved by how far the Vityaz's ADS pose puts its optic slot from the 762's,
        # like the 74u's. Tune in-game with dev_optic_correction.
        optic_aim_correction="1.728,0,-1.172",
        gameplay=gameplay_vityaz,
        category="SMG",
        kill_reward=600,
        guid_salt="vityaz/",
        parts=PARTS_VITYAZ,
        # port_kastov.py's world stock, grip and mag points, and the middle of the barrels.
        part_slot_positions={"stock": (-5.716, 0, 3.649), "pistol_grip": (-3.0, 0, 3.0), "magazine": (2.516, 0, 3.257),
                             "barrel": (8.5, 0, 4.4)},
        part_slot_bodygroups={"barrel": {"muzzle_tip": 1}},
    ),
    "rpk": Prefabs(
        title="RPK",
        description="Soviet 7.62x39mm light machine gun: an AKM with a longer, heavier barrel and a 75-round drum.",
        price=3200,
        deploy_sound="weapons/rpk/sounds/rpk.raise_rattle.sound",
        icon_source="3499492742/materials/vgui/entities/mg_iw9_rkilo",
        # The brake and the factory stock, grip and drum; the rails hidden.
        default_mesh_groups=2363477,
        bones={
            "tag_sling": (None, "-6.969,-0.573,3.351", "0,0,0,1"),
            "tag_barrel_attach": ("tag_sling", "13.313,0.572,2.527", "0,0,0,1"),
            "muzzle": ("tag_barrel_attach", "20.063,0,-1.494", "0,0,0,1"),
            "tag_brass": ("tag_sling", "9.103,-0.17,1.884", "-0.000021,0.000057,-0.707106,0.707107"),
        },
        world_muzzle="26.407,0,4.384",
        world_eject="2.134,-0.743,5.235",
        world_left_hand="7.1,2.7,2.03",  # the front of the handguard
        slots=[
            ("Optic", (-2.2, 0, 6.311), (0.25, 0, 8.73), {"optic_rail": 1}),  # on the side-mount rail (-4.27 to 0.26), like the 74u's
            ("Muzzle", (25.602, 0, 4.384), (17.62, 0, 7.4147), {"muzzle_tip": 1}),  # the brake's rear face
            ("Underbarrel", (9.4, 0, 2.831), (8.3, 0, 6.2), {"grip_rail": 1}),  # the front of the bottom rail (5.93 to 11.52)
            ("Laser", (10.337, -1.085, 4.375), (8.6, -1.22, 7.4147), {}),  # tag_laser_attach, at the short right-side rail
        ],
        charm=(0.0, 1.75, 2.3),
        sticker=((2.9812, 0.6872, 3.7138), (0.0, 1.0, -0.0084), (1.4, 0.7)),
        # The 762's measured correction moved by how far the RPK's ADS pose puts its optic slot from the 762's, like the
        # 74u's. Tune in-game with dev_optic_correction.
        optic_aim_correction="3.326,0,-1.426",
        gameplay=gameplay_rpk,
        category="LMG",
        guid_salt="rpk/",
        parts=PARTS_RPK,
        # port_kastov.py's world stock, grip and mag points (tag_stock_attach, tag_pistolgrip_attach, tag_mag_attach).
        part_slot_positions={"stock": (-5.714, 0, 3.649), "pistol_grip": (-3.0, 0, 3.0), "magazine": (2.516, 0, 3.257)},
        reload_sounds=rpk_reload_sounds,
    ),
    "bizon": Prefabs(
        title="PP-19 Bizon",
        description="Russian 9x18mm submachine gun built on the AKS-74. Straight blowback, fed from a 64-round "
                    "helical magazine under the barrel.",
        price=1400,
        deploy_sound="weapons/bizon/sounds/bizon.raise.sound",
        icon_source="3499492742/materials/vgui/entities/mg_iw9_beta",
        # The muzzle nut and the factory stock and grip; the side rail hidden.
        default_mesh_groups=2129941,
        bones={
            "tag_sling": (None, "-6.972,-0.573,3.352", "0,0,0,1"),
            "tag_barrel_attach": ("tag_sling", "11.84,0.573,2.435", "0,0,0,1"),
            "muzzle": ("tag_barrel_attach", "7.212,0,-1.397", "0,0,0,1"),
            "tag_brass": ("tag_sling", "7.866,-0.17,1.824", "0.000007,0.00001,-0.707106,0.707107"),
        },
        world_muzzle="12.08,0,4.39",
        world_eject="0.894,-0.743,5.176",
        world_left_hand="5.6,2.5,0.55",  # under the front half of the magazine, where the first-person hand holds it
        # No Underbarrel slot: the magazine is the handguard.
        slots=[
            ("Optic", (-2.2, 0, 6.311), (0.25, 0, 8.73), {"optic_rail": 1}),  # on the side-mount rail (-4.27 to 0.25), like the 74u's
            ("Muzzle", (10.808, 0, 4.39), (17.62, 0, 7.4147), {"muzzle_tip": 1}),  # tag_silencer, on the bore behind the nut
            ("Laser", (6.215, -0.848, 4.852), (8.6, -1.22, 7.4147), {}),  # tag_laser_attach (right-side flat 5.4 to 7.1)
        ],
        charm=(0.0, 1.75, 2.3),
        sticker=((1.132, 0.6883, 4.148), (0.0, 0.9999, -0.0135), (1.6, 0.8)),
        # The 762's measured correction moved by how far the Bizon's ADS pose puts its optic slot from the 762's, like
        # the 74u's. Tune in-game with dev_optic_correction.
        optic_aim_correction="2.554,0,-1.353",
        gameplay=gameplay_bizon,
        category="SMG",
        kill_reward=600,
        guid_salt="bizon/",
        parts=PARTS_BIZON,
        # port_kastov.py's world stock and grip points (tag_stock_attach, tag_pistolgrip_attach).
        part_slot_positions={"stock": (-5.716, 0, 3.649), "pistol_grip": (-3.0, 0, 3.0)},
    ),
    "ak105": Prefabs(
        title="AK-105",
        description="Russian 5.45x39mm carbine: the AK-74M cut down to a 314 mm barrel, with a side-folding stock.",
        price=2500,
        deploy_sound="weapons/ak105/sounds/ak105.raise.sound",
        icon_source="3499492742/materials/vgui/entities/mg_iw9_akilo105",
        # The flash hider, the stock hinge and the factory stock, grip and magazine; the optic mount hidden.
        default_mesh_groups=285343829,
        bones={
            "tag_sling": (None, "-6.971,-0.573,3.351", "0,0,0,1"),
            "tag_barrel_attach": ("tag_sling", "13.312,0.573,2.527", "0,0,0,1"),
            "muzzle": ("tag_barrel_attach", "12.477,0,-1.497", "0,0,0,1"),
            "tag_brass": ("tag_sling", "9.102,-0.17,1.884", "0.000005,0.000013,-0.707106,0.707107"),
        },
        world_muzzle="18.819,0,4.381",
        world_eject="2.131,-0.743,5.235",
        world_left_hand="6.9,2.7,1.95",  # the front of the handguard
        slots=[
            ("Optic", (-2.2, 0, 6.172), (0.25, 0, 8.73), {"optic_rail": 1}),  # on the rail mount (-4.35 to 3.08)
            ("Muzzle", (15.824, 0, 4.381), (17.62, 0, 7.4147), {"muzzle_tip": 1}),  # the flash hider's rear face
            ("Underbarrel", (8.24, 0, 3.111), (8.3, 0, 6.2), {}),  # the front of the handguard's bottom rail (5.26 to 10.34)
            ("Laser", (8.49, -1.059, 4.5), (8.6, -1.22, 7.4147), {}),  # tag_laser_attach, at the right-side rail (8.82 to 10.49)
        ],
        charm=(0.0, 1.75, 2.3),
        sticker=((2.5553, 0.6921, 4.1748), (0.001, 1.0, -0.0019), (1.4, 0.7)),
        # The 762's measured correction moved by how far the AK-105's ADS pose puts its optic slot from the 762's, like
        # the 74u's. Tune in-game with dev_optic_correction.
        optic_aim_correction="3.18,0,-1.269",
        gameplay=gameplay_ak105,
        guid_salt="ak105/",
        parts=PARTS_AK105,
        # port_kastov.py's world stock, grip and mag points (tag_stock_attach, tag_pistolgrip_attach, tag_mag_attach).
        part_slot_positions={"stock": (-5.716, 0, 3.649), "pistol_grip": (-3.0, 0, 3.0), "magazine": (2.514, 0, 3.257)},
        reload_sounds=ak105_reload_sounds,
    ),
    "vepr12": Prefabs(
        title="Vepr-12",
        description="Russian 12-gauge semi-automatic shotgun on the Kalashnikov action, fed from 8-round box magazines.",
        price=2200,
        deploy_sound="weapons/vepr12/sounds/vepr12.raise.sound",
        icon_source="3499492742/materials/vgui/entities/mg_iw9_vecho",
        # The muzzle brake and the factory stock, grip and magazine; the gas block's side rail hidden.
        default_mesh_groups=37814293,
        bones={
            "tag_sling": (None, "-6.971,-0.573,3.351", "0,0,0,1"),
            "tag_barrel_attach": ("tag_sling", "13.316,0.573,2.529", "0,0,0,1"),
            "muzzle": ("tag_barrel_attach", "10.877,0,-1.489", "0,0,0,1"),
            "tag_brass": ("tag_sling", "9.103,-0.17,1.884", "0.000007,0.000012,-0.707093,0.70712"),
        },
        world_muzzle="17.222,0,4.391",
        world_eject="2.132,-0.743,5.235",
        world_left_hand="6.9,2.8,1.84",  # the front of the handguard
        # No Muzzle slot: the M4's devices are 5.56 ones.
        slots=[
            ("Optic", (-2.416, 0, 6.143), (0.25, 0, 8.73), {}),  # tag_reflex, on the dust cover's rail (-4.5 to 2.5)
            ("Underbarrel", (8.0, 0, 3.03), (8.3, 0, 6.2), {}),  # the front of the handguard's bottom rail (6.17 to 10.11)
            ("Laser", (8.2, -1.09, 4.45), (8.6, -1.22, 7.4147), {}),  # the handguard's right-side rail (8.18 to 9.96)
        ],
        charm=(0.0, 1.75, 2.3),
        sticker=((-0.311, 0.673, 4.116), (0.0, 1.0, 0.0), (1.6, 0.8)),
        # The 762's measured correction moved by how far the Vepr-12's ADS pose puts its optic slot from the 762's, like
        # the 74u's. Tune in-game with dev_optic_correction.
        optic_aim_correction="3.396,0,-1.26",
        gameplay=gameplay_vepr12,
        category="Shotgun",
        kill_reward=900,
        guid_salt="vepr12/",
        parts=PARTS_VEPR12,
        # port_kastov.py's world stock, grip and mag points (tag_stock_attach, tag_pistolgrip_attach, tag_mag_attach).
        part_slot_positions={"stock": (-5.716, 0, 3.649), "pistol_grip": (-3.0, 0, 3.0), "magazine": (2.516, 0, 3.257)},
        reload_sounds=vepr12_reload_sounds,
    ),
    "m16": Prefabs(
        title="M16A4",
        description="US 5.56x45mm service rifle with a 20-inch barrel and a four-rail handguard. Semi-automatic and "
                    "three-round burst.",
        price=2600,
        deploy_sound="weapons/m16/sounds/m16.raise_rattle.sound",
        icon_source="2962304029/materials/vgui/entities/mg_iw9_mike16",
        # All factory sections and the 30-round magazine; the laser rail is hidden.
        default_mesh_groups=9087989,
        bones={
            "tag_sling": (None, "-5.334,-0.701,4.271", "0,0,0,1"),
            "tag_barrel_attach": ("tag_sling", "7.754,0.701,1.883", "0,0,0,1"),
            "muzzle": ("tag_barrel_attach", "21.35,0,-1.202", "0,0,0,1"),
            "tag_brass": ("tag_sling", "5.883,0.081,0.927", "0,0,-0.707107,0.707107"),
        },
        world_muzzle="23.77,0,4.951",
        world_eject="0.549,-0.62,5.197",
        # The middle of the handguard, where the first-person hand holds it (its side rails are 1.315 right of centre).
        world_left_hand="5.7,2.19,2.68",
        slots=[
            # tag_reflex, on the flat-top rail. An optic takes the carry handle off, as on the real rifle. The front sight
            # post is part of the barrel and stays up, co-witnessing with the dot (optic_sight_lines). A replacement
            # barrel's folding sight folds under an optic (the pack's optics blank its "sight" group).
            ("Optic", (-0.686, 0, 6.153), (0.25, 0, 8.73), {"carry_handle": 1}),
            ("Muzzle", (22.186, 0, 4.951), (17.62, 0, 7.4147), {"muzzle_tip": 1}),  # tag_tip, the flash hider's rear face
            # tag_grip_attach, on the bottom rail; a grip takes off its front half's cover (8.63 to 14.78).
            ("Underbarrel", (10.67, 0, 3.862), (8.3, 0, 6.2), {"grip_cover": 1}),
            # tag_laser_attach, on the rail section a laser brings to the handguard's right side (9.58 to 12.95).
            ("Laser", (10.154, -1.093, 4.961), (8.6, -1.22, 7.4147), {"laser_rail": 1}),
            ("Stock", (-5.806884, 0, 4.949219), (-4.05, 0, 7.4147), {"factory_stock": 1}),
            ("RearGrip", (-3, 0, 3), (-1.61, 0, 5.58), {"factory_grip": 1}),
            ("Barrel", (2.419922, 0, 6.153321), (4.32, 0, 8.6257),
             {"factory_barrel": 1, "factory_handguard": 1, "factory_front_sight": 1,
              "muzzle_tip": 1, "grip_cover": 1, "laser_rail": 2}),
        ],
        charm=(0.0, 1.75, 2.3),
        sticker=((1.193, 0.5403, 3.8305), (0.0, 1.0, 0.0), (1.4, 0.7)),
        # The 762's measured correction moved by how far the M16's ADS pose puts its optic slot from the 762's, like the
        # 74u's. The irons sit high on the carry handle, 1.5 over the rail, hence the z. Tune in-game with
        # dev_optic_correction.
        optic_aim_correction="1.613,0,0.079",
        # The front sight post stays up under an optic, so each 1x optic's dot co-witnesses with it, solved from renders
        # of the aimed view (hc1_m16_cowitness, Editor/Hc1M16OpticQa.cs). Absolute, the post tip on the dot, for the
        # sights that sit low on the rail, as a holographic sight does on a flat-top; lower 1/3, the tip 0.14" under
        # the dot, for those on raised mounts or bases.
        optic_sight_lines=[
            ("gunsmith/m4a1/mw2022/att_vm_holo_east01.gnsmth", "0,0.0055,0.1443", "1.3563,-0.0628,0"),
            ("gunsmith/m4a1/mw2022/att_vm_holo_west01.gnsmth", "0,0.0013,0.0979", "0.6657,-0.0042,0"),
            ("gunsmith/m4a1/mw2022/att_vm_reflex_02.gnsmth", "0,-0.0024,0.177", "0.8747,0.0057,0"),
            ("gunsmith/m4a1/mw2022/att_vm_reflex_east01.gnsmth", "0,0.0014,0.2002", "1.0811,-0.0043,0"),
            ("gunsmith/m4a1/mw2022/att_vm_reflex_west03.gnsmth", "0,-0.0001,0.0619", "0.5072,-0.0005,0"),
            ("gunsmith/m4a1/mw2022/att_vm_reflex_west04.gnsmth", "0,0,0.1544", "0.8808,-0.0006,0"),
            # Lower 1/3: the raised-base and enclosed holographics, and the sights on tall mounts.
            ("gunsmith/m4a1/mw2022/att_vm_2x_west02_holo.gnsmth", "0,0.0009,0.1641", "1.2102,-0.003,0"),
            ("gunsmith/m4a1/mw2022/att_vm_holo_west02.gnsmth", "0,-0.0012,0.185", "1.5213,0.0103,0"),
            ("gunsmith/m4a1/mw2022/att_vm_minireddot01_tall.gnsmth", "0,-0.0036,0.2931", "2.1787,0.0167,0"),
            ("gunsmith/m4a1/mw2022/att_vm_minireddot02_tall.gnsmth", "0,0.0005,0.2826", "2.1537,-0.0019,0"),
            ("gunsmith/m4a1/mw2022/att_vm_minireddot03_tall.gnsmth", "0,-0.001,0.2993", "2.1317,0.0074,0"),
            ("gunsmith/m4a1/mw2022/att_vm_reflex_east02_tall.gnsmth", "0,0.0001,0.1762", "1.0204,-0.0011,0"),
            ("gunsmith/m4a1/mw2022/att_vm_reflex_west02_tall.gnsmth", "0,-0.0018,0.1484", "1.3325,0.0041,0"),
        ],
        gameplay=gameplay_m16,
        guid_salt="m16/",
        part_slot_positions={"magazine": (1.958985, 0, 2.223633)},
    ),
    "p90": Prefabs(
        title="FN P90",
        description="Belgian 5.7x28mm personal defence weapon: a bullpup fed from a 50-round magazine lying along its "
                    "top.",
        price=1700,
        deploy_sound="weapons/p90/sounds/p90.raise.sound",
        icon_source="2802430252/materials/vgui/entities/mg_papa90",
        # The flash hider and the iron sights.
        default_mesh_groups=21,
        bones={
            "tag_sling": (None, "-11.59,0,2.07", "0,0,0,1"),
            "tag_barrel_attach": ("tag_sling", "13.646,0,1.34", "0,0,0,1"),
            "muzzle": ("tag_barrel_attach", "2,0,0.155", "0,0,0,1"),
            # The ejection chute behind the grip: the real gun throws its cases down.
            "tag_brass": ("tag_sling", "2.653,0.059,-0.82", "0.500016,0.499984,-0.499982,0.500018"),
        },
        world_muzzle="4.056,0,3.565",
        world_eject="-8.937,0.059,1.25",
        # Under the frame's front, where the first-person hand holds it (its sides are 0.665 from centre, its bottom
        # at -0.36).
        world_left_hand="-2.5,2.84,-1.55",
        # No Underbarrel slot: the left hand holds the frame's front, which has no rail.
        slots=[
            # tag_reflex, at the back of the top rail (-4 to 1.5). An optic takes the iron sights off.
            ("Optic", (-3.422, 0, 6.558), (0.25, 0, 8.73), {"iron_sights": 1}),
            ("Muzzle", (2.597, 0, 3.565), (17.62, 0, 7.4147), {"muzzle_tip": 1}),  # tag_tip, the flash hider's rear face
            ("Laser", (0.592, -0.914, 5.894), (8.6, -1.22, 7.4147), {}),  # tag_laser_attach, on the right-side rail (0.5 to 1.6)
        ],
        # The stock's left side behind the thumbhole, clear of both hands (the charm's anchor sits 0.57 ahead of this
        # and 1.84 over it, at the stock's surface).
        charm=(-10.07, 1.86, 2.16),
        # High on the housing's left side, where it shows in first person (the butt's flat is out of view).
        sticker=((-11.103, 0.988, 4.41), (0.0, 1.0, 0.0), (1.0, 0.5)),
        # The 762's measured correction moved by how far the P90's ADS pose puts its optic slot from the 762's, like the
        # 74u's. The irons stand high on the top rail, hence the z. Tune in-game with dev_optic_correction.
        optic_aim_correction="2.596,0,-0.445",
        gameplay=gameplay_p90,
        category="SMG",
        kill_reward=600,
        guid_salt="p90/",
    ),
    "mp7": Prefabs(
        title="MP7A1",
        description="German 4.6x30mm personal defence weapon: compact and fast-firing, fed from a 40-round magazine in "
                    "its pistol grip.",
        price=1600,
        deploy_sound="weapons/mp7/sounds/mp7.raise.sound",
        icon_source="2802430252/materials/vgui/entities/mg_mpapa7",
        # The flash hider and the iron sights; the laser's mount hidden.
        default_mesh_groups=85,
        bones={
            "tag_sling": (None, "-9.42,0,4.64", "0,0,0,1"),
            "tag_barrel_attach": ("tag_sling", "10.411,0,-1.266", "0,0,0,1"),
            "muzzle": ("tag_barrel_attach", "3.882,0,0.721", "0,0,0,1"),
            "tag_brass": ("tag_sling", "4.633,-0.701,-0.404", "0,0,-0.707107,0.707107"),
        },
        world_muzzle="4.873,0,4.095",
        world_eject="-4.787,-0.701,4.236",
        # Under the receiver's front, where the first-person hand holds it (its sides are 1.21 from centre, its bottom
        # at 3.664, and the fingers reach its front end at 3).
        world_left_hand="-0.9,2.29,2.47",
        # No Underbarrel slot: the left hand holds the receiver's front, where a grip would go.
        slots=[
            # tag_reflex, at the back of the top rail (-9 to 3). An optic takes the flip-up sights off.
            ("Optic", (-6.726, 0, 6.024), (0.25, 0, 8.73), {"iron_sights": 1}),
            # The flash hider's rear face, at the barrel's end (tag_tip is 0.22 further back, inside the barrel).
            ("Muzzle", (3.953, 0, 4.1), (17.62, 0, 7.4147), {"muzzle_tip": 1}),
            # The back of the ring mount a laser brings to the top rail's right side (tag_laser_attach is its front):
            # there the lasers stay above the left hand's fingers, which wrap the receiver's own side rail.
            ("Laser", (-0.07, -1.496, 5.407), (8.6, -1.22, 7.4147), {"laser_rail": 1}),
        ],
        # The back of the receiver's left side, clear of both hands (the charm's anchor sits 0.57 ahead of this and 1.84
        # over it, under the side's ledge).
        charm=(-8.87, 1.9, 2.36),
        # Behind the left hand, clear of it and the charm, where it shows in first person.
        sticker=((-6.862, 0.7293, 3.402), (-0.0004, 1.0, 0.0001), (1.6, 0.8)),
        # The 762's measured correction moved by how far the MP7's ADS pose puts its optic slot from the 762's, like the
        # 74u's. The irons stand on the top rail, hence the z. Tune in-game with dev_optic_correction.
        optic_aim_correction="1.375,0,-0.462",
        gameplay=gameplay_mp7,
        category="SMG",
        kill_reward=600,
        guid_salt="mp7/",
    ),
    "uzi": Prefabs(
        title="Uzi",
        description="Israeli 9x19mm submachine gun: heavy for its size and slow-firing, with its 32-round magazine in the "
                    "pistol grip.",
        price=1400,
        deploy_sound="weapons/uzi/sounds/uzi.raise_up.sound",
        icon_source="2802430252/materials/vgui/entities/mg_uzulu",
        # The factory stock and magazine; the optic and laser mounts hidden (read from the compiled models).
        default_mesh_groups=1173,
        bones={
            "tag_sling": (None, "-1.69,0.937,4.51", "0,0,0,1"),
            "tag_barrel_attach": ("tag_sling", "4.763,-0.937,-0.39", "0,0,0,1"),
            "muzzle": ("tag_barrel_attach", "4.121,0,0", "0,0,0,1"),
            "tag_brass": ("tag_sling", "-2.056,-1.486,0.161", "0,0,-0.707107,0.707107"),
        },
        world_muzzle="7.194,0,4.12",
        world_eject="-3.746,-0.549,4.671",
        # The lower receiver's front, where the first-person hand holds it (its sides are 0.91 from centre, its bottom
        # at 2.99, and the fingers reach its front end at 3.77).
        world_left_hand="-0.13,2.59,1.8",
        # No Underbarrel slot: the left hand holds the lower receiver's front, and the pack's grips move it.
        slots=[
            # tag_reflex, at the back of the claw mount an optic brings onto the top cover (-7.77 to -3.52).
            ("Optic", (-7.414, 0, 6.292), (0.25, 0, 8.73), {"optic_rail": 1}),
            ("Muzzle", (7.405, 0, 4.12), (17.62, 0, 7.4147), {}),  # the barrel's front face
            # The back of the ring mount a laser brings to the receiver's front, on its right side (tag_laser_attach is
            # its front).
            ("Laser", (1.45, -1.498, 4.893), (8.6, -1.22, 7.4147), {"laser_rail": 1}),
        ],
        # The back of the receiver's left side, clear of both hands and of the folded stock's struts (the charm's
        # anchor sits 0.57 ahead of this, 0.71 in and 1.84 over it, on the receiver's side).
        charm=(-8.57, 1.51, 2.76),
        sticker=((-5.652, 0.696, 4.291), (0.0, 1.0, 0.0), (1.2, 0.6)),
        # The 762's measured correction moved by how far the Uzi's ADS pose puts its optic slot from the 762's, like the
        # 74u's. At the ADS pose the claw mount holds the optic's base 0.32 over the iron sight line, where the 762's rail
        # is 0.22 under its own, hence the z. Tune in-game with dev_optic_correction.
        optic_aim_correction="0.241,0,-1.747",
        gameplay=gameplay_uzi,
        category="SMG",
        kill_reward=600,
        guid_salt="uzi/",
        parts=PARTS_UZI,
        # port_kastov.py's world stock and mag points (tag_stock_attach, tag_mag_attach).
        part_slot_positions={"stock": (-10.503, 0, 4.282), "magazine": (-3.237, 0, -0.7)},
        reload_sounds=uzi_reload_sounds,
    ),
    "aug": Prefabs(
        title="Steyr AUG A3",
        description="Austrian 5.56x45mm bullpup rifle: a 16-inch barrel with a folding foregrip, and the magazine "
                    "behind the pistol grip.",
        price=2800,
        deploy_sound="weapons/aug/sounds/aug.raise.sound",
        icon_source="2802430252/materials/vgui/entities/mg_augolf",
        # The flash hider and the iron sights; the laser's mount hidden (read from the compiled models).
        default_mesh_groups=21665,
        bones={
            "tag_sling": (None, "-17.906,1.067,2.523", "0,0,0,1"),
            "tag_barrel_attach": ("tag_sling", "20.545,-1.067,1.87", "0,0,0,1"),
            "muzzle": ("tag_barrel_attach", "7.269,0,0.005", "0,0,0,1"),
            "tag_brass": ("tag_sling", "7.178,-1.654,2.077", "0,0,-0.707107,0.707107"),
        },
        world_muzzle="9.908,0,4.398",
        world_eject="-10.728,-0.586,4.6",
        # On the foregrip's left side, the palm where the first-person hand's is (the player's hand fitted to its wrist,
        # knuckles and thumb base) and 1 further back, so the rifle hold's fingers wrap the grip's front instead of the
        # air in front of it. The thumb goes round the grip's back near the top.
        world_left_hand="0.25,1.56,0.01",
        world_left_hand_rotation="0.0176,-0.1819,-0.0435,0.9822",
        # No Underbarrel slot: the left hand holds the AUG's own folding foregrip.
        slots=[
            # tag_reflex, on the top rail. An optic takes the flip-up sights off.
            ("Optic", (-5.073, 0, 6.087), (0.25, 0, 8.73), {"iron_sights": 1}),
            ("Muzzle", (8.193, 0, 4.398), (17.62, 0, 7.4147), {"muzzle_tip": 2}),  # off is after the long barrel's tip
            # The back of the mount a laser brings to the barrel's right side, ahead of the foregrip (tag_laser_attach
            # is its front).
            ("Laser", (3.65, -1.218, 4.399), (8.6, -1.22, 7.4147), {"laser_rail": 1}),
        ],
        # The stock's left side above the magazine, clear of both hands (the charm's anchor sits 0.57 ahead of this,
        # 0.71 in and 1.84 over it, on the stock's side).
        charm=(-8.57, 1.75, 2.36),
        sticker=((-10.4073, 0.7448, 3.0155), (0.0266, 0.9992, -0.0286), (1.6, 0.8)),
        # The 762's measured correction moved by how far the AUG's ADS pose puts its optic slot from the 762's, like the
        # 74u's. Tune in-game with dev_optic_correction.
        optic_aim_correction="-0.206,0,-0.69",
        gameplay=gameplay_aug,
        parts={
            "lightweight": Part("Lightweight Stock", "Slim shoulder pad with reduced support.", 1.06, 1.06),
            "tactical": Part("Padded Tactical Stock", "Wider padded shoulder support.", .92, .92),
            "long": Part("Heavy Long Barrel", "Extended heavy barrel for longer engagements.",
                         muzzle_shift=(6.102728, 0, 0)),
            "drum": Part("60 Round Drum", "5.56mm drum magazine with its own reload animation.",
                         magazine_capacity=60, reload_variant="_drummag", reload_times=(2.3, 3.4)),
        },
        part_slot_positions={"stock": (-17, 0, 2.5), "barrel": (6, 0, 4.4), "magazine": (-10, 0, -.5)},
        part_slot_bodygroups={"barrel": {"muzzle_tip": 1}},
        reload_sounds=lambda: load(ASSETS / "Weapons" / "AUG" / "aug_assets.json")["reloads"],
        guid_salt="aug/",
        review_note="Not checked in a match yet: the iron sights and the optics' aim (derived: tune with "
                    "dev_optic_correction), recoil, reload timing and sounds, the look sway, and the left hand on the "
                    "foregrip in first and third person.",
    ),
    "famas": Prefabs(
        title="FAMAS F1",
        description="French 5.56x45mm bullpup rifle with a 25-round magazine, a fixed carry handle and selectable "
                    "automatic, three-round burst and semi-automatic fire.",
        price=2600, deploy_sound="weapons/famas/sounds/famas.raise.sound",
        icon_source="2528829149/materials/vgui/entities/mg_falpha", default_mesh_groups=153231489,
        bones={
            "tag_sling": (None, "-5.747,0,4.872", "0,0,0,1"),
            "tag_barrel_attach": ("tag_sling", "10.799,0,-1.419", "0,0,0,1"),
            "muzzle": ("tag_barrel_attach", "11.28,0,0", "0,0,0,1"),
            "tag_brass": ("tag_sling", "-0.628,-0.596,-0.933", "0,0,-0.707093,0.707121"),
        },
        world_muzzle="16.332,0,3.453", world_eject="-6.375,-0.596,3.939",
        world_left_hand="5.925,1.997,1.052",
        slots=[
            ("Optic", (-.112, 0, 7.677), (.25, 0, 8.73), {"iron_sights": 2, "sight_folded": 1}),
            ("Muzzle", (14.822, 0, 3.453), (17.62, 0, 7.4147), {"muzzle_tip": 4}),
            ("Laser", (10.9, -1.34, 3.464), (8.6, -1.22, 7.4147), {"laser_rail": 1}),
        ],
        charm=(-11.5, 1.15, 2.7), optic_aim_correction="3.305,0,-0.418",
        sticker=((-6.274, 0.9562, 3.427), (0.0, 1.0, -0.0067), (1.6, 0.8)),
        gameplay=gameplay_famas, guid_salt="famas/",
        parts={
            "barshort": Part("Compact Short Barrel", "Shortened barrel assembly.",
                             muzzle_shift=(-1.290, 0, .001), bodygroups={"muzzle_tip": 1}),
            "barlong2": Part("Lightweight Long Barrel", "Extended barrel with a lightweight sleeve.",
                             muzzle_shift=(3.669, 0, .001), bodygroups={"muzzle_tip": 2}),
            "barrellong_alt": Part("Heavy Long Barrel", "Extended heavy-profile barrel.", .96, .96,
                                    muzzle_shift=(3.669, 0, .001), bodygroups={"muzzle_tip": 3}),
            "stock_light": Part("Cutaway Stock", "Lightened buttstock with an open shoulder section.", 1.04, 1.04),
            "stock_stable": Part("Padded Stock", "Padded cheek rest and shoulder support.", .95, .95),
            "stock_tactical_v1": Part("Weighted Stock", "Weighted rear support with an enlarged cheek rest.", .90, .90),
            "xmags": Part("50 Round Mag", "Extended 50-round magazine.", magazine_capacity=50,
                          reload_variant="_xmag", reload_times=(2.5, 2.55), offered=False),
            "xmags2": Part("60 Round Mag", "High-capacity 60-round magazine.", magazine_capacity=60,
                           reload_variant="_xmag2", reload_times=(2.6, 2.9), offered=False),
            "classic": Part("Classic Carry Handle", "Alternative carry-handle upper with the original sight height."),
            "low": Part("Low Profile Rail", "Lower accessory rail with its own folding sights and charging assembly.",
                        bodygroups={"iron_sights": 1}, optic_bodygroups={"sight_folded": 2},
                        optic_mount_shift=(-.605, 0, -1.338), rail_optic_aim=(.605, 0, 1.338),
                        rail_iron_aim=(0, 0, 1.669)),
        },
        part_slot_positions={"barrel": (5.052, 0, 3.453), "stock": (-12, 0, 4),
                             "magazine": (-8, 0, 0), "rail": (0, 0, 7)},
        reload_sounds=lambda: load(ASSETS / "Weapons/FAMAS/famas_assets.json")["reloads"],
    ),
    "fal": Prefabs(
        title="FN FAL",
        description="Belgian 7.62x51mm battle rifle: heavy and hard-kicking, with a 21-inch barrel and a 20-round "
                    "magazine.",
        price=2800,
        deploy_sound="weapons/fal/sounds/fal.raise.sound",
        icon_source="2528829149/materials/vgui/entities/mg_falima",
        # The flash hider, the raised rear sight and the factory stock, barrel and magazine; the optic and laser mounts
        # and the folded sight hidden (read from the compiled models).
        default_mesh_groups=174761,
        bones={
            "tag_sling": (None, "-5.747,0,4.872", "0,0,0,1"),
            "tag_barrel_attach": ("tag_sling", "21.708,0,-0.309", "0,0,0,1"),
            "muzzle": ("tag_barrel_attach", "9.419,0,-0.007", "0,0,0,1"),
            "tag_brass": ("tag_sling", "7.448,-0.459,0.334", "0,0,-0.707092,0.707121"),
        },
        world_muzzle="25.38,0,4.556",
        world_eject="1.701,-0.459,5.206",
        # By the rule, where the first-person hand holds the handguard (its wrist at x 6.39): the handguard's right side
        # is 1.128 from centre and its short bottom rail's underside at 3.345.
        world_left_hand="6.4,2.37,2.16",
        # No Underbarrel slot: the left hand holds the handguard, whose short bottom rail the fingers wrap.
        slots=[
            # tag_reflex, on the rail an optic brings onto the top cover. An optic takes the raised rear sight off and
            # shows it folded, as on the real gun's scope mounts.
            ("Optic", (-3.221, 0, 6.11), (0.25, 0, 8.73), {"optic_rail": 1, "iron_sights": 1, "sight_folded": 1}),
            # tag_tip, the flash hider's rear face. Off is after the 18-inch barrel's short flash hider.
            ("Muzzle", (20.497, 0, 4.556), (17.62, 0, 7.4147), {"muzzle_tip": 2}),
            # The back of the mount a laser brings to the handguard's right side (tag_laser_attach is its front).
            ("Laser", (11.66, -1.453, 5.482), (8.6, -1.22, 7.4147), {"laser_rail": 1}),
        ],
        # The stock's left side, near its front (the charm's anchor sits 0.57 ahead of this, 0.71 in and 1.84 over
        # it, at the stock's surface). Not on the receiver like the Kastovs': the empty reload's left hand racks the
        # charging handle along the receiver's whole left side, and its thumb went through a charm there, while above
        # the trigger guard the disk rested on the right thumb. Here every hand joint stays over 2 from its bounds through
        # both reloads, the sprint and aiming (the Kastov 762's left thumb comes within 0.49 of its charm's).
        charm=(-10.87, 1.46, 3.06),
        sticker=((-3.741, 0.746, 4.613), (0.0, 1.0, 0.0), (1.4, 0.7)),
        # The 762's measured correction moved by how far the FAL's ADS pose puts its optic slot from the 762's, like the
        # 74u's. Tune in-game with dev_optic_correction.
        optic_aim_correction="2.402,0,-1.066",
        gameplay=gameplay_fal,
        guid_salt="fal/",
        # The pack's real FAL parts (kastov_weapons.FAL). The Para's stock is a steel tube with a thin buttplate,
        # lighter than the 50.00's wooden or polymer stock and less to brace against, like the 74u's cut-down skeleton
        # stock. The 18-inch barrel's tag_silencer, where a muzzle device mounts, is 2.099 behind the factory barrel's,
        # and its short flash hider ends 5.926 behind the factory one's front; M80 leaves it at ~817 m/s instead of
        # 840 (~25 fps an inch less), 0.946 of the muzzle energy. The 30-round magazine's reloads have the gun level again
        # at 2.67 s and 3.57 s empty (its clips, measured like the factory reload's 2.67 and 3.4).
        parts={
            "para": Part("Para Folding Stock", "The FAL Para's tubular folding stock. Lighter, with a thin buttplate.",
                         1.05, 1.05),
            "short": Part("18-inch Barrel", "The 18-inch barrel of the folding-stock 50.62, with a short flash hider.",
                          muzzle_shift=(-2.099, 0, 0.002), tip_shift=(-3.827, 0, -0.002), falloff=0.95,
                          bodygroups={"muzzle_tip": 1}),
            "xmag": Part("30 Round Mag", "The 30-round magazine of the FAL's heavy-barrel squad rifle. Longer and "
                         "heavier.", magazine_capacity=30, reload_variant="_xmag", reload_times=(2.67, 3.57)),
        },
        # tag_stock_attach, tag_barrel_attach and tag_mag_attach.
        part_slot_positions={"stock": (-8.847, 0, 4.081), "barrel": (15.961, 0, 4.563), "magazine": (3.118, 0, 3.85)},
        reload_sounds=lambda: load(ASSETS / "Weapons" / "FAL" / "fal_assets.json")["reloads"],
        review_note="Not checked in a match yet: the iron sights and the optics' aim (derived: tune with "
                    "dev_optic_correction), recoil, reload timing and sounds (the 30-round magazine's too), the look sway "
                    "and sprint, the left hand in first and third person, and the 18-inch barrel's muzzle flash and "
                    "devices.",
    ),
    "m18": Prefabs(
        title="SIG Sauer M18",
        description="American 9x19mm service pistol: the US Army's compact P320, with a 3.9-inch barrel and a "
                    "17-round magazine.",
        price=300,
        deploy_sound="weapons/m18/sounds/m18.raise_up.sound",
        icon_source="2459723892/materials/vgui/entities/mg_p320",
        # The coyote slide and the 17-round magazine, by the bit rule (read it again from the compiled model).
        default_mesh_groups=145,
        bones={
            "tag_sling": (None, "-1.96,0,3.7", "0,0,0,1"),
            "tag_barrel_attach": ("tag_sling", "5.932,0,1.186", "0,0,0,1"),
            "muzzle": ("tag_barrel_attach", "-0.49,0,-0.126", "0,0,0,1"),
            # The slide, which the sticker rides.
            "j_slide": ("tag_barrel_attach", "-3.395,0,-0.111", "0,0,0,1"),
            "tag_brass": ("tag_sling", "0.951,-0.451,1.343", "-0.139865,-0.139865,-0.693134,0.693138"),
        },
        world_muzzle="3.482,0,4.76",
        world_eject="-1.009,-0.451,5.043",
        # A pistol: the third-person pistol hold has no left-hand IK, like the USP's and 1911's.
        world_left_hand=None,
        # No M4-part slots: the M18's barrel isn't threaded, it has no optic cut, and the M4's lasers are rifle lasers.
        slots=[],
        charm=None,
        # No optic slot.
        optic_aim_correction="0,0,0",
        gameplay=gameplay_m18,
        category="Pistol",
        # Held at the pistols' height in the gunsmith, like the USP.
        gunsmith_offset="0,0,0",
        guid_salt="m18/",
        parts=PARTS_M18,
        # The slide's middle, and tag_mag_attach.
        part_slot_positions={"barrel": (-0.09, 0, 4.8), "magazine": (-1.966, 0, -0.036)},
        reload_sounds=m18_reload_sounds,
        # The slide's left side between its serrations: flat at y 0.53 from x -1.32 to 1.56 and z 4.42 to 4.80.
        sticker=((0.122, 0.53, 4.606), (0.0, 1.0, 0.0), (1.2, 0.34)),
        sticker_bone="j_slide",
        # The USP's: a pistol in the secondary slot, with its armour penetration.
        equip_fields={"Slot": "Secondary", "ArmorReduction": 0.775, "HelmetReduction": 0.4},
        # The USP's icon's size, a little less for the M18's 7.2 in.
        icon_width=0.33,
        review_note="Not checked in a match yet: the iron sights, recoil, the slide locking back on the last round, "
                    "reload timing and sounds (the 21-round magazine's too), the look sway, the M4's sprint on a "
                    "pistol, and the third-person hold.",
    ),
}

MOUNT_BONE = "tag_sling"

# How far the world model's sticker slot stands off its patch: with GunsmithSticker's own lift the sticker clears
# the gun by 0.03, so it doesn't flicker into it seen from a distance.
WORLD_STICKER_LIFT = 0.018

# How the third-person left hand turns on the handguard (the world model's LeftHandIK rotation, the same on every gun):
# the players' rifle clip's cupped hand, turned 20 degrees so the fingers wrap the handguard's right side.
WORLD_LEFT_HAND_ROTATION = "-0.6308,0.3714,-0.448,0.5133"

# The M4's MW22 parts that fit the guns' slots, plus loadout-only parts. The M4's barrels, stocks, grips and
# magazines are pieces of the M4 itself; its launcher needs the M4's barrel.
SLOT_CATEGORIES = {"Optic", "Muzzle", "Underbarrel", "Laser"}
FITTING_PARTS = [path for path in sorted((ASSETS / "gunsmith" / "m4a1" / "mw2022").glob("*.gnsmth"))
                 if json.loads(path.read_text(encoding="utf-8"))["Category"] in SLOT_CATEGORIES
                 and path.stem != "att_vm_p01_ar_mike4_ubgl"]
FITTING_PARTS.append(ASSETS / "gunsmith" / "ammunition" / "tracer_rounds.gnsmth")
ELIGIBLE = re.compile(r'("EligibleEquipment":\s*\[)(.*?)(\n\s*\])', re.DOTALL)

def remap_guids(document: dict, salt: str) -> dict:
    text = json.dumps(document)
    mapping = {old: str(uuid.uuid5(NAMESPACE, f"{salt}/{old}")) for old in set(GUID.findall(text))}
    return json.loads(GUID.sub(lambda match: mapping[match.group(0)], text))


def new_guid(key: str) -> str:
    return str(uuid.uuid5(NAMESPACE, key))


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, document: dict) -> None:
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8", newline="\n")


def component(game_object: dict, suffix: str) -> dict:
    return next(c for c in game_object.get("Components", []) if c["__type"].endswith(suffix))


def find(game_object: dict, name: str) -> dict:
    if game_object.get("Name") == name:
        return game_object
    for child in game_object.get("Children", []):
        found = find(child, name)
        if found is not None:
            return found
    raise KeyError(name)


def reference(game_object: dict) -> dict:
    return {"_type": "gameobject", "go": game_object["__guid"]}


def component_reference(game_object: dict, comp: dict, kind: str) -> dict:
    return {"_type": "component", "component_id": comp["__guid"], "go": game_object["__guid"],
            "component_type": kind}


def vector(values) -> str:
    return ",".join(f"{v:g}" for v in values)


def icon_path(weapon: Weapon) -> str:
    return f"ui/weapons/guns/{weapon.name}_01.png"


def offered(prefabs: Prefabs, choice: str) -> bool:
    part = prefabs.parts.get(choice)
    return part is None or part.offered


def all_slots(weapon: Weapon, prefabs: Prefabs) -> list[tuple[str, tuple, tuple, dict[str, int]]]:
    """The M4-part slots plus one per part_choices group, whose parts switch its bodygroup instead of mounting."""
    return prefabs.slots + [(PART_SLOTS[group][0], prefabs.part_slot_positions[group],
                             prefabs.part_slot_positions[group], prefabs.part_slot_bodygroups.get(group, {}))
                            for group, choices in weapon.part_choices.items()
                            if not choices[1:] or any(offered(prefabs, choice) for choice, _ in choices[1:])]


def attachment_points(weapon: Weapon, prefabs: Prefabs, prefix: str) -> list[dict]:
    points = []
    for category, target, m4, bodygroups in all_slots(weapon, prefabs):
        key = f"{prefabs.guid_salt}{prefix}/slot/{category}"
        points.append({
            "__guid": new_guid(key), "Flags": 0, "Name": f"{category} Attachment Point",
            "Position": vector(target), "Enabled": True,
            "Components": [{
                "__type": "Facepunch.Gunsmith.GunsmithAttachmentPoint",
                "__guid": new_guid(f"{key}/point"),
                "Category": category,
                "MountBone": MOUNT_BONE,
                "MountOffset": vector(np.subtract(target, m4).round(4)),
                "FittedBodygroups": bodygroups,
            }],
        })
    return points


def charm_point(prefabs: Prefabs, prefix: str, position) -> dict:
    key = f"{prefabs.guid_salt}{prefix}/slot/Charm"
    return {
        "__guid": new_guid(key), "Flags": 0, "Name": "Charm Attachment Point",
        "Position": vector(position), "Enabled": True,
        "Components": [{"__type": "Facepunch.Gunsmith.GunsmithAttachmentPoint",
                        "__guid": new_guid(f"{key}/point"), "Category": "Charm"}],
    }


def sticker_point(prefabs: Prefabs, prefix: str, position, lift: float = 0.0) -> dict:
    """The sticker's slot at position, moved lift out along the patch's normal. Its +X points out of the patch, +Z
    towards up and +Y = Z x X, which on the left side runs towards the butt, so the artwork reads from the muzzle end."""
    _, normal, room = prefabs.sticker
    out = np.asarray(normal, float) / np.linalg.norm(normal)
    up = np.array([0.0, 0.0, 1.0]) - out * out[2]
    up /= np.linalg.norm(up)
    rotation = rotation_to_quaternion(np.stack([out, np.cross(up, out), up], 1))
    key = f"{prefabs.guid_salt}{prefix}/slot/Sticker"
    return {
        "__guid": new_guid(key), "Flags": 0, "Name": "Sticker Attachment Point",
        "Position": vector(np.round(np.add(position, out * lift), 4)),
        "Rotation": ",".join(f"{v:.6f}" for v in rotation), "Enabled": True,
        "Components": [{"__type": "Facepunch.Gunsmith.GunsmithAttachmentPoint", "__guid": new_guid(f"{key}/point"),
                        "Category": "Sticker", "StickerSize": vector(room)}],
    }


def set_aim(functions: dict, prefabs: Prefabs) -> None:
    # ADS comes from the animgraph (ads_delta), like the M4: no manual offset.
    offset = component(functions, "ManualOffset")
    offset["AimOffset"] = "0,0,0"
    offset["AimAngleOffset"] = "0,0,0"
    offset["OpticAimCorrection"] = prefabs.optic_aim_correction
    if prefabs.optic_sight_lines:
        offset["OpticSightLines"] = [{"Optic": optic, "Position": position, "Angles": angles}
                                     for optic, position, angles in prefabs.optic_sight_lines]
    else:
        offset.pop("OpticSightLines", None)


def weapon_prefab(weapon: Weapon, prefabs: Prefabs) -> dict:
    """A generated gameplay prefab: the M4's, with the gun's Gameplay."""
    document = remap_guids(load(M4 / "weapon_m4a1.prefab"), f"{prefabs.guid_salt}weapon")
    root = document["RootObject"]
    root["Name"] = f"weapon_{weapon.name}"
    equipment = component(root, "Equipment")
    equipment["Resource"] = f"{weapon.asset}/{weapon.name}.equip"
    equipment["MountedPrefab"] = {"_type": "gameobject", "prefab": f"{weapon.asset}/mount_{weapon.name}.prefab"}
    equipment["DeploySound"] = prefabs.deploy_sound

    functions = find(root, "Functions")

    def target(game_object: dict, suffix: str) -> dict:
        return component(game_object if suffix == "Equipment" else find(game_object, "Functions"), suffix)

    gameplay = prefabs.gameplay()
    if gameplay.borrow is not None:
        source_path, borrowed = gameplay.borrow
        source = load(source_path)["RootObject"]
        for suffix, names in borrowed.items():
            values = target(source, suffix)
            target(root, suffix).update({name: deepcopy(values[name]) for name in names})
    functions["Components"] = [c for c in functions["Components"]
                               if not any(c["__type"].endswith(f".{suffix}") for suffix in gameplay.remove)]
    for suffix, values in gameplay.fields.items():
        if suffix != "Equipment" and not any(c["__type"].endswith(suffix) for c in functions["Components"]):
            # A component the M4 doesn't have (the RPK's BarrelHeat).
            functions["Components"].append({"__type": f"Facepunch.{suffix}",
                                            "__guid": new_guid(f"{prefabs.guid_salt}weapon/{suffix}"),
                                            "__enabled": True})
        target(root, suffix).update(deepcopy(values))

    set_aim(functions, prefabs)
    return document


def patched_weapon_prefab(weapon: Weapon, prefabs: Prefabs) -> dict:
    """An existing gameplay prefab with the viewmodel's ADS and deploy sound."""
    document = load(weapon.folder / f"weapon_{weapon.name}.prefab")
    root = document["RootObject"]
    component(root, "Equipment")["DeploySound"] = prefabs.deploy_sound
    set_aim(find(root, "Functions"), prefabs)
    return document


def viewmodel_prefab(weapon: Weapon, prefabs: Prefabs) -> dict:
    salt = prefabs.guid_salt
    template = load(M4 / "vm_m4a1.prefab")
    template_root = template["RootObject"]
    root = {key: deepcopy(value) for key, value in template_root.items() if key not in ("Children", "Components")}
    root["__guid"] = new_guid(f"{salt}vm/root")
    root["Name"] = f"vm_{weapon.name}"

    view_model = deepcopy(component(template_root, "ViewModel"))
    renderer = deepcopy(component(template_root, "SkinnedModelRenderer"))
    gunsmith = deepcopy(component(template_root, "GunsmithWeapon"))
    view_model["__guid"] = new_guid(f"{salt}vm/viewmodel")
    renderer["__guid"] = new_guid(f"{salt}vm/renderer")
    gunsmith["__guid"] = new_guid(f"{salt}vm/gunsmith")
    renderer["Model"] = f"{weapon.asset}/v_{weapon.model}.vmdl"
    renderer["BodyGroups"] = prefabs.default_mesh_groups
    renderer["CreateBoneObjects"] = True

    arms_template = find(template_root, "Object")
    arms = deepcopy(arms_template)
    arms["__guid"] = new_guid(f"{salt}vm/arms")
    arms_renderer = component(arms, "SkinnedModelRenderer")
    arms_renderer["__guid"] = new_guid(f"{salt}vm/arms/renderer")
    arms_renderer["BoneMergeTarget"] = component_reference(root, renderer, "SkinnedModelRenderer")

    bones: dict[str, dict] = {}
    children = [arms]
    for name, (parent, position, rotation) in prefabs.bones.items():
        bone = {"__guid": new_guid(f"{salt}vm/bone/{name}"), "Flags": 4, "Name": name, "Position": position,
                "Rotation": rotation, "Enabled": True}
        bones[name] = bone
        if parent is None:
            children.append(bone)
        else:
            bones[parent].setdefault("Children", []).append(bone)

    view_model["Arms"] = component_reference(arms, arms_renderer, "SkinnedModelRenderer")
    view_model["ModelRenderer"] = component_reference(root, renderer, "SkinnedModelRenderer")
    view_model["Muzzle"] = reference(bones["muzzle"])
    view_model["EjectionPort"] = reference(bones["tag_brass"])
    view_model["AimTime"] = weapon.ads_time
    gunsmith["Renderer"] = component_reference(root, renderer, "SkinnedModelRenderer")
    gunsmith["Resource"] = f"{weapon.asset}/{weapon.name}.equip"

    root["Components"] = [view_model, renderer, gunsmith]
    sling = np.array([float(v) for v in prefabs.bones[MOUNT_BONE][1].split(",")])
    if prefabs.charm is not None:
        bones[MOUNT_BONE].setdefault("Children", []).append(
            charm_point(prefabs, "vm", (np.subtract(prefabs.charm, sling)).round(4)))
    if prefabs.sticker is not None:
        bones[prefabs.sticker_bone].setdefault("Children", []).append(sticker_point(
            prefabs, "vm", np.subtract(prefabs.sticker[0], bind_position(prefabs, prefabs.sticker_bone))))
    root["Children"] = children + attachment_points(weapon, prefabs, "vm")
    document = {key: deepcopy(value) for key, value in template.items() if key != "RootObject"}
    document["RootObject"] = root
    document["__references"] = []
    return document


def bind_position(prefabs: Prefabs, bone: str) -> np.ndarray:
    """A bone object's bind position, down its chain of `bones`, which don't turn (only tag_brass does, and nothing
    hangs off it)."""
    parent, position, _ = prefabs.bones[bone]
    assert parent is None or prefabs.bones[parent][2] == "0,0,0,1", "a sticker's bone chain can't turn"
    local = np.array([float(v) for v in position.split(",")])
    return local if parent is None else bind_position(prefabs, parent) + local


def world_prefab(weapon: Weapon, prefabs: Prefabs) -> dict:
    document = remap_guids(load(M4 / "wm_m4a1.prefab"), f"{prefabs.guid_salt}wm")
    root = document["RootObject"]
    root["Name"] = f"wm_{weapon.name}"
    renderer = component(root, "SkinnedModelRenderer")
    renderer["Model"] = f"{weapon.asset}/w_{weapon.model}.vmdl"
    renderer["BodyGroups"] = prefabs.default_mesh_groups
    keep = {"Muzzle": prefabs.world_muzzle, "EjectionPort": prefabs.world_eject, "LeftHandIK": prefabs.world_left_hand}
    root["Children"] = [child for child in root["Children"] if keep.get(child["Name"]) is not None]
    for child in root["Children"]:
        child["Position"] = keep[child["Name"]]
        if child["Name"] == "LeftHandIK":
            child["Rotation"] = prefabs.world_left_hand_rotation or WORLD_LEFT_HAND_ROTATION
    root["Children"] += attachment_points(weapon, prefabs, "wm")
    if prefabs.charm is not None:
        root["Children"].append(charm_point(prefabs, "wm", prefabs.charm))
    if prefabs.sticker is not None:
        root["Children"].append(sticker_point(prefabs, "wm", prefabs.sticker[0], WORLD_STICKER_LIFT))
    document["__references"] = []
    return document


def mount_prefab(weapon: Weapon, prefabs: Prefabs) -> dict:
    document = remap_guids(load(M4 / "mount_m4a1.prefab"), f"{prefabs.guid_salt}mount")
    root = document["RootObject"]
    root["Name"] = f"mount_{weapon.name}"
    renderer = component(find(root, "Model"), "SkinnedModelRenderer")
    renderer["Model"] = f"{weapon.asset}/w_{weapon.model}.vmdl"
    renderer["BodyGroups"] = prefabs.default_mesh_groups
    document["__references"] = []
    return document


def equipment_resource(weapon: Weapon, prefabs: Prefabs) -> dict:
    resource = load(M4 / "m4a1.equip")
    resource.update({
        "Name": prefabs.title,
        "Description": prefabs.description,
        "Icon": icon_path(weapon),
        "Price": prefabs.price,
        "KillReward": prefabs.kill_reward,
        "MainPrefab": {"_type": "gameobject", "prefab": f"{weapon.asset}/weapon_{weapon.name}.prefab"},
        "WorldModelPrefab": {"_type": "gameobject", "prefab": f"{weapon.asset}/wm_{weapon.name}.prefab"},
        "ViewModelPrefab": {"_type": "gameobject", "prefab": f"{weapon.asset}/vm_{weapon.name}.prefab"},
        "WorldModel": f"{weapon.asset}/w_{weapon.model}.vmdl",
        "WorldModelBodyGroups": 0,
        "__references": [],
        "Category": prefabs.category,
        "GunsmithOffset": prefabs.gunsmith_offset,
        **prefabs.equip_fields,
    })
    if prefabs.review_note:
        resource["ReviewNote"] = prefabs.review_note
    return resource


def make_parts_eligible(weapon: Weapon, prefabs: Prefabs) -> int:
    """Adds the gun to the eligible weapons of FITTING_PARTS in its slots' categories (the Bizon has no Underbarrel),
    editing the list in place to keep the files' formatting."""
    # Only these categories use the shared catalogue; replacement stocks/barrels/grips can have gun-specific parts.
    categories = {slot[0] for slot in prefabs.slots} & SLOT_CATEGORIES
    equip = f"{weapon.asset}/{weapon.name}.equip"
    changed = 0
    for path in FITTING_PARTS:
        text = path.read_text(encoding="utf-8")
        part = json.loads(text)
        if equip in part["EligibleEquipment"] or part["Category"] in SLOT_CATEGORIES - categories:
            continue
        match = ELIGIBLE.search(text)
        indent = re.search(r"\n(\s*)\S", match.group(2)).group(1)
        text = text[:match.end(2)] + f',\n{indent}"{equip}"' + text[match.end(2):]
        path.write_text(text, encoding="utf-8", newline="")
        changed += 1
    return changed


def own_parts(weapon: Weapon, prefabs: Prefabs) -> int:
    """Writes a gunsmith part for every non-factory part_choices choice; the gunsmith's "Standard" is choice 0."""
    if weapon.name == "m16":
        # This gun combines native animated magazines with independently mounted shared models.
        from m16_gunsmith import resources
        resources()
        return 20
    assert set(prefabs.parts) == {choice for choices in weapon.part_choices.values() for choice, _ in choices[1:]}
    for group, choices in weapon.part_choices.items():
        category, folder = PART_SLOTS[group]
        for index, (choice, _) in enumerate(choices[1:], start=1):
            part = prefabs.parts[choice]
            if not part.offered:
                continue
            document = {
                "Name": part.name,
                "Category": category,
                "EligibleEquipment": [f"{weapon.asset}/{weapon.name}.equip"],
                "RequiredLevel": 0,
                "Description": f"{part.description} {part.effect()}",
                "ModifyBodygroups": True,
                "Bodygroups": {group: index, **part.bodygroups},
                "VerticalRecoilScale": part.vertical_recoil,
                "HorizontalRecoilScale": part.horizontal_recoil,
            }
            if category == "Magazine":
                document["MagazineCapacity"] = part.magazine_capacity
                document["ReloadTimeMultiplier"] = part.reload_time
            if part.reload_variant:
                sounds = prefabs.reload_sounds()
                document["ReloadAnimation"] = weapon.reload_variants.index(part.reload_variant) + 1
                document["ReloadTime"], document["EmptyReloadTime"] = part.reload_times
                document["ReloadSounds"] = sounds[f"reload{part.reload_variant}"]
                document["EmptyReloadSounds"] = sounds[f"reload_empty{part.reload_variant}"]
            if part.muzzle_shift:
                document["MuzzleShift"] = vector(part.muzzle_shift)
            if part.tip_shift:
                document["TipShift"] = vector(part.tip_shift)
            if part.falloff != 1:
                document["DamageFalloffScale"] = part.falloff
            if part.optic_bodygroups:
                document["OpticBodygroups"] = part.optic_bodygroups
            if part.optic_mount_shift:
                document["OpticMountShift"] = vector(part.optic_mount_shift)
            if part.rail_optic_aim:
                document["RailOpticAimCorrection"] = vector(part.rail_optic_aim)
            if part.rail_iron_aim:
                document["RailIronAimCorrection"] = vector(part.rail_iron_aim)
            document.update({"__references": [], "__version": 0})
            path = ASSETS / "gunsmith" / weapon.name / folder / f"att_vm_p04_{choice}.gnsmth"
            path.parent.mkdir(parents=True, exist_ok=True)
            save(path, document)
    return sum(part.offered for part in prefabs.parts.values())


def icon(weapon: Weapon, prefabs: Prefabs) -> None:
    """White silhouette of the addon's spawn icon, framed like the other 1024px HC1 gun icons."""
    from kastov_materials import load_vtf_texture  # kastov_materials puts SourceIO on the path
    pixels, width, height, _ = load_vtf_texture((EXTRACTED / f"{prefabs.icon_source}.vtf").read_bytes())
    alpha = np.frombuffer(pixels, np.uint8).reshape(height, width, 4)[:, :, 3]
    # The gun is opaque; the soft, semi-transparent rim around it is a drop shadow.
    ys, xs = np.nonzero(alpha > 192)
    crop = alpha[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    # Centred, spanning icon_width of the width (the M4's ~90%).
    scale = prefabs.icon_width * 1024 / crop.shape[1]
    size = (round(crop.shape[1] * scale), round(crop.shape[0] * scale))
    upscaled = np.asarray(Image.fromarray(crop, "L").resize(size, Image.LANCZOS), float)
    # Cut the shadow off after upscaling, leaving a crisp, anti-aliased edge like the other icons.
    edge = np.clip((upscaled - 170) / (235 - 170), 0, 1)
    mask = Image.fromarray((edge * edge * (3 - 2 * edge) * 255).astype(np.uint8), "L")
    out = Image.new("RGBA", (1024, 1024), (255, 255, 255, 0))
    white = Image.new("RGBA", size, (255, 255, 255, 255))
    white.putalpha(mask)
    out.alpha_composite(white, ((1024 - size[0]) // 2, (1024 - size[1]) // 2))
    out.save(ASSETS / icon_path(weapon), optimize=True)


def main() -> None:
    weapon = kastov_weapons.from_command_line(__doc__)
    prefabs = PREFABS[weapon.name]
    out = weapon.folder
    if prefabs.gameplay is not None:
        save(out / f"weapon_{weapon.name}.prefab", weapon_prefab(weapon, prefabs))
    else:
        save(out / f"weapon_{weapon.name}.prefab", patched_weapon_prefab(weapon, prefabs))
    save(out / f"vm_{weapon.name}.prefab", viewmodel_prefab(weapon, prefabs))
    save(out / f"wm_{weapon.name}.prefab", world_prefab(weapon, prefabs))
    save(out / f"mount_{weapon.name}.prefab", mount_prefab(weapon, prefabs))
    save(out / f"{weapon.name}.equip", equipment_resource(weapon, prefabs))
    if prefabs.icon_source is not None:
        icon(weapon, prefabs)
    print(f"wrote {weapon.name}'s prefabs and equip and {own_parts(weapon, prefabs)} own parts; "
          f"made {make_parts_eligible(weapon, prefabs)} parts eligible")


if __name__ == "__main__":
    main()
